import copy
import unittest
from datetime import datetime

from crawler.collection import CollectionError
from crawler.review import Pending, validate_auto_source, verify_gameislearning
from crawler.sources.gameislearning import GameIsLearningCrawler, parse_detail, supplement_registration


NOW = datetime.fromisoformat('2026-09-19T10:00:00+08:00')
URL = 'https://www.gameislearning.url.tw/taigi-info.php?news=story123'
FORM_URL = 'https://docs.google.com/forms/d/example/viewform'
DETAIL = '''<h1>2026年古錐ê講古</h1><p>日期：09月20日（星期日）<br>
地點：喜憨兒南門公園商店<br>https://ppt.cc/example</p>
<table><tr><td>活動地址</td><td><a href="https://maps.google.com/">桃園市桃園區三民路264號 喜憨兒南門公園商店</a></td></tr></table>'''
FORM = '''<title>2026.09.20古錐ê講古｜免費台語繪本活動報名表</title>
<div>地點：喜憨兒南門公園商店。第一場10:30–11:20；第二場11:30–12:20。</div>
<div role="listitem"><div role="heading">參加的場次？</div>
<div role="radio" data-value="第一場10:30-11:20">第一場10:30-11:20</div>
<div role="radio" data-value="第二場11:30-12:20">第二場11:30-12:20</div>
<div role="radio" data-value="兩場都參加10:30-12:20">兩場都參加10:30-12:20</div></div>'''


class Client:
    def __init__(self, form=FORM):
        self.form, self.calls, self.fail = form, [], False
        self.final = FORM_URL

    def get(self, url, form=None):
        self.calls.append(url)
        if url == URL:
            page, final = DETAIL, URL
        elif url == 'https://ppt.cc/example':
            if self.fail:
                raise CollectionError('http_503')
            page, final = self.form, self.final
        else:
            page = '<div class="theme"><a href="' + URL + '"><h3>2026年古錐ê講古</h3></a>2026-09-18 桃園市 桃園區 親子 免費</div>'
            final = url
        return page, {'final_url': final, 'fetched_at': NOW.isoformat(), 'sha256': 'a'*64}


class RegistrationSessionTests(unittest.TestCase):
    def parsed(self):
        return parse_detail(DETAIL, URL, {}, {'is_free': True}, NOW)

    def test_month_day_follows_form_and_excludes_combined_booking(self):
        self.assertEqual(self.parsed()['sessions'], [])
        parsed = supplement_registration(self.parsed(), Client())
        self.assertEqual([s['start_time'] for s in parsed['sessions']],
                         ['2026-09-20T10:30:00+08:00', '2026-09-20T11:30:00+08:00'])
        self.assertEqual([s['end_time'][11:16] for s in parsed['sessions']], ['11:20', '12:20'])

    def test_conflicting_end_retains_certain_start_and_other_session(self):
        client = Client(FORM + '<p>第一場10:30–11:30</p>')
        rows = supplement_registration(self.parsed(), client)['sessions']
        self.assertIsNone(rows[0]['end_time'])
        self.assertEqual(rows[0]['end_time_variants'],
                         ['2026-09-20T11:20:00+08:00', '2026-09-20T11:30:00+08:00'])
        self.assertEqual(rows[1]['end_time'], '2026-09-20T12:20:00+08:00')

    def test_wrong_date_year_venue_and_unsupported_form_rejected(self):
        for form in (FORM.replace('2026.09.20', '2026.09.21'),
                     FORM.replace('2026.09.20', '2027.09.20'),
                     FORM.replace('2026.09.20', '09.20'),
                     FORM.replace('喜憨兒南門公園商店', '另一個地點'),
                     FORM.replace('古錐ê講古', '完全不同的活動')):
            with self.subTest(form=form), self.assertRaises(CollectionError):
                supplement_registration(self.parsed(), Client(form))
        for final in ('https://docs.google.com.evil.test/forms/d/example/viewform',
                      'http://docs.google.com/forms/d/example/viewform'):
            client = Client()
            client.final = final
            with self.assertRaises(CollectionError):
                supplement_registration(self.parsed(), client)

    def test_visible_description_also_supports_sessions_without_choice_question(self):
        parsed = supplement_registration(self.parsed(), Client(FORM.replace('參加的場次','其他問題')))
        self.assertEqual([s['start_time'][11:16] for s in parsed['sessions']], ['10:30','11:30'])
        self.assertEqual(parsed['registration_evidence']['method'], 'public_text_v2')

    def test_collector_failure_preserves_candidate_and_success_splits_two(self):
        collector = GameIsLearningCrawler(max_pages=1, now=NOW)
        client = Client()
        result = collector.collect(client)
        self.assertEqual(len(result.candidates), 2)
        self.assertTrue(all(c['kind'] == 'session' for c in result.candidates))
        client.fail = True
        result = collector.collect(client)
        self.assertEqual(len(result.candidates), 1)
        self.assertIn('http_503', result.candidates[0]['issues'])

    def test_review_and_future_build_recheck_form_evidence(self):
        client = Client(FORM + '<p>第一場10:30–11:30</p>')
        candidate = GameIsLearningCrawler(max_pages=1, now=NOW).collect(client).candidates[0]
        _, source, row = verify_gameislearning(candidate, client, NOW)
        self.assertIsNone(row['activity']['end_time'])
        self.assertIn('結束時間有不同記載', row['activity']['description'])
        self.assertEqual(source['automated_review']['registration_evidence']['final_url'], FORM_URL)
        validate_auto_source(source, None, DETAIL, client=client)
        forged = copy.deepcopy(candidate)
        forged['fields']['start_time'] = '2026-09-20T09:30:00+08:00'
        with self.assertRaises(Pending):
            verify_gameislearning(forged, client, NOW)
        client.form = client.form.replace('10:30–11:30', '10:30–11:40')
        with self.assertRaises(Pending):
            validate_auto_source(source, None, DETAIL, client=client)
        client.fail = True
        with self.assertRaises(CollectionError):
            validate_auto_source(source, None, DETAIL, client=client)


if __name__ == '__main__':
    unittest.main()
