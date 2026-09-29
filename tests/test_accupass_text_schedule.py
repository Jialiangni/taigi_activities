import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime

from crawler.sources.accupass_text_schedule import text_schedule
from crawler.sources.accupass import parse_event
from crawler.review import review, verify_accupass, Pending

EVENT = {'@type': 'Event', 'name': '混合故事課', 'startDate': '2026-10-03T13:00:00+08:00',
         'endDate': '2026-10-03T17:00:00+08:00', 'location': {'name': '故事屋', 'address': '新北市三峽區'},
         'organizer': {'name': '主辦'}, 'eventStatus': 'https://schema.org/EventScheduled'}
TEXT = '2026/10/3（六）13:10〖音樂故事教室〗-嘉寶老師 (約15分鐘/堂) ' \
       '2026/10/3（六）15:30〖台語劇場〗-夾腳拖劇團 (約20分鐘/堂) ' \
       '2026/10/3（六）15:55〖台語劇場〗-夾腳拖劇團 (約20分鐘/堂)'
URL = 'https://www.accupass.com/event/123456'
NOW = datetime.fromisoformat('2026-09-29T12:00:00+08:00')


class Client:
    def __init__(self, text=TEXT): self.text = text
    def get(self, url):
        return '<script type="application/ld+json">' + json.dumps(dict(EVENT, description=self.text)) + '</script>', {
            'url': url, 'final_url': url, 'sha256': 'a'*64, 'fetched_at': NOW.isoformat()}


class TextScheduleTests(unittest.TestCase):
    def test_classifies_only_explicit_labels_and_preserves_approximate_duration(self):
        rows, issue = text_schedule(TEXT, EVENT)
        self.assertEqual(issue, '')
        self.assertEqual(len(rows), 3)
        selected = [r for r in rows if r['category']]
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]['performer'], '夾腳拖劇團')
        self.assertIsNone(selected[0]['end_time'])
        self.assertTrue(selected[0]['duration_approximate'])
        self.assertEqual(selected[0]['category'], '台語舞台劇')

    def test_incomplete_conflicting_dates_and_duplicate_starts_are_not_partially_used(self):
        for text in [TEXT.replace('15:55', '25:55'), TEXT.replace('（六）', '（日）'),
                     TEXT.replace('15:55', '15:30'), TEXT.replace('約20分鐘/堂', '時間未定'),
                     TEXT.replace('2026/10/3', '2026/10/4')]:
            with self.subTest(text=text):
                rows, issue = text_schedule(text, EVENT)
                self.assertFalse(rows)
                self.assertTrue(issue)

    def test_mentioning_taigi_is_not_a_positive_session_label(self):
        for title in ['非台語劇場', '台語顧問分享', '華語場（附台語字幕）']:
            rows, _ = text_schedule(TEXT.replace('台語劇場', title), EVENT)
            self.assertFalse(any(r['category'] for r in rows))

    def test_pipeline_reports_individual_candidates_without_publishing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'data').mkdir(); folder = root/'candidates'; folder.mkdir()
            def write(path, data): (root/path).write_text(json.dumps(data, ensure_ascii=False))
            write('data/verified_activities.json', {'schema_version': 1, 'sources': {}, 'activities': []})
            write('data/ui_taigi.json', {}); write('data/ui_price_taigi.json', {})
            html, ev = Client().get(URL); rows = parse_event(html, URL, ev)
            write('candidates/accupass.json', {'source_id': 'accupass', 'candidates': rows})
            write('candidates/report.json', {'collected_at': NOW.isoformat(), 'sources': [{'source_id': 'accupass', 'status':'ok', 'candidate_count': 1}]})
            audit = review(folder, root, Client(), NOW, apply=True)
            item = audit['decisions'][0]
            self.assertEqual(item['taigi_session_count'], 2)
            self.assertEqual(item['other_session_count'], 1)
            self.assertEqual(item['decision'], 'pending')
            ids = [s['candidate_id'] for s in item['session_classifications']]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(json.loads((root/'data/verified_activities.json').read_text())['activities'], [])
            with self.assertRaises(Pending): verify_accupass(rows[0], Client(), NOW)
            # A source edit must be re-read, never classified using a stale candidate.
            changed = review(folder, root, Client(TEXT.replace('台語劇場', '華語劇場')), NOW)
            self.assertEqual(changed['decisions'][0]['taigi_session_count'], 0)
