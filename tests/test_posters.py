import json
import unittest
from datetime import datetime
from unittest.mock import patch
from pathlib import Path

from crawler.posters import image_url, poster_url
from crawler.verified import load_verified
from crawler.sources.accupass import parse_event
from crawler.sources.tfam import parse_events
from crawler.sources.tmofa import parse_home


class PosterTests(unittest.TestCase):
    def test_accupass_event_image_excludes_avatars_and_recommendations(self):
        url = 'https://www.accupass.com/event/123'
        html = '<img src="https://static.accupass.com/userupload/avatar.jpg">'
        html += '<script type="application/ld+json">' + json.dumps({
            '@type':'Event', 'url':url, 'name':'台語活動',
            'image':{'@type':'ImageObject','url':'https://static.accupass.com/eventbanner/poster.jpg'}}) + '</script>'
        html += '<script type="application/ld+json">' + json.dumps({
            '@type':'Event', 'url':'https://www.accupass.com/event/other',
            'image':'https://static.accupass.com/eventbanner/other.jpg'}) + '</script>'
        self.assertEqual(poster_url(html, url), 'https://static.accupass.com/eventbanner/poster.jpg')
        self.assertEqual(parse_event(html, url, {})[0]['fields']['cover_image'], poster_url(html, url))
        self.assertEqual(poster_url(html.replace(url+'"', url+'0"'),url), '')

    def test_foundation_uses_full_size_article_image_only(self):
        html = '<header><img src="/header.jpg"></header><div class="post-body">'
        html += '<a href="https://blogger.googleusercontent.com/s1200/poster.jpg"><img src="https://blogger.googleusercontent.com/s640/poster.jpg"></a></div>'
        html += '<article class="related"><img src="/unrelated.jpg"></article>'
        self.assertEqual(poster_url(html, 'https://www.tgb.org.tw/2026/09/story.html'),
                         'https://blogger.googleusercontent.com/s1200/poster.jpg')

    def test_library_main_image_is_bound_to_current_activity_id(self):
        html = '<img src="/FileUploads/Activity/999.JPG"><img src="/FileUploads/Activity/123.JPG">'
        self.assertEqual(poster_url(html, 'https://www.typl.gov.tw/zh-tw/Activity/Content/123'),
                         'https://www.typl.gov.tw/FileUploads/Activity/123.JPG')

    def test_lazy_library_image_and_poster_attachment(self):
        url = 'https://www.ntl.edu.tw/wSite/ct?xItem=123'
        self.assertEqual(poster_url('<section class="cp"><img data-src="public/Img/poster.jpg"></section>',url),
                         'https://www.ntl.edu.tw/wSite/public/Img/poster.jpg')
        self.assertEqual(poster_url('<article><a href="/upload/poster.png">下載活動海報</a></article>',url),
                         'https://www.ntl.edu.tw/upload/poster.png')

    def test_museum_carousel_excludes_related_activity(self):
        html = '<div id="carouselExampleIndicators"><a href="/userFiles/poster.jpg"><img src="/userFiles/thumb.jpg"></a></div>'
        html += '<div class="related"><img src="/userFiles/other.jpg"></div>'
        self.assertEqual(poster_url(html,'https://event.culture.tw/mocweb/reg/NTM/Detail.init.ctr?actId=1'),
                         'https://event.culture.tw/userFiles/poster.jpg')

    def test_art_museum_public_dataset_preserves_content_image(self):
        tfam = {'Status':'1','Data':[{'EduID':1,'EduName':'台語活動',
                 'Content':'<p><img src="/upload/poster.jpg"></p>'}]}
        self.assertEqual(parse_events(tfam,{},['台語'])[0]['fields']['cover_image'],
                         'https://www.tfam.museum/upload/poster.jpg')
        tfam['Data'][0]['PlayImg'] = 'Edu\\Main\\1\\poster.jpg'
        self.assertEqual(parse_events(tfam,{},['台語'])[0]['fields']['cover_image'],
                         'https://www.tfam.museum/File/Edu/Main/1/poster.jpg')
        self.assertEqual(poster_url('<div id="divImgs"><img src="/File/Event/Image/poster.jpg"></div>',
                         'https://www.tfam.museum/Event/Event_page.aspx?id=1'),
                         'https://www.tfam.museum/File/Event/Image/poster.jpg')
        data = {'props':{'pageProps':{'news':[{'id':1,'lang':'ch','title':'台語活動',
                      'content':'<img src="/upload/poster.jpg">'}],'info':[]}}}
        rows,_ = parse_home('<script id="__NEXT_DATA__">'+json.dumps(data)+'</script>',{},['台語'])
        self.assertEqual(rows[0]['fields']['cover_image'],'https://tmofa.tycg.gov.tw/upload/poster.jpg')

    def test_no_image_never_falls_back_to_site_logo_or_decorations(self):
        html = '<meta property="og:image" content="/default.jpg"><header><img src="/logo.png"></header>'
        html += '<article><img src="/emoji/smile.png"><img width="16" height="16" src="/tiny.png"><aside><img src="/ad.jpg"></aside></article>'
        self.assertEqual(poster_url(html,'https://reading.tpml.gov.taipei/News_Content.aspx?s=1'),'')
        self.assertEqual(poster_url('<article class="related"><img src="/other.jpg"><a href="/other.png">海報</a></article>',
                         'https://example.org/event/1'),'')
        self.assertEqual(poster_url('<article><img src="/img/TitleText.png"><img src="/images/ageRange.png"></article>',
                         'https://atpass.ntpclib.gov.tw/activities/detail?cntId=1'),'')

    def test_image_urls_are_https_encoded_and_never_executable(self):
        for value in ('javascript:alert(1)','data:image/png;base64,AA','http://example.org/p.jpg',
                      'https://user:pass@example.org/p.jpg','https://[','https://example.org:8080/p.jpg'):
            self.assertEqual(image_url(value,'https://example.org/event/1'),'')
        self.assertEqual(image_url('/upload/海報 1.jpg','https://example.org/event/1'),
                         'https://example.org/upload/%E6%B5%B7%E5%A0%B1%201.jpg')

    def test_live_build_refreshes_posters_without_changing_sessions(self):
        fixture=Path(__file__).parent/'fixtures/verified_catalog_base.json'
        now = datetime.fromisoformat('2026-09-18T23:59:59+08:00')
        old=load_verified(fixture, now=now)
        proof={'url':'https://example.org/new.jpg','checked_at':'2026-09-18T23:59:00+08:00'}
        with patch('crawler.verified.check_live_sources', return_value={old[0].source_url:proof}):
            new=load_verified(fixture, now=now,check_sources=True)
        self.assertEqual(new[0].cover_image,proof['url'])
        self.assertEqual([(a.id,a.start_time,a.end_time) for a in old],[(a.id,a.start_time,a.end_time) for a in new])
        with patch('crawler.verified.check_live_sources', return_value={old[0].source_url:dict(proof,url='')}):
            new=load_verified(fixture,now=now,check_sources=True)
        self.assertEqual(new[0].cover_image,'')


if __name__ == '__main__':
    unittest.main()
