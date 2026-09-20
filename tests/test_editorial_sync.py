"""Exercise real Git download/return in temporary local repositories."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from crawler.ai_editorial import fingerprint, save_json
from crawler.editorial_queue import request_for, result_name
from scripts import editorial_sync as sync


class EditorialSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'repo'
        self.remote = self.base / 'remote.git'
        self.output = self.base / 'work'
        self.repo.mkdir()
        self.git('init', '--bare', str(self.remote), cwd=self.base)
        self.git('init')
        self.git('checkout', '-b', 'main')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.org')
        self.git('remote', 'add', 'origin', str(self.remote))
        activity = {'id': 'future', 'title': '台語故事', 'description': '王老師講故事，介紹故事裡的人物與生活。',
                    'start_time': '2099-01-01T10:00:00+08:00', 'end_time': '2099-01-01T11:00:00+08:00',
                    'source_url': 'https://example.org/event/future'}
        row = {'activity': activity, 'verification': {}}
        self.item = request_for(row, {})
        self.guide = 'Fixture guide'
        (self.repo / 'TAIGI_EDITORIAL.md').write_text(self.guide)
        (self.repo / 'EDITORIAL_HANDOFF.md').write_text('Fixture contract')
        for name, value in {
            'config': {'enabled': True, 'provider': 'codex'},
            'queue': {'schema_version': 1, 'items': [self.item]},
            'receipts': {'schema_version': 1, 'results': {}}
        }.items():
            save_json(self.repo / ('data/editorial/' + name + '.json'), value)
        save_json(self.repo / 'data/verified_activities.json', {'activities': []})
        save_json(self.repo / 'data/ai_taigi.json', {'schema_version': 1, 'protected_activity_ids': [],
                                                  'editions': {}, 'attempts': {}, 'daily_usage': {}})
        self.git('add', '.')
        self.git('commit', '-m', 'Fixture')
        self.git('push', '-u', 'origin', 'main')
        self.result = {'schema_version': 1, 'activity_id': 'future', 'source_hash': self.item['source_hash'],
            'guide_hash': fingerprint(self.guide), 'summary_taigi': '王老師講故事，介紹故事內底的人物佮生活。',
            'description_taigi': '王老師講故事，介紹故事內底的人物佮生活。',
            'uncertain_terms': [], 'dictionary_evidence': [],
            'editor': {'provider': 'other-ai', 'model': 'fixture'}, 'edited_at': '2026-09-20T08:00:00+08:00',
            'review': {'facts_match': True, 'natural_taiwanese': True, 'people_and_content_complete': True,
                       'issues': [], 'evidence': [{'claim': '王老師講故事', 'quote': '王老師講故事'}]}}
        self.root_patch = patch.object(sync, 'ROOT', self.repo)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def git(self, *args, cwd=None):
        return subprocess.check_output(['git'] + list(args), cwd=str(cwd or self.repo),
                                       stderr=subprocess.DEVNULL).decode().strip()

    def test_download_submit_is_idempotent_and_preserves_dirty_checkout(self):
        (self.repo / 'TAIGI_EDITORIAL.md').write_text('Unsaved local edit')
        self.git('add', 'TAIGI_EDITORIAL.md')
        (self.repo / 'unrelated.txt').write_text('Do not touch')
        before = self.git('status', '--porcelain')
        self.assertEqual(sync.download(self.output, 'codex'), 1)
        self.assertEqual((self.output / 'TAIGI_EDITORIAL.md').read_text(), self.guide)
        save_json(self.output / 'results' / result_name(self.item), self.result)
        self.assertEqual(sync.submit(self.output / 'results', push=True), 1)
        self.assertEqual(self.git('status', '--porcelain'), before)
        changed = self.git('diff', '--name-only', 'HEAD', 'origin/main')
        # origin/main refresh happens on the next call, verifying persistence too.
        self.assertEqual(sync.submit(self.output / 'results', push=True), 0)
        changed = self.git('diff', '--name-only', 'HEAD', 'origin/main')
        self.assertEqual(changed, 'data/editorial/results/' + result_name(self.item))
        self.assertEqual(sync.download(self.output, 'codex'), 0)

    def test_provider_switch_clears_old_input_and_does_not_require_api(self):
        self.assertEqual(sync.download(self.output, 'codex'), 1)
        self.assertEqual(sync.download(self.output, 'other-ai'), 0)
        self.assertEqual(json.loads((self.output / 'input.json').read_text())['items'], [])

    def test_push_race_retries_latest_main_without_losing_other_change(self):
        sync.download(self.output, 'codex')
        save_json(self.output / 'results' / result_name(self.item), self.result)
        original = sync.git
        calls = []
        def racing_git(*args, **kwargs):
            if args[0] == 'push' and not calls:
                calls.append(True)
                (self.repo / 'concurrent.txt').write_text('Other writer')
                self.git('add', 'concurrent.txt')
                self.git('commit', '-m', 'Concurrent update')
                self.git('push', 'origin', 'main')
                raise RuntimeError('simulated non-fast-forward')
            return original(*args, **kwargs)
        with patch.object(sync, 'git', side_effect=racing_git):
            self.assertEqual(sync.submit(self.output / 'results', push=True), 1)
        self.git('fetch', 'origin', 'main')
        self.assertEqual(self.git('show', 'origin/main:concurrent.txt'), 'Other writer')
        self.assertIn('summary_taigi', self.git('show', 'origin/main:data/editorial/results/' + result_name(self.item)))


if __name__ == '__main__':
    unittest.main()
