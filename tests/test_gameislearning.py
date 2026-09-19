import unittest
from datetime import datetime

from crawler.collection import TAIPEI
from crawler.sources.gameislearning import (GameIsLearningCrawler, choose_registration_url,
                                             parse_detail, sessions_of)


URL = 'https://www.gameislearning.url.tw/taigi-info.php?news=1615lr4vi187'
NOW = datetime.fromisoformat('2026-09-19T10:00:00+08:00')
DETAIL = '''<main><h1>115-2初階台語推廣課程</h1><p>
免費公益課程<br>⏰️115/9/23~11/25共10週次，每週三 PM 6:40~8:40<br>
🏡台北市立圖書館總館11樓 研習教室<br>社團法人台灣台語文化協會 邀請您<br>
即刻開始報名<br>https://www.beclass.com/rid=30528256a95cf1ac73d1<br>
https://liff.line.me/example</p>
<table><tr><td>活動地址</td><td><a href="https://www.google.com/maps/search/x">台北市大安區建國南路二段125號 臺北市立圖書館總館</a></td></tr></table>
<table><tr><td id="titleTD"><a href="https://www.beclass.com/rid=30528256a95cf1ac73d1">來源</a></td></tr></table></main>'''
LISTING = '''<div class="theme"><a href="taigi-info.php?news=1615lr4vi187"><h3>115-2初階台語推廣課程</h3></a>
<span>2026-09-14</span><span>課程 台北市 大安區 免費</span></div>'''


class FakeClient:
    def __init__(self): self.calls = []
    def get(self, url, form=None):
        self.calls.append((url, form))
        if 'taigi-info.php' in url:
            return DETAIL, {'url':url, 'final_url':url, 'sha256':'a'*64,
                            'fetched_at':NOW.isoformat()}
        return LISTING, {'url':url, 'final_url':url, 'sha256':'b'*64,
                         'fetched_at':NOW.isoformat()}


class GameIsLearningTests(unittest.TestCase):
    def test_plain_text_registration_and_recurring_sessions(self):
        row = parse_detail(DETAIL, URL, {'sha256':'a'*64}, {
            'city':'臺北市', 'district':'大安區', 'type':'課程',
            'is_free':True, 'published_at':'2026-09-14'}, NOW)
        self.assertEqual(row['registration_url'], 'https://www.beclass.com/rid=30528256a95cf1ac73d1')
        self.assertEqual(row['city'], '臺北市')
        self.assertEqual(row['district'], '大安區')
        self.assertEqual(row['organizer'], '社團法人台灣台語文化協會')
        self.assertEqual(len(row['sessions']), 10)
        self.assertEqual(row['sessions'][0]['start_time'], '2026-09-23T18:40:00+08:00')
        self.assertEqual(row['sessions'][-1]['start_time'], '2026-11-25T18:40:00+08:00')

    def test_single_date_and_url_priority(self):
        body = '10月4日上午\n時間｜10:30－12:00'
        self.assertEqual(sessions_of(body, '2026-09-15', NOW), [{
            'start_time':'2026-10-04T10:30:00+08:00',
            'end_time':'2026-10-04T12:00:00+08:00'}])
        self.assertEqual(choose_registration_url([
            'https://liff.line.me/help', 'https://forms.gle/signup']), 'https://forms.gle/signup')
        self.assertEqual(sessions_of('場次：2026/10/30 (五) 19:30', '2026-09-15', NOW), [{
            'start_time':'2026-10-30T19:30:00+08:00', 'end_time':None}])
        self.assertEqual(len(sessions_of(
            '每月一次，週六上午 10:00－12:00\n日期：09/19、10/17、11/21、12/19',
            '2026-09-15', NOW)), 4)

    def test_only_detail_poster_is_used_without_guessing_original_url(self):
        image = 'https://files.gameislearning.url.tw/taigi/info-pic/poster.jpg?2'
        page = '<img src="https://files.gameislearning.url.tw/logo.jpg">' + DETAIL
        self.assertEqual(parse_detail(page, URL, {}, now=NOW)['cover_image'], '')
        page += '<img id="myPic" src="' + image + '">'
        self.assertEqual(parse_detail(page, URL, {}, now=NOW)['cover_image'], image)
        self.assertEqual(parse_detail(page.replace(image, '/taigi/info-pic/poster.png'),
                                      URL, {}, now=NOW)['cover_image'],
                         'https://www.gameislearning.url.tw/taigi/info-pic/poster.png')
        for invalid in ('http://files.gameislearning.url.tw/taigi/info-pic/x.jpg',
                        'https://files.gameislearning.url.tw.evil.test/taigi/info-pic/x.jpg',
                        'https://files.gameislearning.url.tw/logo.jpg',
                        'https://files.gameislearning.url.tw:bad/taigi/info-pic/x.jpg',
                        'https://[', 'javascript:alert(1)', ''):
            with self.subTest(url=invalid):
                self.assertEqual(parse_detail(page.replace(image, invalid), URL, {}, now=NOW)['cover_image'], '')

    def test_city_posts_are_collected_as_trusted_session_candidates(self):
        result = GameIsLearningCrawler(max_pages=1, max_details=20, now=NOW).collect(FakeClient())
        self.assertEqual(result.status, 'ok')
        self.assertEqual(len(result.candidates), 10)
        self.assertTrue(all(row['trusted_language_source'] for row in result.candidates))
        self.assertTrue(all(row['kind'] == 'session' for row in result.candidates))
        forms = [form for _, form in FakeClient().calls if form]


if __name__ == '__main__':
    unittest.main()
