import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from crawler import editorial_queue as q
from crawler.ai_editorial import fingerprint, save_json, approved_edition, EditorialError
from crawler.models import Activity
from crawler.verified import REVIEWED_FIELDS, load_verified
from scripts.editorial_sync import checked_files


class EditorialQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.now = datetime.fromisoformat('2027-01-01T08:00:00+08:00')
        self.activity = Activity(id='new', title='台語故事',
            description='王老師講故事，介紹故事裡的人物與生活。需要事先報名。',
            city='臺北市', venue='故事館', organizer='故事館',
            start_time='2027-02-01T10:00:00+08:00', end_time='2027-02-01T11:00:00+08:00',
            source_url='https://example.org/event/new').to_dict()
        self.row = {'activity': self.activity, 'verification': {'status': 'verified',
            'source_id': 'source', 'language_evidence': '台語故事',
            'confirmed_fields': {k: self.activity[k] for k in REVIEWED_FIELDS}}}
        self.source = {'url': self.activity['source_url'], 'title': '台語故事',
                       'required_text': ['台語故事'], 'checked_at': self.now.isoformat(),
                       'snapshot_sha256': 'a' * 64}
        self.item = q.request_for(self.row, self.source)
        self.guide = 'Test editorial guide'
        (self.root / 'TAIGI_EDITORIAL.md').write_text(self.guide)
        self.write('data/verified_activities.json', {'schema_version': 1, 'sources': {}, 'activities': []})
        self.write('data/ai_taigi.json', {'schema_version': 1, 'protected_activity_ids': [],
                                        'editions': {}, 'attempts': {}, 'daily_usage': {}})
        self.write(q.RECEIPTS, {'schema_version': 1, 'results': {}})
        self.write(q.QUEUE, {'schema_version': 1, 'items': [self.item]})
        self.result = {'schema_version': 1, 'activity_id': 'new', 'source_hash': self.item['source_hash'],
            'guide_hash': fingerprint(self.guide),
            'summary_taigi': '王老師講故事，介紹故事內底的人物佮生活。',
            'description_taigi': '王老師講故事，介紹故事內底的人物佮生活。這場活動愛事先報名。',
            'uncertain_terms': [], 'dictionary_evidence': [],
            'editor': {'provider': 'other-ai', 'model': 'test-fixture'},
            'edited_at': self.now.isoformat(),
            'review': {'facts_match': True, 'natural_taiwanese': True,
                       'people_and_content_complete': True, 'issues': [],
                       'evidence': [{'claim': '王老師講故事', 'quote': '王老師講故事'},
                                    {'claim': '愛事先報名', 'quote': '需要事先報名'}]}}

    def write(self, name, value):
        save_json(self.root / name, value)

    def return_result(self, result=None):
        self.write(q.RESULTS + '/' + q.result_name(self.item), result or self.result)

    def test_no_result_never_publishes_and_never_checks_network(self):
        with patch('crawler.verified.check_live_sources') as live:
            self.assertEqual(q.ingest(self.root, self.now), [])
            live.assert_not_called()
        self.assertEqual(q.read(self.root, 'data/verified_activities.json')['activities'], [])

    def test_any_provider_can_return_and_public_copy_is_bound(self):
        self.return_result()
        with patch('crawler.verified.check_live_sources', return_value={}) as live:
            self.assertEqual(q.ingest(self.root, self.now), ['new'])
            self.assertEqual(len(live.call_args[0][0]), 1)
        state = q.read(self.root, 'data/ai_taigi.json')
        self.assertEqual(approved_edition(self.activity, state)['summary_taigi'], self.result['summary_taigi'])
        self.assertEqual(len(load_verified(self.root / 'data/verified_activities.json', now=self.now)), 1)
        self.assertEqual(q.pending(self.root, self.now), [])
        with patch('crawler.verified.check_live_sources') as live:
            self.assertEqual(q.ingest(self.root, self.now), [])
            live.assert_not_called()

    def test_failed_live_source_leaves_all_publication_data_untouched(self):
        self.return_result()
        names = ['data/verified_activities.json', 'data/ai_taigi.json', q.QUEUE, q.RECEIPTS]
        before = [(self.root / n).read_bytes() for n in names]
        with patch('crawler.verified.check_live_sources', side_effect=ValueError('source changed')):
            with self.assertRaises(ValueError):
                q.ingest(self.root, self.now)
        self.assertEqual(before, [(self.root / n).read_bytes() for n in names])

    def test_wrong_hash_guide_facts_dictionary_and_unresolved_terms_rejected(self):
        mutations = [lambda r: r.update(source_hash='b' * 64),
                     lambda r: r.update(guide_hash='c' * 64),
                     lambda r: r['review'].update(facts_match=False),
                     lambda r: r['review']['evidence'][0].update(quote='not in source'),
                     lambda r: r.update(uncertain_terms=['疑詞']),
                     lambda r: r.update(dictionary_evidence=[{'status': 'not_found'}]),
                     lambda r: r.update(summary_taigi='新增原文沒有的票價 9999 元，請盡早報名。'),
                     lambda r: r.update(start_time='2027-01-01')]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                result = copy.deepcopy(self.result)
                mutation(result)
                with self.assertRaises((ValueError, EditorialError)):
                    q.validate_result(result, self.item, self.guide)

    def test_expired_and_protected_records_never_enter_publishing(self):
        self.return_result()
        self.assertEqual(q.pending(self.root, self.now + timedelta(days=40)), [])
        state = q.read(self.root, 'data/ai_taigi.json')
        state['protected_activity_ids'] = ['new']
        self.write('data/ai_taigi.json', state)
        self.assertEqual(q.ingest(self.root, self.now), [])

    def test_published_id_never_rewritten_even_if_date_changed(self):
        changed = copy.deepcopy(self.row)
        changed['activity']['start_time'] = '2027-03-01T10:00:00+08:00'
        self.write('data/verified_activities.json', {'schema_version': 1, 'sources': {'source': self.source},
                                                    'activities': [changed]})
        self.assertEqual(q.pending(self.root, self.now), [])

    def test_cross_id_duplicate_and_tampered_queue_blocked(self):
        other = copy.deepcopy(self.row)
        other['activity']['id'] = 'other'
        self.write('data/verified_activities.json', {'schema_version': 1, 'sources': {'source': self.source},
                                                    'activities': [other]})
        self.assertEqual(q.pending(self.root, self.now), [])
        item = copy.deepcopy(self.item)
        item['activity']['venue'] = 'tampered'
        self.write(q.QUEUE, {'schema_version': 1, 'items': [item]})
        with self.assertRaises(ValueError):
            q.pending(self.root, self.now)

    def test_checked_files_reuses_identical_return_and_preserves_accepted_copy(self):
        folder = self.root / 'local'
        save_json(folder / q.result_name(self.item), self.result)
        with patch('scripts.editorial_sync.pending', return_value=[self.item]):
            self.assertEqual(len(checked_files(folder, self.root)), 1)
            self.return_result()
            self.assertEqual(checked_files(folder, self.root), [])
        q.ingest(self.root, self.now, live_check=False)
        self.assertEqual(checked_files(folder, self.root), [])
        self.result['description_taigi'] += '更改'
        save_json(folder / q.result_name(self.item), self.result)
        with self.assertRaises(ValueError):
            checked_files(folder, self.root)

    def test_prepare_uses_isolated_catalog_and_keeps_unprocessed_batches(self):
        self.write('data/ui_taigi.json', {})
        self.write('data/ui_price_taigi.json', {})
        def fake_review(folder, root, now, apply):
            # Represents a newly verified second session from the existing verifier.
            row = copy.deepcopy(self.row)
            row['activity']['id'] = 'second'
            row['activity']['start_time'] = '2027-02-02T10:00:00+08:00'
            row['activity']['end_time'] = '2027-02-02T11:00:00+08:00'
            row['verification']['confirmed_fields'] = {k: row['activity'][k] for k in REVIEWED_FIELDS}
            save_json(root / 'data/verified_activities.json', {'schema_version': 1,
                      'sources': {'source': self.source}, 'activities': [row]})
            return {'applied_to_catalog': True}
        original = (self.root / 'data/verified_activities.json').read_bytes()
        with patch('crawler.editorial_queue.review', side_effect=fake_review):
            queued = q.prepare(self.root, self.root, self.now)
            self.assertEqual({i['activity_id'] for i in queued['items']}, {'new', 'second'})
            self.assertEqual(len(q.prepare(self.root, self.root, self.now)['items']), 2)
        self.assertEqual(original, (self.root / 'data/verified_activities.json').read_bytes())
        self.assertFalse(q.read(self.root, 'data/audit/latest-candidate-review.json')['applied_to_catalog'])

    def test_series_request_only_checks_its_own_session(self):
        row = copy.deepcopy(self.row)
        row['verification']['opentix_session_id'] = 'new'
        source = dict(self.source, opentix_sessions=[{'session_id': 'ended'}, {'session_id': 'new'}])
        self.assertEqual(q.request_for(row, source)['source']['opentix_sessions'], [{'session_id': 'new'}])
        self.assertEqual(len(source['opentix_sessions']), 2)


if __name__ == '__main__':
    unittest.main()
