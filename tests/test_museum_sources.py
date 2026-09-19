import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from crawler.web_sources import WebsiteCrawler, culture_portal_detail
from crawler.resources import load_resources
from crawler.sources.tfam import parse_events
from crawler.collection import CollectionError, Document
from crawler.verified import check_source_content, load_verified
from build_html import generate_single_html
from test_collection import MockClient


class MuseumTests(unittest.TestCase):
    def test_known_service_is_collected_at_depth_zero_without_invented_session(self):
        u = 'https://example.org/guide'
        spec = {'id': 'museum', 'urls': ['https://example.org/'], 'known_pages': [
            {'url': u, 'title': '常設展導覽', 'kind': 'guide_service'}]}
        r = WebsiteCrawler(spec, ['台語']).collect(MockClient(pages={u: '<main>台語語音導覽</main>', 'https://example.org/': '<h1>台語博物館</h1>'}))
        self.assertEqual(len(r.candidates), 1)
        self.assertEqual(r.candidates[0]['kind'], 'guide_service')
        self.assertIsNone(r.candidates[0]['fields']['start_time'])

    def test_real_museum_paths_and_sign_language_not_taigi(self):
        for path in ['/Event/Event_page.aspx?id=12', '/tw/ExhibitionAndEvent/Info/test', '/wSite/ct?xItem=1']:
            u = 'https://example.org' + path
            fake = MockClient(pages={'https://example.org/': '<a href="'+path+'">導覽</a>', u: '<main>台語導覽 2021年1月23日</main>'})
            r = WebsiteCrawler({'id': 'museum', 'urls': ['https://example.org/']}, ['台語']).collect(fake)
            self.assertEqual(len(r.candidates), 1)
            self.assertIsNone(r.candidates[0]['fields']['start_time'])
            fake.pages[u] = '<main>手語導覽 2026年10月24日</main>'
            self.assertEqual(WebsiteCrawler({'id': 'museum', 'urls': ['https://example.org/']}, ['台語']).collect(fake).candidates, [])

    def test_resource_expiry_and_no_calendar_fields(self):
        rows = load_resources(now=datetime.fromisoformat('2026-09-18T23:59:59+08:00'))
        self.assertEqual(len(rows), 9)
        self.assertTrue(all('start_time' not in r for r in rows))
        self.assertEqual(len(load_resources(now=datetime.fromisoformat('2026-12-07T00:00:00+08:00'))), 7)
        with self.assertRaises(ValueError):
            check_source_content(rows[0], '<p>展覽已結束，原台語資訊已移除</p>')

    def test_resources_are_visible_and_html_escaped(self):
        rows = load_resources(now=datetime.fromisoformat('2026-09-18T23:59:59+08:00'))
        rows[0]['title'] = '<script>alert(1)</script>'
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'index.html'
            generate_single_html([], p, resources=rows)
            html = p.read_text()
        self.assertIn('台語導覽、展覽佮閱讀資訊', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>alert(1)</script>', html)

    def test_library_resources_are_not_audio_guides_or_calendar_sessions(self):
        rows = load_resources(now=datetime.fromisoformat('2026-09-18T23:59:59+08:00'))
        libraries = [r for r in rows if r['id'].startswith('tpml_')]
        self.assertEqual(len(libraries), 4)
        self.assertEqual({r['kind'] for r in libraries}, {'exhibition_resource', 'reading_resource'})
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'index.html'
            generate_single_html([], p, resources=libraries)
            html = p.read_text()
        self.assertIn('台語閱讀推廣', html)
        self.assertIn('台語相關展覽', html)
        self.assertNotIn('展覽與台語語音導覽', html)
        at_october = load_resources(now=datetime.fromisoformat('2026-10-01T00:00:00+08:00'))
        self.assertNotIn('tpml_xiyuan_reading', {r['id'] for r in at_october})
        at_new_year = load_resources(now=datetime.fromisoformat('2027-01-01T00:00:00+08:00'))
        self.assertFalse(any(r['id'].startswith('tpml_') for r in at_new_year))

    def test_taigiloo_story_uses_explicit_dates_not_week_rule(self):
        events = load_verified(Path(__file__).parent / 'fixtures/verified_catalog_20260918.json', now=datetime.fromisoformat('2026-09-18T23:59:59+08:00'))
        rows = [a for a in events if a.id.startswith('ntl_taigiloo_')]
        self.assertEqual([a.start_time[:10] for a in rows], ['2026-10-15', '2026-11-19', '2026-12-17'])
        self.assertTrue(all(a.end_time[11:16] == '11:50' and a.is_free is None for a in rows))

    def test_tfam_json_filters_language_and_rejects_changed_schema(self):
        payload = {'Status': '1', 'Data': [
            {'EduID': 1, 'EduName': '台語導覽', 'Content': '<p>每月場次另公告</p>'},
            {'EduID': 2, 'EduName': '手語聽賞', 'Content': '<p>手語翻譯</p>'}]}
        rows = parse_events(payload, {}, ['台語', '臺語'])
        self.assertEqual(len(rows), 1)
        self.assertIn('id=1', rows[0]['source_url'])
        self.assertIsNone(rows[0]['fields']['start_time'])
        with self.assertRaises(CollectionError):
            parse_events({'Status': '0', 'Data': []}, {}, ['台語'])

    def test_portal_related_activity_is_not_language_evidence(self):
        html = """<h1>logo</h1><div class="title_01">化石展</div><p>華語展覽</p><h2>相關系列活動</h2><a onclick="viewDetail('123');">台語講座</a>"""
        title, body, links = culture_portal_detail(Document(html), 'https://event.culture.tw/mocweb/reg/NTM/Detail.init.ctr?actId=2')
        self.assertEqual(title, '化石展')
        self.assertNotIn('台語', body)
        self.assertEqual(links[0][0], 'https://event.culture.tw/mocweb/reg/NTM/Detail.init.ctr?actId=123')
