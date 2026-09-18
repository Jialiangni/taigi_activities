import json
import unittest
from io import BytesIO
from email.message import Message
from urllib.parse import parse_qs, urlsplit
from crawler.collection import Client, CollectionError, Document
from crawler.collect import collectors
from crawler.institutions import registry
from crawler.library_sources import LibraryListingCrawler, listing_page
from crawler.web_sources import WebsiteCrawler

EV = {'sha256': 'a'*64, 'fetched_at':'2026-09-18T12:00:00+08:00'}

class Fake:
    def __init__(self, pages):
        self.pages, self.calls, self.requests = list(pages), [], []
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        item=self.pages.pop(0)
        if isinstance(item, Exception):raise item
        return item, dict(EV, url=url, final_url=url)

def ty_item(area, identifier, title='台語故事'):
    return '<div class="list-item" data-area="'+area+'" data-title="'+title+'"><a href="/zh-tw/Activity/Content/'+identifier+'">'+title+'</a></div>'

class DistrictTests(unittest.TestCase):
    def test_all_54_districts_have_libraries_and_centers(self):
        rows=registry()
        for city,count in [('臺北市',12),('新北市',29),('桃園市',13)]:
            libs={r['district'] for r in rows if r.get('city')==city and r.get('collector')=='library_listing'}
            centers={r['district'] for r in rows if r.get('city')==city and r['group']=='community_centers'}
            self.assertEqual(len(libs),count);self.assertEqual(libs,centers)
        self.assertEqual(len(collectors({},['community_centers'])),54)
        self.assertEqual(len(collectors({},['public_libraries'])),60)
        for r in rows:
            if r.get('listing_type')=='taoyuan':
                q=parse_qs(urlsplit(r['urls'][0]).query,keep_blank_values=True)
                self.assertTrue(all('Filter[{}]'.format(i) in q for i in range(5)))

    def test_three_main_libraries_in_default_collection(self):
        sources=collectors({})
        self.assertIsInstance(sources['tpml_main'],LibraryListingCrawler)
        self.assertIn('n=C4252F536DF57EC4',sources['tpml_main'].spec['urls'][0])
        ntpc=sources['ntpclib_district_220'].spec
        self.assertEqual(ntpc['area_code'],'220')
        self.assertNotIn('branch',parse_qs(urlsplit(ntpc['urls'][0]).query))
        self.assertIn('新北市立圖書館總館',ntpc['aliases'])
        typl=sources['typl_district_2'].spec
        self.assertIn('1',typl['area_codes'])
        self.assertEqual(parse_qs(urlsplit(typl['urls'][0]).query)['Filter[4]'],['2.1'])
        self.assertIn('桃園市立圖書館總館',typl['aliases'])

    def test_ty_real_form_paging_and_no_invented_sessions(self):
        spec={'id':'test','listing_type':'taoyuan','city':'桃園市','district':'復興區','area_codes':['14'],'urls':['https://www.typl.gov.tw/zh-tw/Activity']}
        fake=Fake([ty_item('14','1'),ty_item('14','2'),'<div class="not-found"></div>','<main>台語故事</main>','<main>台語故事</main>'])
        r=LibraryListingCrawler(spec,['台語'],10).collect(fake)
        self.assertEqual(len(r.candidates),2);self.assertEqual(r.status,'ok')
        self.assertEqual(fake.calls[1][1],{'ajax':True,'form':{'CurrentPage':2}})
        self.assertIsNone(r.candidates[0]['fields']['start_time'])
        self.assertNotIn('city',r.candidates[0]['fields'])
        self.assertFalse(r.coverage_complete)

    def test_ignored_filter_and_repeated_page_fail_closed(self):
        spec={'id':'test','listing_type':'taoyuan','city':'桃園市','district':'復興區','area_codes':['14'],'urls':['https://www.typl.gov.tw/zh-tw/Activity']}
        with self.assertRaises(CollectionError):listing_page(ty_item('1','1'),spec['urls'][0],spec)
        fake=Fake([ty_item('14','1'),ty_item('14','1'),'<main>台語故事</main>'])
        r=LibraryListingCrawler(spec,['台語'],10).collect(fake)
        self.assertEqual(r.status,'partial');self.assertIn('library_repeated_listing_page',str(r.errors))

    def test_taipei_numeric_pagination_stays_in_branch(self):
        u='https://reading.tpml.gov.taipei/News.aspx?n=one'
        html='<table><a href="News_Content.aspx?n=one&s=1">台語故事</a></table><a href="News.aspx?n=one&page=2">2</a><a href="News.aspx?n=other&page=2">2</a><a href="https://evil.test/News_Content.aspx?n=one&s=2">台語</a>'
        links,more,_=listing_page(html,u,{'listing_type':'taipei'})
        self.assertEqual(len(links),1);self.assertEqual(len(more),1);self.assertIn('n=one&page=2',more[0][1])

    def test_ntpc_posts_same_area_and_csrf_for_literal_pagechange(self):
        u='https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=239'
        area='<select name="area"><option value="239" selected>鶯歌區</option></select>'
        page=area+'<form id="form1"><input name="csrfToken" value="ephemeral"><input name="pageSize" value="25"></form><a onclick="pagechange(2)">下一頁</a><a href="/singlehtml/ActvInfo?cntId=1">台語</a>'
        fake=Fake([page,area+'<form id="form1"></form>','<main>台語故事</main>'])
        spec={'id':'test','listing_type':'new_taipei','area_code':'239','urls':[u],'city':'新北市','district':'鶯歌區'}
        r=LibraryListingCrawler(spec,['台語'],10).collect(fake)
        self.assertEqual(fake.calls[1][1]['form']['area'],'239')
        self.assertEqual(fake.calls[1][1]['form']['page'],'2')
        self.assertEqual(fake.calls[1][1]['form']['csrfToken'],'ephemeral')
        self.assertEqual(len(r.candidates),1)
        failed=LibraryListingCrawler(spec,['台語'],10).collect(Fake([CollectionError('http_502')]))
        self.assertEqual(failed.status,'failed')

    def test_center_rental_is_not_event_but_actual_event_is_collected(self):
        base='https://www.banqiao.ntpc.gov.tw/'
        fake=Fake(['<a href="home.jsp?dataserno=1">活動中心台語故事</a><a href="home.jsp?dataserno=2">活動中心場地租借</a>', '<h1>活動中心台語故事</h1><main>里民活動中心 台語故事 9/20</main>', '<h1>活動中心場地租借</h1><main>活動中心租借辦法。台語課程可申請</main>'])
        spec={'id':'center','group':'community_centers','urls':[base]}
        r=WebsiteCrawler(spec,['台語'],3).collect(fake)
        self.assertEqual(len(r.candidates),1);self.assertIn('dataserno=1',r.candidates[0]['source_url'])

    def test_government_attachment_query_is_not_parsed_as_html(self):
        base='https://example.org/'
        fake=Fake(['<a href="uploaddowndoc?file=notice.pdf&amp;flag=doc">活動中心台語公告</a><a href="notice.pdf?x=1">台語公告</a>'])
        r=WebsiteCrawler({'id':'test','urls':[base]},['台語'],3).collect(fake)
        self.assertEqual(len(fake.calls),1);self.assertEqual(r.candidates,[])

    def test_deep_government_html_does_not_exhaust_stack(self):
        doc=Document("<div>"*1500+"<main>台語活動中心</main><script>hidden</script>")
        self.assertEqual(doc.content(),"台語活動中心")
        self.assertEqual(len(list(doc.root.all("div"))),1500)

    def test_form_encoding_evidence_redacts_csrf(self):
        class Response(BytesIO):
            status=200;url='https://example.org/list';headers=Message()
        class Opener:
            def open(self,req,timeout):
                self.req=req
                return Response(b'<main>ok</main>')
        client=Client(delay=0);client.opener=Opener()
        _,ev=client.get('https://example.org/list',form={'page':'2','csrfToken':'secret'},ajax=True)
        self.assertEqual(client.opener.req.get_header('Content-type'),'application/x-www-form-urlencoded')
        self.assertIn(b'csrfToken=secret',client.opener.req.data)
        self.assertNotIn('csrfToken',ev['request_form']);self.assertNotIn('secret',json.dumps(ev))
        self.assertEqual(ev['request_method'],'POST')
