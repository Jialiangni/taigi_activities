import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from crawler.review import (Pending, accupass_series_candidates, review,
                            validate_auto_source, verify_accupass)
from crawler.sources.accupass import parse_event, table_schedule

NOW = datetime.fromisoformat('2026-09-19T20:00:00+08:00')
URL = 'https://www.accupass.com/event/123456'
EVENT = {'@type':'Event', 'name':'台語戲劇導覽',
    'startDate':'2026-09-19T15:00:00+08:00', 'endDate':'2026-09-21T16:00:00+08:00',
    'eventStatus':'https://schema.org/EventScheduled',
    'location':{'name':'臺北紀念館', 'address':'臺北市大同區寧夏路87號'},
    'organizer':{'name':'故事屋'}, 'description':'在紀念館中體驗歷史故事。歡迎親子同行。'}
TABLE = '''<table><tr><th>月份</th><th>日期</th><th>時間</th></tr>
<tr><td rowspan="3">9月</td><td>9月19日(六)</td><td>15:00-16:00</td></tr>
<tr><td>9月20日(日)</td><td>15:00-16:00</td></tr>
<tr><td>9月21日(一)</td><td>15:00-16:00</td></tr></table>'''


def page(event=None, table=TABLE, terms='本活動全程以台語演出為主。活動費用｜免費，需事先報名。'):
    return '<script type="application/ld+json">' + json.dumps(event or EVENT) + '</script><main>' + terms + table + '</main>'


class Client:
    def __init__(self, html=None): self.html = html or page()
    def get(self, url):
        return self.html, {'final_url':url, 'sha256':'a'*64, 'fetched_at':NOW.isoformat()}


