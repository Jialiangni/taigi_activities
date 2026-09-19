import json
import unittest
from pathlib import Path
from crawler.collection import Document
from crawler.editorial import accupass_editions, accupass_edition
from crawler.sources.accupass import activity_intro


class AccupassEditorialTests(unittest.TestCase):
    def test_detail_article_keeps_late_cast_and_excludes_other_content(self):
        body = '活動重點。' * 60 + '演出人員：甲、乙。9/20由丙接替乙。'
        html = ('<nav>熱門推薦</nav><article>另一場的講者丁</article>'
                '<article class="EventContent_event-content__abc">' + body +
                '</article><footer>售票平台導覽</footer>')
        self.assertEqual(activity_intro({'description':'極短的SEO摘要'}, Document(html)), body)

    def test_unknown_or_ambiguous_template_uses_complete_schema_copy(self):
        intro = '詳細的活動說明。' * 40 + '主講人：王老師。'
        for html in ['<main>推薦活動講者</main>', '<article>不確定的正文</article>',
                     '<article class="EventContent_event-content__a">甲</article>'
                     '<article class="EventContent_event-content__b">乙</article>']:
            self.assertEqual(activity_intro({'description':intro}, Document(html)),intro)

    def test_current_editions_bind_sessions_and_source_evidence(self):
        root=Path(__file__).resolve().parents[1]
        catalog=json.loads((root/'data/verified_activities.json').read_text())
        entries=accupass_editions()
        self.assertEqual(len(entries),44)
        self.assertEqual(len({e['activity_id'] for e in entries}),44)
        covered=0
        for row in catalog['activities']:
            a=row['activity']; e=accupass_edition(a,entries)
            if not e: continue
            covered+=1
            self.assertTrue(e['source_quotes'])
            required=catalog['sources'][row['verification']['source_id']]['required_text']
            self.assertTrue(all(q in required for q in e['source_quotes']))
            self.assertLess(len(e['summary_taigi']),len(e['description_taigi']))
            self.assertIn('\n\n',e['description_taigi'])
            for field in ['title','start_time','description','source_url']:
                changed=dict(a,**{field:a[field]+' changed'})
                self.assertIsNone(accupass_edition(changed,entries))
                with self.assertRaises(ValueError):
                    accupass_edition(changed,entries,strict=True)
        self.assertEqual(covered,44)

    def test_session_copy_keeps_speakers_books_and_cast_correction(self):
        editions={e['activity_id']:e for e in accupass_editions()}
        event=editions['acc_2606300741301758195196_20260920_1500']
        self.assertIn('黃郁盛、李佳勳佮嚴梓碩',event['summary_taigi'])
        self.assertIn('沈宥齊',event['description_taigi'])
        a=editions['acc_2607280236031295663510_20260920_1030']
        b=editions['acc_2607280236031295663510_20260920_1330']
        self.assertIn('李苑芳',a['summary_taigi'])
        self.assertIn('棕色的熊',a['description_taigi'])
        self.assertNotIn('黑象與白象',a['description_taigi'])
        self.assertIn('黑象與白象',b['description_taigi'])
        self.assertNotIn('棕色的熊',b['description_taigi'])
