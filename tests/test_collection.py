import gzip
import json
import tempfile
import unittest
from unittest.mock import patch
from copy import deepcopy
from email.message import Message
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from crawler.collection import Client, CollectionError, Document, Result, canonical, city_of, local_time
from crawler.culture import parse_culture
from crawler.collect import collectors, run
from crawler.social import read_pages
from crawler.web_sources import WebsiteCrawler, FeedCrawler, parse_feed
from crawler.sources.tmofa import parse_home
from crawler.sources.accupass import parse_event, AccupassCrawler
from crawler.sources.opentix import parse_program, OpentixCrawler
from crawler.sources.eraticket import parse_era
from crawler.sources.facebook import FacebookCrawler
from crawler.sources.instagram import InstagramCrawler
from crawler.sources.threads import ThreadsCrawler

FIX = Path(__file__).parent / 'fixtures'
EV = {'url': 'https://example.org/feed', 'sha256': 'a' * 64, 'fetched_at': '2026-09-18T12:00:00+08:00'}


class MockClient:
    def __init__(self, jsons=None, pages=None):
        self.jsons, self.pages = list(jsons or []), dict(pages or {})
        self.calls, self.requests = [], []

    def json(self, url, payload=None, token=None):
        self.calls.append((url, payload, token))
        result = self.jsons.pop(0)
        if isinstance(result, Exception):
            raise result
        return result, dict(EV, url=url)

    def get(self, url):
        value = self.pages[url]
        if isinstance(value, Exception):
            raise value
        return value, dict(EV, url=url, final_url=url)


