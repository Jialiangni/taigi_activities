import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import editorial_gate as gate
from scripts.install_editorial_gate import configuration, launch_agent
from crawler.ai_editorial import fingerprint, save_json
from crawler.editorial_queue import request_for, result_name


class EditorialGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.settings = {'state_dir': str(self.base), 'workers': {'codex': {'argv': ['/usr/bin/true']}}}
        self.guide = 'Fixture guide'
        activity = {'id': 'future', 'title': '台語故事', 'description': '王老師講故事，介紹故事裡的人物與生活。',
                    'start_time': '2099-01-01T10:00:00+08:00', 'end_time': '2099-01-01T11:00:00+08:00',
                    'source_url': 'https://example.org/event/future'}
        item = request_for({'activity': activity}, {})
        self.task = {k: item[k] for k in ('activity_id', 'source_hash', 'activity')}
        self.task['result_file'] = result_name(item)
        self.result = {'schema_version': 1, 'activity_id': 'future', 'source_hash': item['source_hash'],
            'guide_hash': fingerprint(self.guide), 'summary_taigi': '王老師講故事，介紹故事內底的人物佮生活。',
            'description_taigi': '王老師講故事，介紹故事內底的人物佮生活。',
            'uncertain_terms': [], 'dictionary_evidence': [],
            'editor': {'provider': 'codex', 'model': 'fixture'}, 'edited_at': '2026-09-20T08:00:00+08:00',
            'review': {'facts_match': True, 'natural_taiwanese': True, 'people_and_content_complete': True,
                       'issues': [], 'evidence': [{'claim': '王老師講故事', 'quote': '王老師講故事'}]}}

    def download(self, directory):
        save_json(directory / 'input.json', {'schema_version': 1, 'provider': 'codex',
                                             'guide_hash': fingerprint(self.guide), 'items': [self.task]})
        (directory / 'TAIGI_EDITORIAL.md').write_text(self.guide)
        (directory / 'EDITORIAL_HANDOFF.md').write_text('Fixture contract')
        return 1

    def edit(self, settings, provider, job, prompt):
        self.assertIn('不操作Git', prompt)
        save_json(job / 'results' / self.task['result_file'], self.result)

    def test_empty_queue_starts_no_process_and_needs_no_codex_installation(self):
        worker, submitter = Mock(), Mock()
        with patch('scripts.editorial_gate.subprocess.Popen') as process:
            report = gate.run({'state_dir': str(self.base)}, downloader=Mock(return_value=0),
                              submitter=submitter, invoke=worker)
        self.assertEqual(report['ai_starts'], 0)
        self.assertEqual(report['status'], 'empty')
        worker.assert_not_called()
        process.assert_not_called()
        submitter.assert_not_called()

    def test_only_pending_work_starts_ai_and_valid_copy_returns(self):
        worker = Mock(side_effect=self.edit)
        report = gate.run(self.settings, downloader=self.download, submitter=Mock(return_value=0), invoke=worker)
        worker.assert_called_once()
        self.assertEqual(report['ai_starts'], 1)
        self.assertTrue((self.base / 'results' / self.task['result_file']).exists())

    def test_valid_local_copy_retries_return_without_rewriting(self):
        save_json(self.base / 'results' / self.task['result_file'], self.result)
        worker, submitter = Mock(), Mock(return_value=1)
        report = gate.run(self.settings, downloader=self.download, submitter=submitter, invoke=worker)
        worker.assert_not_called()
        self.assertEqual(report['submitted'], 1)

    def test_ai_failure_is_bounded_and_complete_output_survives(self):
        def fail(*args):
            raise RuntimeError('test failure')
        for _ in range(2):
            with self.assertRaises(RuntimeError):
                gate.run(self.settings, downloader=self.download, submitter=Mock(return_value=0), invoke=fail)
        worker = Mock()
        report = gate.run(self.settings, downloader=self.download, submitter=Mock(return_value=0), invoke=worker)
        worker.assert_not_called()
        self.assertEqual(report['status'], 'needs_attention')

    def test_worker_failure_after_valid_file_does_not_force_ai_retry(self):
        def partial(*args):
            self.edit(*args)
            raise RuntimeError('failed after saving')
        with self.assertRaises(RuntimeError):
            gate.run(self.settings, downloader=self.download, submitter=Mock(return_value=0), invoke=partial)
        worker = Mock()
        gate.run(self.settings, downloader=self.download, submitter=Mock(return_value=1), invoke=worker)
        worker.assert_not_called()

    def test_unconfigured_provider_never_starts_worker_or_consumes_attempt(self):
        settings = dict(self.settings, workers={})
        worker = Mock()
        with self.assertRaises(ValueError):
            gate.run(settings, downloader=self.download, submitter=Mock(return_value=0), invoke=worker)
        worker.assert_not_called()
        self.assertFalse((self.base / 'attempts.json').exists())

    def test_overlapping_gate_is_locked_before_download(self):
        import fcntl
        with (self.base / 'gate.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            downloader = Mock()
            report = gate.run(self.settings, downloader=downloader)
            self.assertEqual(report['status'], 'locked')
            downloader.assert_not_called()

    def test_launchd_starts_python_and_only_tuesday_friday_at_eight(self):
        spec = launch_agent(self.base, self.base / 'runner.json')
        self.assertIn('editorial_gate.py', spec['ProgramArguments'][1])
        self.assertFalse(spec['RunAtLoad'])
        self.assertEqual(spec['StartCalendarInterval'], [
            {'Weekday': 2, 'Hour': 8, 'Minute': 0}, {'Weekday': 5, 'Hour': 8, 'Minute': 0}])
        cmd = configuration(self.base, '/path/to/codex')['workers']['codex']['argv']
        self.assertIn('forced_login_method="chatgpt"', cmd)
        self.assertNotIn('danger-full-access', cmd)

    def test_failed_download_never_starts_worker(self):
        worker = Mock()
        with self.assertRaises(RuntimeError):
            gate.run(self.settings, downloader=Mock(side_effect=RuntimeError('offline')),
                     submitter=Mock(), invoke=worker)
        worker.assert_not_called()
        self.assertEqual(json.loads((self.base / 'latest-run.json').read_text())['ai_starts'], 0)

    def test_stale_local_guide_copy_is_replaced_instead_of_blocking_submit(self):
        old = dict(self.result, guide_hash='outdated')
        save_json(self.base / 'results' / self.task['result_file'], old)
        submitter = Mock(return_value=1)
        report = gate.run(self.settings, downloader=self.download, submitter=submitter, invoke=self.edit)
        self.assertEqual(report['ai_starts'], 1)
        submitter.assert_called_once()

    def test_real_subprocess_adapter_gets_prompt_and_writes_valid_result_without_api_key(self):
        # Executes Python as a fixture worker, not a model. Tests the real process
        # boundary, cwd, stdin, environment and persisted output contract.
        script = self.base / 'fixture_worker.py'
        script.write_text('import os,sys,json\nfrom pathlib import Path\n'
            'assert "OPENAI_API_KEY" not in os.environ\n'
            'assert "CODEX_API_KEY" not in os.environ\n'
            'assert "不操作Git" in sys.stdin.read()\n'
            'task=json.loads(Path("input.json").read_text())["items"][0]\n'
            'Path("results",task["result_file"]).write_text(' + repr(json.dumps(self.result)) + ')\n')
        settings = dict(self.settings, workers={'codex': {'argv': [sys.executable, str(script)]}})
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'fixture', 'CODEX_API_KEY': 'fixture'}):
            report = gate.run(settings, downloader=self.download, submitter=Mock(return_value=1))
        self.assertEqual(report['ai_starts'], 1)
        self.assertEqual(report['submitted'], 1)


if __name__ == '__main__':
    unittest.main()
