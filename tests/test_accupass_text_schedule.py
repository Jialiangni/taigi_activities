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

class ReviewedTextTests(unittest.TestCase):
    def fixture(self, directory):
        from crawler.accupass_text_review import digest
        terms = ' 故事屋。台語劇場由夾腳拖劇團演出。需購票，陪同家長需另購票。適合3-10歲，每場20位。'
        client = Client(TEXT + terms)
        html, evidence = client.get(URL); live = parse_event(html, URL, evidence)[0]; fields = live['fields']
        contract = {'title': live['title'], 'article_sha256': digest(fields['official_summary']),
                    'identity': {k: fields[k] for k in ('address','city','organizer','event_status','start_time','end_time')},
                    'venue': '故事屋', 'is_free': False, 'price_info': '需購票，陪同家長需另購票。',
                    'ticket_quote': '需購票，陪同家長需另購票。',
                    'language_quote': '台語劇場由夾腳拖劇團演出。',
                    'description_quotes': ['台語劇場由夾腳拖劇團演出。', '需購票，陪同家長需另購票。', '適合3-10歲，每場20位。'],
                    'sessions': [s for s in fields['text_schedule_rows'] if s['category']]}
        root = Path(directory); (root/'data').mkdir(exist_ok=True)
        (root/'data/accupass_text_reviews.json').write_text(json.dumps({'schema_version':1,'events':{URL:contract}}))
        child = dict(live, fields=dict(fields, reviewed_text_session=contract['sessions'][0]))
        return root, client, child, contract

    def test_reviewed_paid_session_live_binding_and_conflicts(self):
        from crawler.accupass_text_review import verify_session, validate_live
        from crawler.collection import CollectionError
        with tempfile.TemporaryDirectory() as temp:
            root, client, child, contract = self.fixture(temp)
            _, source, row = verify_session(child, client, root, NOW)
            self.assertFalse(row['activity']['is_free'])
            self.assertIsNone(row['activity']['end_time'])
            self.assertEqual(row['activity']['category'], '台語舞台劇')
            validate_live(source, client.get(URL)[0])
            for original, replacement in [('15:30','15:35'),('夾腳拖劇團','另一劇團'),('20位','30位'),('需購票','免費'),('台語劇場','華語劇場')]:
                with self.subTest(original=original), self.assertRaises(CollectionError):
                    validate_live(source, Client(client.text.replace(original,replacement)).get(URL)[0])
            forged = dict(child, fields=dict(child['fields'], reviewed_text_session=child['fields']['text_schedule_rows'][0]))
            with self.assertRaises(CollectionError): verify_session(forged, client, root, NOW)

    def test_old_candidates_refresh_then_two_sessions_reach_editorial_queue(self):
        from crawler.editorial_queue import prepare
        with tempfile.TemporaryDirectory() as temp:
            root, client, _, _ = self.fixture(temp)
            def write(name, value): (root/name).write_text(json.dumps(value))
            write('data/verified_activities.json', {'schema_version':1,'sources':{},'activities':[]})
            write('data/ai_taigi.json', {'schema_version':1,'protected_activity_ids':[],'editions':{},'attempts':{},'daily_usage':{}})
            write('data/ui_taigi.json', {}); write('data/ui_price_taigi.json', {})
            (root/'data/editorial').mkdir()
            write('data/editorial/queue.json', {'schema_version':1,'items':[]})
            write('data/editorial/receipts.json', {'schema_version':1,'results':{}})
            folder = root/'candidates'; folder.mkdir()
            html, evidence = client.get(URL); rows = parse_event(html, URL, evidence)
            rows[0]['fields'].pop('text_schedule_rows'); rows[0]['fields'].pop('text_schedule_issue')
            write('candidates/accupass.json', {'source_id':'accupass','candidates':rows})
            write('candidates/report.json', {'collected_at':NOW.isoformat(),'sources':[{'source_id':'accupass','status':'ok','candidate_count':1}]})
            from unittest.mock import patch
            with patch('crawler.review.Client', return_value=client):
                result = prepare(folder, root, NOW)
                again = prepare(folder, root, NOW)
            self.assertEqual(len(result['items']), 2)
            self.assertEqual([i['activity_id'] for i in result['items']], [i['activity_id'] for i in again['items']])
            self.assertEqual(json.loads((root/'data/verified_activities.json').read_text())['activities'], [])
