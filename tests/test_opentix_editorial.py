import json
import unittest
from pathlib import Path
from crawler.editorial import opentix_editions, session_edition


class OpentixEditorialTests(unittest.TestCase):
    def test_editions_are_bound_to_reviewed_sessions_and_rechecked_content(self):
        catalog = json.loads((Path(__file__).resolve().parents[1] / 'data/verified_activities.json').read_text())
        rows = {r['activity']['id']: r for r in catalog['activities']}
        editions = opentix_editions()
        self.assertEqual(len(editions), 40)
        self.assertEqual(len({e['activity_id'] for e in editions}), 40)
        self.assertEqual(len({e['binding']['source_url'] for e in editions}), 16)
        for entry in editions:
            row = rows[entry['activity_id']]
            self.assertEqual(session_edition(row['activity'], editions), entry)
            self.assertTrue(entry['source_quotes'])
            required = catalog['sources'][row['verification']['source_id']]['required_text']
            self.assertTrue(all(q in required for q in entry['source_quotes']))
            self.assertGreater(len(entry['description_taigi']), len(entry['summary_taigi']))
            self.assertIn('\n\n', entry['description_taigi'])
            self.assertNotIn('這場有台語內容', entry['description_taigi'])
            for field in ('source_url', 'title', 'start_time', 'end_time', 'description'):
                changed = dict(row['activity'], **{field: 'changed'})
                self.assertIsNone(session_edition(changed, editions))
                with self.assertRaises(ValueError):
                    session_edition(changed, editions, strict=True)

    def test_program_roles_versions_and_session_extras_are_not_conflated(self):
        entries = {e['activity_id']: e for e in opentix_editions()}
        def body(sid): return entries['opentix_' + sid]['description_taigi']
        self.assertIn('翁郁琁', body('2085288863274115073'))
        self.assertIn('電影本身74分鐘', body('2085288863274115073'))
        self.assertIn('整體活動約120分鐘', body('2085288863274115073'))
        self.assertIn('陳芬蘭擔任幕後代唱', body('2085261583923527681'))
        self.assertIn('陳秋燕', body('2085262078443405313'))
        self.assertNotIn('座談', body('2085262078443405313'))
        self.assertIn('研究策展處同仁', body('2085270043361689600'))
        self.assertNotIn('李威儀', body('2085270043361689600'))
        self.assertNotIn('蘇致亨', body('2085270043361689600'))
        for sid in ('2062085945916366848', '2057009592664137729', '2062086080595501056'):
            self.assertIn('祖母版', body(sid))
            self.assertIn('劉靜琦', body(sid))
            self.assertNotIn('葉子彥', body(sid))
        self.assertIn('同步錄影', body('2062086080595501056'))
        self.assertNotIn('同步錄影', body('2062085945916366848'))
        self.assertIn('演前導聆', body('2075132078315433985'))
        self.assertIn('座談', body('2075152117302697985'))
        self.assertNotIn('座談', body('2075152279245320193'))
        self.assertNotIn('演前導聆', body('2075152279245320193'))
        self.assertIn('座談', body('2038903364299452417'))
        self.assertNotIn('座談', body('2038903989607149569'))
        self.assertIn('座談', body('2049747309313294337'))
        self.assertNotIn('座談', body('2049748445126623233'))