class CollectionTests(unittest.TestCase):
    def test_live_accupass_fixture_is_period_not_certified_session(self):
        rows = parse_event((FIX / 'accupass_event.html').read_text(), 'https://www.accupass.com/event/1', EV)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r['fields']['start_time'], '2026-10-11T10:00:00+08:00')
        self.assertEqual(r['fields']['city'], '桃園市')
        self.assertEqual(r['kind'], 'event_period')
        self.assertIsNone(r['fields']['is_free'])
        self.assertEqual(r['review_status'], 'pending')

    def test_live_opentix_fixture_keeps_distinct_session_ids(self):
        program = json.loads((FIX / 'opentix_program.json').read_text())
        rows = parse_program(program, EV)
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]['id'], rows[1]['id'])
        self.assertEqual(rows[0]['fields']['start_time'], rows[1]['fields']['start_time'])
        self.assertEqual(rows[0]['fields']['city'], '臺北市')
        self.assertIsNone(rows[0]['fields']['is_free'])
        group = deepcopy(program['eventVenues'][0])
        group['venue']['city'] = '高雄市'
        program['eventVenues'].append(group)
        self.assertEqual(len(parse_program(program, EV)), 2)

    def test_missing_or_mixed_prices_not_invented(self):
        p = json.loads((FIX / 'opentix_program.json').read_text())
        event = p['eventVenues'][0]['events'][0]
        event.pop('startDateTime')
        event['groupSections'] = {'default': [{'price': 0}, {'price': 200}]}
        row = parse_program(p, EV)[0]
        self.assertIsNone(row['fields']['start_time'])
        self.assertIsNone(row['fields']['is_free'])
        self.assertIn('missing_start_time', row['issues'])

    def test_live_era_table_keeps_dates_and_unknown_end(self):
        rows = parse_era((FIX / 'era_session.html').read_text(), 'https://ticket.com.tw/example', EV)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['fields']['start_time'], '2026-12-26T18:00:00+08:00')
        self.assertIsNone(rows[0]['fields']['end_time'])
        self.assertIsNone(rows[0]['fields']['city'])  # Taichung cannot silently become Taipei.

    def test_accupass_real_post_shape_and_pagination(self):
        fake = MockClient(jsons=[{'total': 2, 'items': [{'eventIdNumber': '1'}]},
                                 {'total': 2, 'items': [{'eventIdNumber': '2'}]}],
                          pages={f'https://www.accupass.com/event/{i}': (FIX / 'accupass_event.html').read_text() for i in [1, 2]})
        r = AccupassCrawler(['台語']).collect(fake)
        self.assertEqual(len(r.candidates), 2)
        self.assertEqual([x[1]['currentIndex'] for x in fake.calls], [0, 1])
        self.assertEqual(fake.calls[0][1]['cityLocationList'], ['1', '2', '3'])
        self.assertEqual(r.status, 'ok')

    def test_opentix_uses_returned_offset_and_detail_api(self):
        program = json.loads((FIX / 'opentix_program.json').read_text())
        fake = MockClient(jsons=[{'result': {'found': [{'source': {'id': program['id'], 'title': '台語'}}], 'nextOffset': 15}},
                                 {'result': {'found': [], 'nextOffset': None}}, {'result': program}])
        r = OpentixCrawler(['台語']).collect(fake)
        self.assertEqual(len(r.candidates), 2)
        self.assertEqual(fake.calls[1][1]['offset'], 15)
        self.assertEqual(fake.calls[0][1]['cityFilter'], ['臺北', '新北', '桃園'])
        self.assertIn('csm.api.opentix.life/programs/', fake.calls[2][0])

    def test_accupass_broad_search_hits_need_actual_detail_keyword(self):
        html = '<script type="application/ld+json">{"@type":"Event","name":"英文課程"}</script><main>英文閱讀</main>'
        client = MockClient(jsons=[{'total': 1, 'items': [{'eventIdNumber': '1'}]}],
                            pages={'https://www.accupass.com/event/1': html})
        result = AccupassCrawler(['台語']).collect(client)
        self.assertEqual(result.candidates, [])
        self.assertIn('detail_pages_without_exact_keyword=1', result.notes)

    def test_bad_search_and_repeated_pages_are_explicit_errors(self):
        for payload in [{}, {'total': 10, 'items': []}]:
            r = AccupassCrawler(['台語']).collect(MockClient(jsons=[payload]))
            self.assertEqual(r.status, 'failed')
            self.assertTrue(r.errors)
        r = AccupassCrawler(['台語']).collect(MockClient(jsons=[
            {'total': 2, 'items': [{'eventIdNumber': '1'}]},
            {'total': 2, 'items': [{'eventIdNumber': '1'}]}],
            pages={'https://www.accupass.com/event/1': CollectionError('http_404')}))
        self.assertIn('invalid_or_repeated_search_page', [e['code'] for e in r.errors])

    def test_culture_sessions_and_not_on_sale_is_not_free(self):
        item = {'UID': 'a', 'title': '台語故事', 'descriptionFilterHtml': '親子共學',
                'masterUnit': ['桃園市立圖書館'], 'showInfo': [
                    {'time': '2026/10/11 10:00:00', 'endTime': '2026/10/11 12:00:00',
                     'location': '桃園市桃園區', 'locationName': '總館', 'onSales': 'N', 'price': ''},
                    {'time': '2026/10/12 10:00:00', 'location': '臺中市', 'locationName': '某館'}]}
        rows = parse_culture([item], EV, ['台語'], [{'id': 'typl', 'aliases': ['桃園市立圖書館']}])
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]['fields']['is_free'])
        self.assertEqual(rows[0]['matched_sources'], ['typl'])
        self.assertEqual(rows[0]['fields']['end_time'], '2026-10-11T12:00:00+08:00')

    def test_atom_rss_and_opensearch_pagination(self):
        atom = '''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:o="http://a">
        <o:totalResults>100</o:totalResults><o:startIndex>1</o:startIndex><o:itemsPerPage>50</o:itemsPerPage>
        <entry><title>台語故事</title><link rel="alternate" href="https://example.org/post/1"/>
        <published>2026-09-01T01:00:00Z</published><content>十月活動詳見公告</content></entry></feed>'''
        rows, more = parse_feed(atom, 'test', EV, ['台語'])
        self.assertEqual(rows[0]['fields']['published_at'], '2026-09-01T01:00:00Z')
        self.assertIsNone(rows[0]['fields']['start_time'])
        self.assertIn('start-index=51', more[0])
        rss = '<rss><channel><item><title>台語故事</title><link>https://example.org/2</link><description>故事會</description></item></channel></rss>'
        self.assertEqual(len(parse_feed(rss, 'test', EV, ['台語'])[0]), 1)
        with self.assertRaises(CollectionError):
            parse_feed('<html>login</html>', 'test', EV, ['台語'])

    def test_website_follows_activity_link_without_treating_home_as_event(self):
        spec = {'id': 'site', 'urls': ['https://example.org/']}
        client = MockClient(pages={'https://example.org/': '<h1>機構</h1><a href="/News_Content?s=1">台語親子活動</a>',
            'https://example.org/News_Content?s=1': '<h1>機構</h1><main>台語活動 10月11日</main>'})
        result = WebsiteCrawler(spec, ['台語'], 5).collect(client)
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0]['title'], '台語親子活動')
        self.assertIsNone(result.candidates[0]['fields']['start_time'])
        self.assertFalse(result.coverage_complete)

    def test_feed_approved_publisher_mirror_and_unknown_host(self):
        first = 'https://example.org/feed'
        mirror = 'https://publisher.example/feeds/123'
        atom = '<feed xmlns="http://www.w3.org/2005/Atom"><link rel="next" href="' + mirror + '?start-index=51"/></feed>'
        fake = MockClient(pages={first: atom, mirror + '?start-index=51': '<feed/>'})
        result = FeedCrawler('test', first, ['台語'], feed_mirrors=(mirror,)).collect(fake)
        self.assertEqual(result.status, 'ok')
        result = FeedCrawler('test', first, ['台語']).collect(fake)
        self.assertEqual(result.errors[0]['code'], 'unapproved_feed_paging_host')

    def test_tmofa_embedded_announcements_keep_unknown_event_time(self):
        item = {'id': 633, 'lang': 'ch', 'state': 1, 'title': '台語閱讀',
                'content': '<p>親子共讀</p>', 'publish_up': '2026-09-01'}
        data = {'props': {'pageProps': {'news': [item, dict(item, id=634, lang='en')], 'info': []}}}
        html = '<script id="__NEXT_DATA__" type="application/json">' + json.dumps(data) + '</script>'
        rows, counts = parse_home(html, EV, ['台語'])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['source_url'], 'https://tmofa.tycg.gov.tw/ch/news/latest-news/633')
        self.assertIsNone(rows[0]['fields']['start_time'])
        self.assertEqual(rows[0]['fields']['published_at'], '2026-09-01')
        with self.assertRaises(CollectionError):
            parse_home('<html>challenge</html>', EV, ['台語'])

    def test_social_missing_auth_is_not_empty_success(self):
        for crawler in (FacebookCrawler(env={}), InstagramCrawler(env={}), ThreadsCrawler(env={})):
            result = crawler.collect(MockClient())
            self.assertEqual(result.status, 'needs_configuration')

    def test_social_post_time_never_becomes_event_time(self):
        fake = MockClient(jsons=[{'data': [{'id': '1', 'message': '台語講座', 'permalink_url': 'https://www.facebook.com/1', 'created_time': '2026-09-01'}]}])
        result = FacebookCrawler(['台語'], env={'FACEBOOK_ACCESS_TOKEN': 'SECRET', 'FACEBOOK_PAGE_IDS': '123'}).collect(fake)
        self.assertIsNone(result.candidates[0]['fields']['start_time'])
        self.assertEqual(result.candidates[0]['fields']['published_at'], '2026-09-01')
        self.assertNotIn('SECRET', json.dumps(result.to_dict()))
        self.assertNotIn('SECRET', fake.calls[0][0])

    def test_instagram_user_id_on_both_requests_and_timestamp_separate(self):
        fake = MockClient(jsons=[{'data': [{'id': '22'}]}, {'data': [{'id': '1', 'caption': '台語', 'permalink': 'https://www.instagram.com/p/a', 'timestamp': 123}]}])
        result = InstagramCrawler(['台語'], env={'INSTAGRAM_ACCESS_TOKEN': 'SECRET', 'INSTAGRAM_USER_ID': '123'}).collect(fake)
        self.assertTrue(all('user_id=123' in c[0] for c in fake.calls))
        self.assertIsNone(result.candidates[0]['fields']['start_time'])
        self.assertEqual(result.candidates[0]['fields']['published_at'], 123)

    def test_instagram_same_cursor_with_new_page_is_supported(self):
        page = lambda id, more: {'data': [{'id': id}], 'paging': {'next': 'https://graph.facebook.com/next?after=A', 'cursors': {'after': 'A'}} if more else {}}
        fake = MockClient(jsons=[page('1', True), page('2', True), page('3', False)])
        rows = list(read_pages(fake, 'https://graph.facebook.com/v26.0/22/recent_media', {}, 'SECRET', 5, True))
        self.assertEqual(len(rows), 3)
        fake = MockClient(jsons=[page('1', True), page('1', True)])
        with self.assertRaises(CollectionError):
            list(read_pages(fake, 'https://graph.facebook.com/x', {}, 'SECRET', 5, True))

    def test_social_paging_cannot_exfiltrate_token(self):
        fake = MockClient(jsons=[{'data': [], 'paging': {'next': 'https://evil.example/steal?after=x'}}])
        with self.assertRaises(CollectionError):
            list(read_pages(fake, 'https://graph.facebook.com/x', {}, 'SECRET', 5))
        self.assertEqual(len(fake.calls), 1)

    def test_threads_current_documented_host_and_parameters(self):
        fake = MockClient(jsons=[{'data': []}])
        r = ThreadsCrawler(['台語'], env={'THREADS_ACCESS_TOKEN': 'SECRET'}).collect(fake)
        self.assertEqual(r.status, 'ok')
        self.assertTrue(fake.calls[0][0].startswith('https://graph.threads.com/v1.0/keyword_search?'))
        self.assertIn('search_type=RECENT', fake.calls[0][0])

    def test_registry_covers_every_group_and_no_legacy_activity_fallback(self):
        all_sources = collectors({})
        self.assertEqual(len(all_sources), 50)
        for required in ['accupass', 'opentix', 'eraticket', 'li_kang_khiok', 'le_chang', 'facebook', 'instagram', 'threads', 'tpml', 'ntpclib', 'typl', 'tfam', 'gold', 'ty_youth', 'ntl', 'yingge_library', 'taigiloo', 'dadaocheng', '228_national']:
            self.assertIn(required, all_sources)
        with self.assertRaises(CollectionError):
            all_sources['accupass'].fetch_activities()

    def test_canonical_unicode_and_no_invented_dates(self):
        self.assertEqual(canonical('https://example.org/台語?q=台語'), 'https://example.org/%E5%8F%B0%E8%AA%9E?q=%E5%8F%B0%E8%AA%9E')
        self.assertIsNone(local_time('2026-09-18'))
        self.assertIsNone(local_time(None))
        self.assertIsNone(city_of('未知地點'))
        self.assertEqual(local_time('2026-09-18T00:00:00Z'), '2026-09-18T08:00:00+08:00')

    def test_gzip_response(self):
        class Response:
            status, url = 200, 'https://example.org/api'
            headers = Message()
            headers['Content-Encoding'] = 'gzip'
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size): return gzip.compress(b'{"items":[]}')
        class Opener:
            def open(self, *args, **kwargs): return Response()
        client = Client(delay=0)
        client.opener = Opener()
        data, ev = client.json('https://example.org/api')
        self.assertEqual(data, {'items': []})

    def test_runner_preserves_other_source_reports_after_failure(self):
        class Good:
            def collect(self, client): return Result('good', 'fixture')
        class Bad:
            def collect(self, client): raise CollectionError('http_503')
        with tempfile.TemporaryDirectory() as tmp, patch('crawler.collect.collectors', return_value={'good': Good(), 'bad': Bad()}):
            report = run({'workers': 2}, tmp, client_factory=MockClient)
            self.assertFalse(report['publication_changed'])
            self.assertEqual({r['source_id']: r['status'] for r in report['sources']}, {'good': 'ok', 'bad': 'failed'})
            self.assertTrue((Path(tmp) / 'good.json').exists())
            failed = json.loads((Path(tmp) / 'bad.json').read_text())
            self.assertEqual(failed['errors'][0]['code'], 'http_503')
            self.assertIn('completed_at', failed)


if __name__ == '__main__':
    unittest.main()
