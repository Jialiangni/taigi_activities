import copy
import io
import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from crawler.collection import CollectionError
from crawler.review import review, Pending, language_claims, validate_auto_source, source_url, duplicate
from crawler.sources.opentix import parse_program
from crawler.verified import load_verified
from scripts.fetch_review_candidates import extract, trusted_run

NOW = datetime.fromisoformat('2026-09-19T10:00:00+08:00')
URL = 'https://www.opentix.life/event/123'


class Client:
    def __init__(self, program):
        self.program = program
        self.fail = False
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        if self.fail:
            raise CollectionError('http_502')
        p = self.program
        return '<main>' + p['name'] + '臺北劇場' + p['description'] + '</main>', {
            'final_url': url, 'sha256': 'a'*64, 'fetched_at': NOW.isoformat()}

    def json(self, url):
        self.calls.append(url)
        if self.fail:
            raise CollectionError('http_502')
        return {'result': self.program}, {'sha256': 'b'*64, 'fetched_at': NOW.isoformat()}


class CandidateReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'data').mkdir()
        self.folder = self.root/'candidates'
        self.folder.mkdir()
        self.program = {'id': '123', 'name': '台語故事劇場', 'status': 3,
            'description': '<p>演出語言：臺語</p>', 'changeNotification': '<p></p>',
            'programOrganizers': [{'type': '主辦單位', 'info': [{'name': '故事劇團'}]}],
            'eventVenues': [{'id': '10', 'eventNoteContent': '',
                'venue': {'name': '臺北劇場', 'city': '臺北市', 'area': '中正區', 'address': '中山路1號'},
                'events': [{'id': '789', 'status': 0, 'description': '',
                    'startDateTime': '2026-10-01T14:00:00+08:00', 'endDateTime': '2026-10-01T15:00:00+08:00',
                    'groupSections': {'default': [{'price': 300}]}}]}]}
        self.client = Client(self.program)
        self.write('data/verified_activities.json', {'schema_version': 1, 'sources': {}, 'activities': []})
        self.write('data/ui_taigi.json', {})
        self.write('data/ui_price_taigi.json', {})
        self.candidates = parse_program(self.program, {})
        self.save_candidates()

    def write(self, name, data):
        (self.root/name).write_text(json.dumps(data, ensure_ascii=False))

    def save_candidates(self, collected=NOW):
        self.write('candidates/opentix.json', {'source_id': 'opentix', 'candidates': self.candidates})
        self.write('candidates/report.json', {'collected_at': collected.isoformat(),
            'sources': [{'source_id': 'opentix', 'status': 'ok', 'candidate_count': len(self.candidates)}]})

    def run_review(self, apply=True):
        return review(self.folder, root=self.root, client=self.client, now=NOW, apply=apply)

    def test_live_evidence_approval_and_idempotent_repeat(self):
        first = self.run_review()
        self.assertEqual(first['counts'], {'approved': 1})
        events = load_verified(self.root/'data/verified_activities.json', now=NOW)
        self.assertEqual(events[0].id, 'opentix_789')
        original = (self.root/'data/verified_activities.json').read_bytes()
        self.client.calls.clear()
        self.assertEqual(self.run_review()['counts'], {'duplicate': 1})
        self.assertEqual(self.client.calls, [])
        self.assertEqual(original, (self.root/'data/verified_activities.json').read_bytes())

    def test_dry_run_and_network_failure_preserve_catalog(self):
        original = (self.root/'data/verified_activities.json').read_bytes()
        self.assertEqual(self.run_review(False)['counts'], {'approved': 1})
        self.assertEqual(original, (self.root/'data/verified_activities.json').read_bytes())
        self.client.fail = True
        self.assertEqual(self.run_review()['counts'], {'pending': 1})
        self.assertEqual(json.loads((self.root/'data/verified_activities.json').read_text())['activities'], [])

    def test_subtitles_biographies_negation_and_keyword_hits_are_not_language_proof(self):
        for text in ['字幕語言：臺語', '曾演出台語劇', '台語指導：某某',
                     '演出語言：華語；演員會台語', '非臺語發音', '本片並非演出語言：臺語',
                     '臺灣台語發音比例：0%', '演出語言：台語以外的語言']:
            with self.subTest(text=text):
                p = copy.deepcopy(self.program)
                p['description'] = '<p>'+text+'</p>'
                self.assertEqual(language_claims(p, p['eventVenues'][0]), [])

    def test_venue_language_overrides_generic_program_claim(self):
        self.program['eventVenues'][0]['eventNoteContent'] = '<p>演出語言：華語</p>'
        self.assertEqual(language_claims(self.program, self.program['eventVenues'][0]), [])

    def test_cancellation_status_mismatch_and_ambiguous_sessions_stay_pending(self):
        original = copy.deepcopy(self.program)
        mutations = [lambda p:p.update(changeNotification='本場取消'),
                     lambda p:p.update(status=4),
                     lambda p:p['eventVenues'][0]['events'][0].update(status=4),
                     lambda p:p['eventVenues'][0]['events'][0].update(startDateTime='2026-10-01T15:00:00+08:00'),
                     lambda p:p.update(description='<p>字幕語言：臺語</p>'),
                     lambda p:p.update(description='<p>雙版本演出</p><p>演出語言：臺語</p>')]
        for mutate in mutations:
            p = copy.deepcopy(original)
            mutate(p)
            self.client.program = p
            self.assertEqual(self.run_review()['counts'], {'pending': 1})

    def test_other_source_and_partial_source_failure_do_not_promote_or_erase(self):
        self.candidates.append(dict(self.candidates[0], id='other', source_url='https://attacker.example/event/123'))
        self.save_candidates()
        result = self.run_review()
        self.assertEqual(result['counts'], {'approved': 1, 'duplicate': 1})
        # A new unknown source URL must never be fetched.
        self.candidates = [dict(self.candidates[0], fields={}, source_url='https://attacker.example/event/123')]
        self.save_candidates()
        result = self.run_review()
        self.assertEqual(result['counts'], {'pending': 1})
        self.assertTrue(all('attacker' not in url for url in self.client.calls))

    def test_owner_feedback_excludes_matching_candidate_without_network(self):
        c = self.candidates[0]
        self.write('data/manual_candidate_decisions.json', {'schema_version': 1, 'decisions': [{
            'candidate_id': c['id'], 'source_id': c['source_id'], 'source_url': c['source_url'],
            'title': c['title'], 'decision': 'excluded', 'reason': 'owner_feedback_not_event',
            'reviewed_at': NOW.isoformat()}]})
        result = self.run_review()
        self.assertEqual(result['counts'], {'excluded': 1})
        self.assertEqual(result['decisions'][0]['review_mode'], 'owner_feedback')
        self.assertEqual(self.client.calls, [])

    def test_cross_platform_session_duplicate(self):
        self.run_review()
        path = self.root/'data/verified_activities.json'
        catalog = json.loads(path.read_text())
        catalog['activities'][0]['verification'].pop('opentix_session_id')
        catalog['activities'][0]['verification'].pop('mode')
        catalog['sources']['auto_op_123'].pop('opentix_sessions')
        catalog['sources']['auto_op_123'].pop('automated_review')
        catalog['sources']['auto_op_123']['url'] = 'https://example.org/events/1'
        catalog['activities'][0]['activity']['source_url'] = 'https://example.org/events/1'
        self.write('data/verified_activities.json', catalog)
        self.assertEqual(self.run_review()['counts'], {'duplicate': 1})

    def test_missing_or_stale_candidate_report_stops_before_writing(self):
        self.save_candidates(NOW-timedelta(days=2))
        with self.assertRaises(Pending): self.run_review()
        self.save_candidates()
        (self.folder/'opentix.json').unlink()
        with self.assertRaises(Pending): self.run_review()

    def test_recheck_rejects_changed_language_and_program_status(self):
        self.run_review()
        source = json.loads((self.root/'data/verified_activities.json').read_text())['sources']['auto_op_123']
        validate_auto_source(source, self.program)
        for key, value in [('description','<p>演出語言：華語</p>'), ('status',4), ('changeNotification','延期')]:
            p = dict(self.program, **{key:value})
            with self.assertRaises(ValueError): validate_auto_source(source, p)

    def test_separate_sessions_are_not_deduplicated(self):
        event = copy.deepcopy(self.program['eventVenues'][0]['events'][0])
        event.update(id='790',startDateTime='2026-10-02T14:00:00+08:00',endDateTime='2026-10-02T15:00:00+08:00')
        self.program['eventVenues'][0]['events'].append(event)
        self.candidates = parse_program(self.program, {})
        self.save_candidates()
        self.assertEqual(self.run_review()['counts'], {'approved': 2})

    def test_untrusted_runs_and_zip_paths_rejected(self):
        run = {'head_repository': {'full_name':'owner/repo'}, 'head_branch':'main',
               'path':'.github/workflows/collect.yml','event':'schedule','status':'completed',
               'conclusion':'failure','created_at':NOW.isoformat()}
        self.assertTrue(trusted_run(run,'owner/repo',NOW))
        self.assertFalse(trusted_run(dict(run,event='pull_request'),'owner/repo',NOW))
        self.assertFalse(trusted_run(run,'other/repo',NOW))
        for name in ['../report.json','run.py','facebook.json']:
            raw = io.BytesIO()
            with zipfile.ZipFile(raw,'w') as z:z.writestr(name,'{}')
            with self.assertRaises(ValueError):extract(raw.getvalue(),self.root/'artifact')

    def test_source_identity_preserves_library_query_ids(self):
        a = 'https://www.library.ntpc.gov.tw/singlehtml/ActvInfo?cntId=one'
        b = 'https://www.library.ntpc.gov.tw/singlehtml/ActvInfo?cntId=two'
        self.assertNotEqual(source_url(a), source_url(b))
        self.assertEqual(source_url(a), source_url(a+'&utm_source=test#top'))

    def test_series_period_is_not_silently_dropped_as_first_session(self):
        self.run_review()
        catalog = json.loads((self.root/'data/verified_activities.json').read_text())
        hint = dict(catalog['activities'][0]['activity'], end_time='2026-10-02T15:00:00+08:00')
        self.assertIsNone(duplicate(hint, catalog))


if __name__ == '__main__':
    unittest.main()
