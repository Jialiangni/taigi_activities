import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from crawler import editorial_queue as q
from crawler.ai_editorial import fingerprint, save_json
from crawler.tw_hokkien import MODEL, PROVIDER, FIELDS, text_hash, terminology_edits, apply_edits
from scripts.tw_hokkien_result import package
from scripts.editorial_gate import valid_saved


class TranslationFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.activity = {'id': 'trial', 'title': '免費故事', 'description': '王老師講故事。活動免費。',
                         'source_url': 'https://example.org/trial', 'start_time': '2099-01-01T10:00:00+08:00'}
        self.item = q.request_for({'activity': self.activity}, {})
        self.guide = 'Fixture guide'
        self.task = {k: self.item[k] for k in ('activity_id', 'source_hash', 'activity')}
        self.task['result_file'] = q.result_name(self.item)
        self.prose = '王老師講故事，介紹故事內底的人物佮生活。活動免費。'
        self.review = {'facts_match': True, 'natural_taiwanese': False,
                       'people_and_content_complete': True, 'issues': [],
                       'evidence': [{'claim': '活動免費', 'quote': '活動免費'}]}
        self.bundle = {'provider': PROVIDER, 'items': [self.task], 'guide_hash': fingerprint(self.guide)}
        save_json(self.root / 'input.json', self.bundle)
        (self.root / 'TAIGI_EDITORIAL.md').write_text(self.guide)
        save_json(self.root / 'translation_terminology.json', {'preferences': [{
            'id': 'free-admission-mian-tsinn', 'source_term': '免費', 'preferred_taigi': '免錢'}]})
        save_json(self.root / 'review.json', self.review)
        self.plan = {'activity_id': 'trial', 'fields': {}, 'review_file': 'review.json'}
        for field in FIELDS:
            name = field + '.txt'
            self.plan['fields'][field] = name
            (self.root / name).write_text(self.prose)
            save_json(self.root / (name + '.translation.json'), {
                'status': 'ready', 'model': {'name': MODEL, 'digest': 'a' * 64},
                'source': '活動免費', 'source_sha256': text_hash('活動免費'),
                'translation': self.prose, 'translation_sha256': text_hash(self.prose),
                'language_rewritten_by_codex': False, 'protected_literals': ['王老師']})
        save_json(self.root / 'plan.json', self.plan)

    def pack(self, ok=True):
        proc = subprocess.CompletedProcess([], 0 if ok else 2,
            json.dumps({'ok': ok, 'language_rewritten_by_codex': False}))
        with patch('scripts.tw_hokkien_result.subprocess.run', return_value=proc) as verify:
            path = package(self.root, 'plan.json', '/fixture/translator')
            self.assertEqual(verify.call_count, 2)
        return json.loads(path.read_text())

    def test_v2_without_naturalness_review_preserves_model_and_quotes(self):
        result = self.pack()
        q.validate_result(result, self.item, self.guide)
        self.assertFalse(result['review']['natural_taiwanese'])
        self.assertEqual(result['summary_taigi'], self.prose.replace('免費', '免錢'))
        self.assertEqual((self.root / 'summary_taigi.txt').read_text(), self.prose)
        self.assertEqual(result['review']['evidence'][0], {'claim': '活動免錢', 'quote': '活動免費'})
        self.assertEqual(result['translation']['fields']['summary_taigi']['verified_translation'], self.prose)

    def test_model_provenance_facts_and_unauthorized_rewrites_rejected(self):
        original = self.pack()
        mutations = [lambda r: r['review'].update(facts_match=False),
                     lambda r: r['review'].update(people_and_content_complete=False),
                     lambda r: r['review'].update(natural_taiwanese=True),
                     lambda r: r['review']['issues'].append('added recording claim'),
                     lambda r: r['editor'].update(model='other-model'),
                     lambda r: r['translation'].update(model_digest='missing'),
                     lambda r: r['translation']['fields']['summary_taigi'].update(cli_verified=False),
                     lambda r: r.update(summary_taigi=r['summary_taigi'] + '任意改寫'),
                     lambda r: r['translation']['fields']['summary_taigi']['user_overrides'][0].update(replacement='other'),
                     lambda r: r.update(source_hash='b' * 64)]
        for mutate in mutations:
            bad = copy.deepcopy(original)
            mutate(bad)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                q.validate_result(bad, self.item, self.guide)

    def test_failed_cli_verify_never_writes_result(self):
        with self.assertRaises(ValueError):
            self.pack(ok=False)
        self.assertFalse((self.root / 'results' / self.task['result_file']).exists())

    def test_wrong_local_model_stops_packaging(self):
        path = self.root / 'summary_taigi.txt.translation.json'
        report = json.loads(path.read_text()); report['model']['name'] = 'SARC'
        save_json(path, report)
        with self.assertRaises(ValueError):
            self.pack()

    def test_protected_official_name_and_overlap_are_not_rewritten(self):
        text = '免費故事：活動免費。'
        edits = terminology_edits(text, self.item['activity'])
        self.assertEqual(apply_edits(text, edits, self.item['activity']), '免費故事：活動免錢。')
        bad = dict(edits[0], start=0, end=2)
        with self.assertRaises(ValueError):
            apply_edits(text, [bad], self.item['activity'])
        with self.assertRaises(ValueError):
            apply_edits(text, edits * 2, self.item['activity'])

    def test_switch_does_not_reuse_legacy_worker_result(self):
        result = self.pack()
        legacy = {k: v for k, v in result.items() if k != 'translation'}
        legacy.update(schema_version=1, editor={'provider': 'codex', 'model': 'fixture'})
        legacy['review']['natural_taiwanese'] = True
        path = self.root / 'legacy.json'; save_json(path, legacy)
        self.assertTrue(valid_saved(path, self.task, self.guide, 'codex'))
        self.assertFalse(valid_saved(path, self.task, self.guide, PROVIDER))
        save_json(self.root / 'data/editorial/config.json', {'provider': PROVIDER})
        with self.assertRaises(ValueError):
            q.check_provider(self.root, legacy)

    def test_unresolved_semantics_keeps_audit_but_cannot_publish(self):
        self.review['facts_match'] = False
        self.review['issues'] = ['Model added recording not in source']
        save_json(self.root / 'review.json', self.review)
        with self.assertRaises(ValueError):
            self.pack()
        self.assertTrue((self.root / 'audit/trial.packaged.json').exists())
        self.assertFalse((self.root / 'results' / self.task['result_file']).exists())


if __name__ == '__main__':
    unittest.main()
