import json
import unittest
from pathlib import Path
from unittest.mock import patch

from crawler.editorial import (directory_introduction, display_summary, editions,
                               official_introduction, text_hash)


class DirectoryEditorialTests(unittest.TestCase):
    def test_real_prose_survives_without_navigation_or_registration_advertising(self):
        body = ('地點：臺北市圖書館\n加入官方 LINE 好友並傳送貼圖\n'
                '老師以繪本介紹海洋生物，帶領孩子猜水果謎語。\n'
                'https://forms.gle/example')
        result = official_introduction(body)
        self.assertIn('海洋生物', result)
        self.assertIn('猜水果謎語', result)
        self.assertNotIn('LINE', result)
        self.assertNotIn('https://', result)
        self.assertNotIn('請看活動公告', result)

    def test_translation_is_bound_to_source_body_and_session(self):
        body = '第一場介紹海洋生物。第二場猜水果謎語。'
        entry = {'source_url':'https://example.test/event', 'body_sha256':text_hash(body),
                 'sessions':['2026-09-20T10:30:00+08:00'], 'description':'第一場海洋故事',
                 'description_taigi':'做伙來聽海洋的故事。', 'summary_taigi':'海洋故事'}
        parsed = {'source_url':entry['source_url'], 'title':'故事活動', 'text':body}
        with patch('crawler.editorial.editions', return_value=[entry]):
            result = directory_introduction(parsed, {'start_time':entry['sessions'][0]})
            self.assertEqual(result['description_taigi'],entry['description_taigi'])
            for other in [dict(parsed,text=body+'內容已更換。'),dict(parsed,source_url='https://other.test/event')]:
                self.assertNotIn('description_taigi',directory_introduction(other,{'start_time':entry['sessions'][0]}))
            self.assertNotIn('description_taigi',directory_introduction(parsed,{'start_time':'2026-09-20T11:30:00+08:00'}))

    def test_published_directory_sessions_have_specific_short_and_long_taiwanese_copy(self):
        data = Path(__file__).resolve().parents[1]/'data'
        catalog=json.loads((data/'verified_activities.json').read_text())
        translations=json.loads((data/'ui_taigi.json').read_text())
        current={(e['source_url'],start):e for e in editions() for start in e['sessions']}
        count=0
        for row in catalog['activities']:
            a=row['activity']
            key=(a['source_url'],a['start_time'])
            if key not in current: continue
            count+=1; entry=current[key]
            self.assertEqual(a['description'],entry['description'])
            translated=translations[a['description']]
            self.assertEqual(translated,entry['description_taigi'])
            self.assertNotIn('台語站收錄的台語活動',translated)
            self.assertGreater(len(translated),len(entry['summary_taigi']))
            self.assertIn('\n\n',translated)
            self.assertEqual(display_summary(a['description'],translated),entry['summary_taigi'])
            for quote in entry['source_quotes']:
                self.assertIn(quote,catalog['sources'][row['verification']['source_id']]['required_text'])
        self.assertEqual(count,28)

    def test_untranslated_or_changed_description_cannot_use_an_old_summary(self):
        entry=editions()[0]
        self.assertEqual(display_summary(entry['description'],''),'')
        self.assertEqual(display_summary(entry['description']+'更新','新譯文'),'新譯文')

