import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from crawler import editorial_queue as q
from crawler.ai_editorial import fingerprint, save_json
from crawler.meta_translation import MODEL, PROVIDER
from crawler.tw_hokkien import FIELDS, text_hash
from scripts.meta_result import package
from scripts.muse_translate import extract_events, make_prompt, verify
from scripts import editorial_gate as gate

RUN = '00000000-0000-4000-8000-000000000001'


def events(prompt, text):
    return '\n'.join(json.dumps({'payload_type': kind, 'payload': dict(data, command_id=RUN)})
                     for kind, data in [
        ('run.model.configured', {'model_id': MODEL, 'provider_id': 'meta'}),
        ('turn.input.user', {'prompt': prompt}),
        ('run.terminal.completed', {'terminal': 'completed', 'text': text})])


class MetaFlowTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.activity = {'id': 'trial', 'title': 'Example event', 'description': 'Example activity costs 200.',
                         'source_url': 'https://example.org/trial', 'start_time': '2099-01-01T10:00:00+08:00'}
        self.item = q.request_for({'activity': self.activity}, {})
        self.task = {k: self.item[k] for k in ('activity_id', 'source_hash', 'activity')}
        self.task['result_file'] = q.result_name(self.item)
        self.guide = 'Test guide'
        self.prose = self.activity['description']
        self.review = {'facts_match': True, 'natural_taiwanese': False, 'people_and_content_complete': True,
                       'issues': [], 'evidence': [{'claim': 'costs 200', 'quote': 'costs 200'}]}
        self.bundle = {'provider': PROVIDER, 'items': [self.task], 'guide_hash': fingerprint(self.guide)}
        save_json(self.root / 'input.json', self.bundle)
        (self.root / 'TAIGI_EDITORIAL.md').write_text(self.guide)
        (self.root / 'EDITORIAL_HANDOFF.md').write_text('Test contract')
        save_json(self.root / 'translation_terminology.json', {'preferences': [{
            'id': 'free-admission-mian-tsinn', 'source_term': '免費', 'preferred_taigi': '免錢'}]})
        save_json(self.root / 'review.json', self.review)
        plan = {'activity_id': 'trial', 'fields': {}, 'review_file': 'review.json'}
        for field in FIELDS:
            path = self.root / (field + '.txt')
            plan['fields'][field] = path.name
            path.write_text(self.prose)
            folder = Path(str(path) + '.audit'); folder.mkdir()
            prompt = make_prompt(self.prose, ['200'])
            raw = events(prompt, self.prose)
            (folder / 'events.jsonl').write_text(raw)
            (folder / 'prompt.txt').write_text(prompt)
            save_json(Path(str(path) + '.translation.json'), {
                'status': 'ready', 'model': MODEL, 'transport': 'muse-code', 'run_id': RUN,
                'source': self.prose, 'source_sha256': text_hash(self.prose), 'protected_literals': ['200'],
                'translation': self.prose, 'translation_sha256': text_hash(self.prose),
                'events_sha256': text_hash(raw), 'language_rewritten_by_codex': False})
        save_json(self.root / 'plan.json', plan)

    def test_package_actual_events_and_reject_factual_or_lineage_errors(self):
        path = package(self.root, 'plan.json')
        result = json.loads(path.read_text())
        q.validate_result(result, self.item, self.guide)
        self.assertEqual(result['schema_version'], 3)
        self.assertFalse(result['review']['natural_taiwanese'])
        mutations = [lambda r: r.update(summary_taigi=r['summary_taigi'] + 'Extra'),
                     lambda r: r['review'].update(facts_match=False),
                     lambda r: r['review'].update(natural_taiwanese=True),
                     lambda r: r['editor'].update(model='other'),
                     lambda r: r['translation']['fields']['summary_taigi'].update(run_id='fake'),
                     lambda r: r['translation']['fields']['summary_taigi'].update(artifact_verified=False)]
        for change in mutations:
            bad = copy.deepcopy(result); change(bad)
            with self.assertRaises(ValueError):
                q.validate_result(bad, self.item, self.guide)

    def test_prompt_and_output_tampering_prevent_packaging(self):
        p = self.root / 'summary_taigi.txt'
        self.assertTrue(verify(p)['ok'])
        p.write_text('Changed model output')
        with self.assertRaises(ValueError):
            package(self.root, 'plan.json')
        self.assertFalse((self.root / 'results').exists())

    def test_incomplete_mixed_runs_and_tools_rejected(self):
        raw = events('prompt', 'output')
        variants = [raw.replace('muse-spark-1.3', 'other'),
                    '\n'.join(raw.splitlines()[:-1]),
                    raw + '\n' + raw.splitlines()[-1],
                    raw + '\n' + json.dumps({'payload_type': 'tool.call.started', 'payload': {}})]
        for variant in variants:
            with self.assertRaises(ValueError):
                extract_events(variant, 'prompt')

    def test_gate_routes_meta_and_preserves_old_history(self):
        packaged = json.loads(package(self.root, 'plan.json').read_text())
        def download(folder):
            folder.mkdir(parents=True)
            for name in ('input.json', 'TAIGI_EDITORIAL.md', 'EDITORIAL_HANDOFF.md', 'translation_terminology.json'):
                (folder / name).write_bytes((self.root / name).read_bytes())
            return 1
        def invoke(settings, provider, folder, prompt):
            self.assertEqual(provider, PROVIDER)
            self.assertIn('muse_translate.py', prompt)
            self.assertIn('meta_result.py', prompt)
            self.assertNotIn('{meta_', prompt)
            self.assertTrue((folder / 'translation_terminology.json').exists())
            save_json(folder / 'results' / self.task['result_file'], packaged)
        settings = {'state_dir': str(self.root / 'gate'), 'workers': {PROVIDER: {'argv': ['/usr/bin/true']}}}
        submit = Mock(return_value=1)
        report = gate.run(settings, downloader=download, submitter=submit, invoke=invoke)
        self.assertEqual(report['submitted'], 1)
        self.assertFalse(gate.valid_saved(self.root / 'results' / self.task['result_file'], self.task, self.guide, 'tw-hokkien'))
        save_json(self.root / 'data/editorial/config.json', {'provider': PROVIDER})
        legacy = dict(packaged, schema_version=2, editor={'provider': 'tw-hokkien', 'model': 'legacy'})
        with self.assertRaises(ValueError):
            q.check_provider(self.root, legacy)


if __name__ == '__main__':
    unittest.main()
