import copy
import json
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from build_html import generate_single_html
from crawler.verified import DATA_PATH, check_source_content, check_opentix_sessions, load_verified
from crawler.sources.opentix import parse_program
from crawler.sources.google_workspace import GoogleWorkspaceSync, ics_text, fold_line
from main import build

NOW = datetime.fromisoformat('2026-09-18T23:00:00+08:00')


class VerifiedCalendarTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((Path(__file__).parent / 'fixtures/verified_catalog_base.json').read_text())
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'data.json'

    def load(self, data=None, now=NOW):
        self.path.write_text(json.dumps(data or self.data))
        return load_verified(self.path, now=now)

    def mutate(self, key, value):
        self.data['activities'][0]['activity'][key] = value
        self.data['activities'][0]['verification']['confirmed_fields'][key] = value

    def test_baseline_catalog_and_original_exclusion(self):
        events = self.load()
        old = json.loads((DATA_PATH.parent / 'audit/2026-09-18-legacy.json').read_text())
        self.assertEqual(len(old['records']), 64)
        self.assertEqual(len(events), 8)
        self.assertFalse({a.id for a in events} & {r['activity']['id'] for r in old['records']})
        self.assertEqual(sum(a.is_free is True for a in events), 5)
        self.assertEqual(sum(a.is_free is None for a in events), 3)

    def test_expanded_public_catalog_has_reviewed_sessions(self):
        events = load_verified(now=NOW)
        self.assertEqual(len(events), 81)
        self.assertEqual(sum(a.city.value == '臺北市' for a in events), 27)
        self.assertEqual(sum(a.city.value == '新北市' for a in events), 10)
        self.assertEqual(sum(a.city.value == '桃園市' for a in events), 44)
        self.assertEqual(sum(a.is_free is True for a in events), 16)
        self.assertEqual(sum(a.is_free is False for a in events), 28)
        self.assertFalse(any('後街人生' in a.title for a in events))
        # Human-rights series has five explicit sessions, not one multi-month event.
        series = [a for a in events if a.id.startswith('acc_2607280236031295663510')]
        self.assertEqual(len(series), 5)
        self.assertTrue(all(a.start_time[:10] == a.end_time[:10] for a in series))

    def test_live_opentix_change_blocks_publication(self):
        program = json.loads((Path(__file__).parent / 'fixtures/opentix_program.json').read_text())
        source = {'url': 'https://www.opentix.life/event/' + str(program['id']),
                  'opentix_sessions': [r['fields'] for r in parse_program(program, {})]}
        check_opentix_sessions(source, {'result': program})
        for key, value in [('startDateTime', 1), ('status', 999)]:
            changed = copy.deepcopy(program)
            changed['eventVenues'][0]['events'][0][key] = value
            with self.assertRaises(ValueError): check_opentix_sessions(source, {'result': changed})
        changed = copy.deepcopy(program)
        changed['eventVenues'][0]['events'].pop(0)
        with self.assertRaises(ValueError): check_opentix_sessions(source, {'result': changed})

    def test_yongchun_course_matches_official_recurrence_and_copy_fee(self):
        rows = [a for a in load_verified(now=NOW) if a.id.startswith('tpml_yongchun_')]
        self.assertEqual(len(rows), 16)
        self.assertEqual(rows[0].start_time, '2026-09-23T14:00:00+08:00')
        self.assertEqual(rows[-1].end_time, '2027-01-06T16:00:00+08:00')
        self.assertTrue(all(datetime.fromisoformat(a.start_time).weekday() == 2 for a in rows))
        total = sum((datetime.fromisoformat(a.end_time) - datetime.fromisoformat(a.start_time)).total_seconds() for a in rows)
        self.assertEqual(total, 32 * 3600)
        self.assertTrue(all(a.is_free is False and '影印費' in a.price_info and '整期' in a.description for a in rows))

    def test_district_audit_publishes_only_approved_ids(self):
        audit = json.loads((DATA_PATH.parent / 'audit/2026-09-18-district-publication-review.json').read_text())
        self.assertEqual(len(audit['records']), 14)
        events = load_verified(now=NOW)
        self.assertTrue(set(audit['new_session_ids']) <= {a.id for a in events})
        urls = {a.source_url for a in events}
        withheld = [r for r in audit['records'] if r['decision'] in ('excluded', 'expired', 'out_of_region', 'pending_language_evidence')]
        self.assertTrue(all(r['url'] not in urls and not r['published_ids'] for r in withheld))

    def test_unreviewed_entry_fails(self):
        self.data['activities'][0]['verification']['status'] = 'pending'
        with self.assertRaises(ValueError): self.load()

    def test_missing_language_evidence_fails(self):
        self.data['activities'][0]['verification']['language_evidence'] = ''
        with self.assertRaises(ValueError): self.load()

    def test_changed_date_requires_review(self):
        self.data['activities'][0]['activity']['start_time'] = '2026-09-21T14:00:00+08:00'
        with self.assertRaises(ValueError): self.load()

    def test_homepage_is_not_evidence(self):
        self.data['sources']['ntpc_booking']['url'] = 'https://www.library.ntpc.gov.tw/'
        with self.assertRaises(ValueError): self.load()

    def test_invalid_or_missing_time_is_not_invented(self):
        for value in ('', '2026-09-20', '2026-02-30T14:00:00+08:00', '2026-09-20T14:00:00'):
            with self.subTest(value=value):
                self.mutate('start_time', value)
                with self.assertRaises(ValueError): self.load()

    def test_out_of_region_is_not_defaulted_to_taipei(self):
        self.mutate('city', '臺中市')
        with self.assertRaises(ValueError): self.load()

    def test_invalid_end_and_unknown_fee(self):
        self.mutate('end_time', '2026-09-20T13:00:00+08:00')
        with self.assertRaises(ValueError): self.load()
        self.mutate('end_time', '2026-09-20T16:00:00+08:00')
        self.mutate('is_free', None)
        with self.assertRaises(ValueError): self.load()

    def test_duplicate_session_fails_but_distinct_sessions_survive(self):
        self.assertEqual(sum(a.start_time.startswith('2026-10-11') for a in self.load()), 2)
        duplicate = copy.deepcopy(self.data['activities'][0])
        duplicate['activity']['id'] = 'duplicate'
        self.data['activities'].append(duplicate)
        with self.assertRaises(ValueError): self.load()

    def test_past_sessions_removed_at_end_in_taipei_timezone(self):
        # 08:00 UTC is 16:00 Taipei, exactly the first session's ending.
        events = self.load(now=datetime.fromisoformat('2026-09-20T08:00:00+00:00'))
        self.assertEqual(len(events), 7)
        self.assertNotIn('ntpc_xizhi_songs_20260920', [a.id for a in events])
        self.assertEqual(self.load(now=datetime.fromisoformat('2027-01-01T00:00:00+08:00')), [])

    def test_source_change_or_block_page_fails(self):
        source = {'url': 'https://example.org/event/1', 'required_text': ['2026/10/03 10:00', '台語']}
        check_source_content(source, '<p>2026/10/03 10:00</p><b>台語</b>')
        for text in ('captcha', '<p>2026/10/04 10:00 台語</p>', '<script>2026/10/03 10:00 台語</script>'):
            with self.assertRaises(ValueError): check_source_content(source, text)

    def test_source_failure_preserves_existing_artifacts(self):
        out = Path(self.tmp.name)
        for name in ('index.html', 'taigi_activities.ics'): (out/name).write_text('existing')
        with patch('main.load_verified', side_effect=ValueError('source failed')):
            with self.assertRaises(ValueError): build(out, check_sources=True)
        for name in ('index.html', 'taigi_activities.ics'): self.assertEqual((out/name).read_text(), 'existing')

    def test_calendar_uses_real_end_and_utc(self):
        events = self.load()
        sync = GoogleWorkspaceSync()
        path = Path(self.tmp.name)/'events.ics'
        sync.export_ics(events, path)
        raw = path.read_bytes()
        self.assertEqual(raw.count(b'BEGIN:VEVENT'), 8)
        self.assertIn(b'DTSTART:20260920T060000Z\r\nDTEND:20260920T080000Z', raw)
        self.assertNotIn(b'\n', raw.replace(b'\r\n', b''))
        self.assertTrue(all(len(line) <= 75 for line in raw.split(b'\r\n')))
        query = parse_qs(urlsplit(sync.generate_google_calendar_url(events[0])).query)
        self.assertEqual(query['dates'], ['20260920T060000Z/20260920T080000Z'])
        self.assertEqual(query['ctz'], ['Asia/Taipei'])

    def test_calendar_escaping_and_utf8_folding(self):
        self.assertEqual(ics_text('a\\b;c,d\ne'), r'a\\b\;c\,d\ne')
        value = 'SUMMARY:' + '台語𨑨迌' * 40
        folded = fold_line(value)
        self.assertEqual(folded.replace('\r\n ', ''), value)
        self.assertTrue(all(len(line.encode()) <= 75 for line in folded.split('\r\n')))

    def test_html_and_ics_share_identical_sessions(self):
        events = self.load()
        output = Path(self.tmp.name)/'index.html'
        generate_single_html(events, output)
        html = output.read_text()
        data = json.loads(re.search(r'const ACTIVITIES_DATA = (\[.*?\]);', html, re.S).group(1))
        sync = GoogleWorkspaceSync()
        self.assertEqual([r['id'] for r in data], [a.id for a in events])
        for row, event in zip(data, events): self.assertEqual(row['ics_event'], sync.event_content(event))
        self.assertNotIn('images.unsplash.com', html)
        empty = Path(self.tmp.name)/'empty.html'
        generate_single_html([], empty)
        self.assertIn('const ACTIVITIES_DATA = [];', empty.read_text())


if __name__ == '__main__': unittest.main()
