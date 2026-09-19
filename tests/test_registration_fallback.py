import copy
import shutil
from pathlib import Path
import unittest
from datetime import datetime
from unittest.mock import patch
from urllib.request import Request

from crawler.collection import Client as HTTPClient, CollectionError, SafeRedirect
from crawler.registration import resolve_registration, supported_url
from crawler.poster_ocr import (supplement_activity, poster_sessions, tsv_lines, PosterRedirect)
from crawler.sources.gameislearning import parse_detail
from crawler.review import verify_gameislearning, validate_auto_source, Pending

NOW = datetime.fromisoformat('2026-09-19T21:00:00+08:00')
URL = 'https://www.gameislearning.url.tw/taigi-info.php?news=ocr123'
FORM = 'https://docs.google.com/forms/d/test/viewform'
LINK = 'https://linktr.ee/story'
IMAGE = 'https://files.gameislearning.url.tw/taigi/info-pic/test.jpg'
DETAIL = '<h1>2026年古錐親子講古</h1><p>日期：10月04日（星期日）<br>地點：故事圖書館<br>https://linktr.ee/story</p><table><tr><td>活動地址</td><td><a href="https://maps.google.com/">臺北市中山區一號 故事圖書館</a></td></tr></table><img id="myPic" src="'+IMAGE+'">'
PAGE = '<title>古錐親子講古報名表</title><div>地點：故事圖書館</div><div>活動日期：2026/10/04（日）</div><div>活動時間：10:30-12:00</div>'


def parsed(): return parse_detail(DETAIL, URL, {}, {'is_free':True}, NOW)


class Client:
    def __init__(self, pages=None):
        self.pages = pages or {LINK:'<a href="'+FORM+'">報名</a>', FORM:PAGE, URL:DETAIL}
        self.calls = []
    def get(self, url):
        self.calls.append(url)
        if url not in self.pages: raise CollectionError('http_404')
        return self.pages[url], {'final_url':url, 'fetched_at':NOW.isoformat(), 'sha256':'a'*64}


def recognition():
    return {'url':IMAGE,'final_url':IMAGE,'image_sha256':'b'*64,'checked_at':NOW.isoformat(),
        'engine':'test', 'lines':[{'text':text,'confidence':96} for text in (
            '古錐親子講古', '故事圖書館', '2026/10/04（日）', '活動時間10:30-12:00')]}