class SeriesTests(unittest.TestCase):
    def children(self, client=None):
        client = client or Client()
        html, evidence = client.get(URL)
        parent = parse_event(html, URL, evidence)[0]
        return accupass_series_candidates(parent, client)

    def test_table_rowspan_and_individual_proof(self):
        children = self.children()
        self.assertEqual(len(children), 3)
        with self.assertRaisesRegex(Pending, 'expired'):
            verify_accupass(children[0], Client(), NOW)
        sources = []
        for child in children[1:]:
            key, source, row = verify_accupass(child, Client(), NOW)
            sources.append(key)
            self.assertEqual(row['activity']['description'], EVENT['description'])
            self.assertEqual(row['activity']['start_time'], child['fields']['start_time'])
            self.assertEqual(len(source['automated_review']['series_schedule']), 3)
            validate_auto_source(source, None, page())
            with self.assertRaises(Pending):
                validate_auto_source(source, None, page(table=TABLE.replace('9月20日(日)', '9月22日(二)')))
            with self.assertRaises(Pending):
                validate_auto_source(source, None, page(terms='本活動全程以台語演出為主。活動費用｜500元。'))
        self.assertEqual(len(set(sources)), 2)

    def test_incomplete_or_conflicting_table_does_not_partially_publish(self):
        for table, reason in [
            (TABLE.replace('9月20日(日)', '9月20日(一)'), 'weekday_mismatch'),
            (TABLE.replace('9月20日(日)', '日期另訂'), 'incomplete_schedule_row'),
            (TABLE.replace('9月21日(一)', '9月20日(日)'), 'duplicate_schedule_start'),
            (TABLE.replace('<th>月份</th>', '<th>場地</th>'), 'per_session_fields_need_review'),
            (TABLE.replace('<td>9月21日(一)</td><td>15:00-16:00</td>', ''), 'incomplete_schedule_row'),
            (TABLE.replace('16:00', '14:00'), 'ambiguous_or_outside_period')]:
            with self.subTest(reason=reason):
                rows, issue = table_schedule(table, EVENT)
                self.assertFalse(rows)
                self.assertEqual(issue, reason)

    def test_reported_eight_session_shape_keeps_only_september_twentieth(self):
        days = [(7,18,'六'), (7,19,'日'), (8,9,'日'), (8,22,'六'),
                (8,23,'日'), (9,5,'六'), (9,19,'六'), (9,20,'日')]
        table = '<table><tr><th>日期</th><th>時間</th></tr>' + ''.join(
            f'<tr><td>{month:02d}月{day:02d}日（{weekday}）</td><td>15:00-16:00</td></tr>'
            for month,day,weekday in days) + '</table>'
        event = dict(EVENT, startDate='2026-07-18T15:00:00+08:00', endDate='2026-09-20T16:00:00+08:00')
        children = self.children(Client(page(event=event, table=table)))
        remaining = [child for child in children if datetime.fromisoformat(child['fields']['end_time']) > NOW]
        self.assertEqual(len(children), 8)
        self.assertEqual([c['fields']['start_time'] for c in remaining], ['2026-09-20T15:00:00+08:00'])

    def test_shared_time_rowspan(self):
        table = TABLE.replace('<td>15:00-16:00</td>', '<td rowspan="3">15:00-16:00</td>', 1)
        table = table.replace('<td>15:00-16:00</td>', '')
        rows, issue = table_schedule(table, EVENT)
        self.assertFalse(issue)
        self.assertEqual(len(rows), 3)

    def test_cross_year_is_resolved_from_explicit_period(self):
        event = dict(EVENT, startDate='2026-12-31T15:00:00+08:00', endDate='2027-01-01T16:00:00+08:00')
        table = '<table><tr><th>日期</th><th>時間</th></tr><tr><td>12/31(四)</td><td>15:00-16:00</td></tr><tr><td>1/1(五)</td><td>15:00-16:00</td></tr></table>'
        rows, issue = table_schedule(table, event)
        self.assertFalse(issue)
        self.assertEqual(rows[-1]['start_time'], '2027-01-01T15:00:00+08:00')

    def test_keyword_or_one_taigi_session_does_not_certify_entire_series(self):
        for text in ['台語顧問，活動費用｜免費。', '【台語場】活動費用｜免費。',
                     '本活動全程以台語演出為主。部分場次為華語。活動費用｜免費。',
                     '本活動全程以台語演出為主。活動費用｜待公告。',
                     '本活動全程以台語演出為主。活動費用｜免費。材料費100元。',
                     '本活動全程以台語演出為主。活動費用｜免費。活動已取消。']:
            with self.subTest(text=text), self.assertRaises(Pending):
                self.children(Client(page(terms=text)))
        # A contingent right to postpone is not an actual postponement.
        self.assertEqual(len(self.children(Client(page()+'<p>主辦單位保有延期或調整場次之權利。</p>'))), 3)

    def test_paid_offer_and_unknown_description_are_not_filled_in(self):
        event = dict(EVENT, offers=[{'price':500}])
        with self.assertRaisesRegex(Pending, 'series_offer_price_conflict'):
            self.children(Client(page(event=event)))
        event = dict(EVENT, description='')
        client = Client(page(event=event))
        _, _, row = verify_accupass(self.children(client)[-1], client, NOW)
        self.assertNotIn('在紀念館中體驗', row['activity']['description'])
        self.assertIn('請看官方活動頁', row['activity']['description'])

    def test_forged_candidate_time_rejected_on_fresh_fetch(self):
        child = self.children()[1]
        child['fields']['start_time'] = '2026-09-20T14:00:00+08:00'
        with self.assertRaises(Pending): verify_accupass(child, Client(), NOW)

    def test_pipeline_expands_filters_deduplicates_and_keeps_real_intro(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'data').mkdir(); folder = root/'candidates'; folder.mkdir()
            def write(path, value): (root/path).write_text(json.dumps(value, ensure_ascii=False))
            write('data/verified_activities.json', {'schema_version':1,'sources':{},'activities':[]})
            write('data/ui_taigi.json', {}); write('data/ui_price_taigi.json', {})
            html, evidence = Client().get(URL); candidates = parse_event(html,URL,evidence)
            write('candidates/accupass.json', {'source_id':'accupass','candidates':candidates})
            write('candidates/report.json', {'collected_at':NOW.isoformat(), 'sources':[{'source_id':'accupass','status':'ok','candidate_count':1}]})
            audit = review(folder, root, Client(), NOW, apply=True)
            self.assertEqual(audit['counts'], {'routed':1,'excluded':1,'approved':2})
            catalog = json.loads((root/'data/verified_activities.json').read_text())
            self.assertEqual(len(catalog['activities']), 2)
            self.assertNotIn(EVENT['description'], json.loads((root/'data/ui_taigi.json').read_text()))
            self.assertEqual(review(folder, root, Client(), NOW, apply=True)['counts'], {'duplicate':1})
            self.assertEqual(catalog, json.loads((root/'data/verified_activities.json').read_text()))
            # Owner exclusions take priority over automatic expansion.
            write('data/manual_candidate_decisions.json', {'schema_version':1, 'decisions':[{
                'candidate_id':candidates[0]['id'],'source_id':'accupass','source_url':URL,
                'title':EVENT['name'],'decision':'excluded','reason':'owner_excluded','reviewed_at':NOW.isoformat()}]})
            self.assertEqual(review(folder, root, Client(), NOW, apply=False)['counts'], {'excluded':1})


if __name__ == '__main__': unittest.main()
