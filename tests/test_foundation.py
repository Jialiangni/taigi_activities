import unittest
from datetime import datetime
from html import escape
from crawler.collection import CollectionError, Document
from crawler.sources.li_kang_khiok import LiKangKhiokCrawler

URL = 'https://www.tgb.org.tw/2026/07/829.html'
BODY = '''台語唸歌講座 8/29 拜六14:00-16:00 台北NGO會館
9/20 禮拜14:00-16:00 TCCC 松江館751教室
10/17 拜六14:00-16:00 臺灣圖書館一樓簡報室
講座免費報名 https://forms.gle/8EDj3suDUbHDphvj6 台語使用比例100%'''
NOW = datetime.fromisoformat('2026-09-18T20:00:00+08:00')


def feed(body=BODY, url=URL, extra=''):
    return '''<feed xmlns="http://www.w3.org/2005/Atom"><entry>
<title>臺灣唸歌廳-楊秀卿篇 網站、講座</title><published>2026-08-02T11:24:00+08:00</published>
<link rel="alternate" href="{}"/><content type="html">{}</content></entry>{}</feed>'''.format(url, escape(body), extra)


def article(body=BODY):
    return '<h1>基金會首頁</h1><h3 class="post-title entry-title">唸歌講座</h3><div class="post-body entry-content">' + body + '</div><aside>12/31 相關文章 https://forms.gle/unrelated</aside>'


class FakeClient:
    def __init__(self, xml=None, html=None, error=False):
        self.xml, self.html, self.error = xml or feed(), html or article(), error
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        if '/feeds/' not in url and self.error:
            raise CollectionError('http_503')
        return (self.xml if '/feeds/' in url else self.html), {'url': url, 'final_url': url, 'sha256': 'a'*64}


class FoundationTests(unittest.TestCase):
    def collect(self, client=None, **kwargs):
        return LiKangKhiokCrawler(max_pages=1, now=NOW, **kwargs).collect(client or FakeClient())

    def test_old_post_retains_three_sessions_and_signup_without_publishing(self):
        result = self.collect()
        row = result.candidates[0]
        hints = row['fields']['session_hints']
        self.assertEqual([(h['month'], h['day']) for h in hints], [(8,29), (9,20), (10,17)])
        self.assertTrue(all(h['year'] is None and h['publication_year_hint'] == 2026 for h in hints))
        self.assertIsNone(row['fields']['start_time'])
        self.assertEqual(row['review_status'], 'pending')
        self.assertEqual(row['fields']['registration_links'], ['https://forms.gle/8EDj3suDUbHDphvj6'])
        self.assertEqual(row['evidence']['url'], URL)
        self.assertIn('/feeds/', row['feed_evidence']['url'])
        self.assertEqual(len(result.to_dict()['review_queue']), 1)
        self.assertNotIn('12/31', row['text'])

    def test_article_failure_keeps_feed_body_and_anchor_links(self):
        body = BODY + '<a href="https://example.org/signup">報名</a>'
        result = self.collect(FakeClient(xml=feed(body), error=True))
        row = result.candidates[0]
        self.assertEqual(result.status, 'partial')
        self.assertIn('https://example.org/signup', row['fields']['content_links'])
        self.assertIn('article_detail_unavailable', row['issues'])
        self.assertEqual(len(row['fields']['session_hints']), 3)

    def test_explicit_year_shared_afternoon_time_and_bad_dates(self):
        body = '台語 2026/9/19 拜六 第一場 10/18 禮拜 第二場 時間下晡2:00-4:00 2/30 https://example.org/12/31/'
        row = self.collect(FakeClient(xml=feed(body), html=article(body))).candidates[0]
        hints = row['fields']['session_hints']
        self.assertEqual([(h['year'],h['month'],h['day']) for h in hints], [(2026,9,19),(None,10,18)])
        self.assertIsNone(row['fields']['start_time'])

    def test_upcoming_series_priority_and_detail_budget(self):
        other = feed('台語 2026/1/1 已過期', 'https://www.tgb.org.tw/2026/08/old.html').split('<entry>')[1].split('</entry>')[0]
        client = FakeClient(xml=feed(extra='<entry>'+other+'</entry>'))
        result = self.collect(client, max_details=1)
        self.assertEqual(result.candidates[0]['source_url'], URL)
        self.assertNotIn('https://www.tgb.org.tw/2026/08/old.html', client.urls)
        self.assertIn('article_detail_budget_exhausted', result.candidates[1]['issues'])
        self.assertEqual(len(result.to_dict()['review_queue']), 2)
        self.assertFalse(result.coverage_complete)

    def test_feed_cap_does_not_drop_first_page_series(self):
        client = FakeClient(xml=feed(extra='<link rel="next" href="https://www.blogger.com/feeds/8088173083479680563/posts/default?start-index=51"/>'))
        result = self.collect(client)
        self.assertEqual(result.status, 'partial')
        self.assertIn('feed_page_limit_reached', result.notes)
        self.assertEqual(result.candidates[0]['source_url'], URL)

    def test_foreign_article_never_requested(self):
        client = FakeClient(xml=feed(url='https://example.org/2026/07/829.html'))
        result = self.collect(client)
        self.assertEqual(len(client.urls), 1)
        self.assertEqual(result.errors[0]['code'], 'unapproved_foundation_article')

    def test_blocked_article_never_replaces_feed_with_sidebar(self):
        result = self.collect(FakeClient(html='<h1>Access denied</h1><aside>台語 9/20</aside>'))
        self.assertEqual(result.errors[0]['code'], 'invalid_foundation_article')
        self.assertEqual(len(result.candidates[0]['fields']['session_hints']), 3)

    def test_configured_budget_reaches_collector(self):
        from crawler.collect import collectors
        self.assertEqual(collectors({'limits':{'foundation_details':7}}, ['li_kang_khiok'])['li_kang_khiok'].max_details, 7)