class FallbackTests(unittest.TestCase):
    def test_link_page_follows_next_layer_and_skips_ocr(self):
        client = Client()
        with patch('crawler.poster_ocr.read_poster', side_effect=AssertionError('OCR must be last')):
            result = supplement_activity(parsed(), client)
        self.assertEqual(client.calls,[LINK,FORM])
        self.assertEqual(result['sessions'][0]['end_time'],'2026-10-04T12:00:00+08:00')
        self.assertEqual(result['registration_url'],LINK)
        self.assertEqual(len(result['registration_evidence']['hops']),2)

    def test_start_only_announcement_can_fill_end_from_form(self):
        source = parsed();source['sessions']=[{'start_time':'2026-10-04T10:30:00+08:00','end_time':None}]
        self.assertEqual(supplement_activity(source, Client())['sessions'][0]['end_time'], '2026-10-04T12:00:00+08:00')
        with patch('crawler.poster_ocr.read_poster',side_effect=AssertionError('cannot override conflict')):
            with self.assertRaisesRegex(CollectionError, 'registration_session_conflict'):
                supplement_activity(source,Client({LINK:'<a href="'+FORM+'">報名</a>',FORM:PAGE.replace('10:30','09:30')}))

    def test_complete_announcement_does_not_fetch_or_ocr(self):
        source = parsed();source['sessions']=[{'start_time':'2026-10-04T10:30:00+08:00','end_time':'2026-10-04T12:00:00+08:00'}]
        client=Client()
        with patch('crawler.poster_ocr.read_poster',side_effect=AssertionError('not needed')):
            self.assertEqual(supplement_activity(source,client),source)
        self.assertEqual(client.calls,[])

    def test_beclass_scopes_description_and_excludes_other_forms(self):
        url='https://www.beclass.com/rid=abc123'
        page='<title>古錐親子講古</title><div class="BOXContent">地點：故事圖書館<br>活動日期：2026-10-04<br>活動時間：10:30-12:00</div><aside>其他活動2026/10/09 13:00-16:00</aside>'
        source=parsed();source.update(registration_url=url,content_links=[url])
        result=supplement_activity(source,Client({url:page}))
        self.assertEqual(len(result['sessions']),1)
        self.assertEqual(result['sessions'][0]['start_time'],'2026-10-04T10:30:00+08:00')

    def test_multi_date_choices_do_not_include_combined_booking_or_deadline(self):
        source=parsed();source['text']='地點：故事圖書館';source.update(registration_url=FORM,content_links=[FORM])
        page='<title>古錐親子講古</title><div>故事圖書館</div><div>報名截止：2026/10/01 12:00-13:00</div><div role="listitem"><div role="heading">參加場次</div>'
        for label in ('2026/10/04（日）10:30-12:00','2026/10/11（日）14:00-15:00','兩場都參加2026/10/04 10:30-15:00'):
            page+='<div role="radio" data-value="'+label+'">'+label+'</div>'
        result=supplement_activity(source,Client({FORM:page+'</div>'}))
        self.assertEqual([r['start_time'][:10] for r in result['sessions']],['2026-10-04','2026-10-11'])

    def test_conflicting_forms_cannot_be_selected_arbitrarily(self):
        second=FORM.replace('test','second')
        client=Client({LINK:'<a href="'+FORM+'">報名</a><a href="'+second+'">報名</a>',FORM:PAGE,second:PAGE.replace('10:30','11:00')})
        with self.assertRaisesRegex(CollectionError,'multiple_forms_conflict'):
            supplement_activity(parsed(),client)

    def test_wrong_date_or_weekday_never_uses_poster_to_override(self):
        for page in (PAGE.replace('2026/10/04','2026/10/05'), PAGE.replace('（日）','（六）')):
            with patch('crawler.poster_ocr.read_poster',side_effect=AssertionError('conflict')):
                with self.assertRaises(CollectionError):
                    supplement_activity(parsed(),Client({LINK:'<a href="'+FORM+'">報名</a>',FORM:page}))

    def test_ocr_last_resort_and_low_confidence_remains_pending(self):
        source=parsed();source.update(registration_url='',content_links=[])
        with patch('crawler.poster_ocr.read_poster',return_value=recognition()):
            result=supplement_activity(source,Client())
        self.assertEqual(result['sessions'][0]['start_time'],'2026-10-04T10:30:00+08:00')
        self.assertEqual(result['poster_ocr_evidence']['image_sha256'],'b'*64)
        for change in ('confidence','year','venue'):
            value=recognition()
            if change=='confidence':value['lines'][2]['confidence']=60
            elif change=='year':
                value['lines'][2]['text']='10月04日（日）'
                source['title']='古錐親子講古'
            else:value['lines'][1]['text']='其他地方'
            with self.subTest(change=change), self.assertRaises(CollectionError):poster_sessions(source,value)

    def test_review_and_build_recheck_image_and_times(self):
        source=parsed();source.update(registration_url='',content_links=[])
        detail=DETAIL.replace('https://linktr.ee/story','')
        client=Client({URL:detail})
        with patch('crawler.poster_ocr.read_poster',return_value=recognition()):
            resolved=supplement_activity(source,client)
            fields=dict(resolved,**resolved['sessions'][0]);fields.pop('sessions')
            candidate={'id':'ocr','source_url':URL,'title':source['title'],'kind':'session',
                       'trusted_language_source':True,'fields':fields}
            _, proof, row=verify_gameislearning(candidate,client,NOW)
            validate_auto_source(proof,None,detail,client=client)
            self.assertEqual(row['activity']['start_time'],'2026-10-04T10:30:00+08:00')
        changed=recognition();changed['image_sha256']='c'*64
        with patch('crawler.poster_ocr.read_poster',return_value=changed),self.assertRaisesRegex(Pending,'poster_ocr_source_changed'):
            validate_auto_source(proof,None,detail,client=client)
        forged=copy.deepcopy(candidate);forged['fields']['start_time']='2026-10-04T09:00:00+08:00'
        with patch('crawler.poster_ocr.read_poster',return_value=recognition()),self.assertRaises(Pending):
            verify_gameislearning(forged,client,NOW)

    def test_network_scope_rejects_redirect_before_request(self):
        for bad in ('http://docs.google.com/forms/d/test/viewform','https://docs.google.com.evil.test/forms/d/test/viewform',
                    'https://127.0.0.1/private','https://docs.google.com/forms/d/test/formResponse'):
            self.assertFalse(supported_url(bad))
        with self.assertRaises(CollectionError):
            SafeRedirect({'docs.google.com'}).redirect_request(Request(FORM),None,302,'',{},'https://127.0.0.1/private')
        with self.assertRaises(CollectionError):
            PosterRedirect().redirect_request(Request(IMAGE),None,302,'',{},'https://other.test/image.jpg')
        with self.assertRaises(CollectionError): HTTPClient(allowed_hosts={'docs.google.com'}).get('https://localhost/')

    def test_year_heading_and_start_only_are_explicit_not_crawl_year(self):
        source=parsed();source.update(registration_url=FORM,content_links=[FORM])
        page='<title>2026年古錐親子講古</title><p>故事圖書館</p><p>活動日期：10月04日（日）</p><p>活動時間：10:30</p>'
        result=resolve_registration(source,Client({FORM:page}))
        self.assertEqual(result['sessions'][0]['start_time'],'2026-10-04T10:30:00+08:00')
        self.assertIsNone(result['sessions'][0]['end_time'])

    def test_nested_link_limit_and_response_redirect_are_blocked(self):
        second='https://linktr.ee/second';third='https://linktr.ee/third'
        client=Client({LINK:'<a href="'+second+'">下一頁</a>',second:'<a href="'+third+'">下一頁</a>',third:'<a href="'+FORM+'">報名</a>'})
        with self.assertRaisesRegex(CollectionError,'depth_limit'):resolve_registration(parsed(),client)
        with self.assertRaisesRegex(CollectionError,'redirect_url_not_allowed'):
            SafeRedirect({'docs.google.com'},supported_url).redirect_request(Request(FORM),None,302,'',{},
                'https://docs.google.com/forms/d/test/formResponse')

    def test_link_anchor_in_announcement_is_kept(self):
        html=DETAIL.replace('https://linktr.ee/story','<a href="'+FORM+'">活動報名</a>')
        self.assertEqual(parse_detail(html,URL,{},now=NOW)['registration_url'],FORM)

    def test_poster_month_day_can_use_explicit_announcement_year(self):
        value=recognition();value['lines'][2]['text']='10月04日（日）'
        result=poster_sessions(parsed(),value)
        self.assertEqual(result['sessions'][0]['start_time'],'2026-10-04T10:30:00+08:00')
        self.assertEqual(result['poster_ocr_evidence']['year_evidence']['quote'],'2026年')

    def test_poster_does_not_choose_between_conflicting_end_times(self):
        value=recognition();value['lines'].append({'text':'活動時間10:30-11:30','confidence':99})
        with self.assertRaisesRegex(CollectionError,'poster_session_conflict'):poster_sessions(parsed(),value)

    @unittest.skipUnless(shutil.which('tesseract'), 'Tesseract integration runs on Linux CI')
    def test_real_tesseract_recognizes_chinese_date_and_time_fixture(self):
        from crawler.poster_ocr import recognize
        output = recognize((Path(__file__).parent/'fixtures/poster_ocr.png').read_bytes())
        text = ''.join(r['text'].replace(' ','') for r in output['lines'])
        self.assertIn('親子故事活動', text)
        self.assertIn('2026/10/04', text)
        self.assertRegex(text, r'10:30[-–—]12:00')

    def test_ocr_tsv_confidence_is_minimum_not_average(self):
        header='level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'
        rows=tsv_lines(header+'5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t95\t2026/10/04\n5\t1\t1\t1\t1\t2\t0\t0\t10\t10\t60\t10:30\n')
        self.assertEqual(rows[0]['confidence'],60)
        self.assertEqual(rows[0]['text'],'2026/10/04 10:30')


if __name__=='__main__': unittest.main()
