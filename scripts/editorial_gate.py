"""Plain-Python scheduled gate. Never starts an AI process for an empty queue."""
import argparse
import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import editorial_sync as sync
from crawler.ai_editorial import fingerprint, save_json
from crawler.editorial_queue import validate_result


def task_request(task):
    return dict(task, row={'activity': task['activity']})


def valid_saved(path, task, guide):
    if not path.exists():
        return False
    if path.is_symlink() or path.stat().st_size > 150000:
        raise ValueError('Unsafe local result')
    try:
        validate_result(json.loads(path.read_text()), task_request(task), guide)
        return True
    except (ValueError, sync.EditorialError, KeyError):
        return False


def submit_saved(pool, tasks, guide, submitter):
    # Only current validated copies enter submission. A stale local draft must
    # not prevent its replacement or block other newly completed activities.
    with tempfile.TemporaryDirectory(prefix='taigi-ready-') as temp:
        selected = Path(temp)
        count = 0
        for task in tasks:
            source = pool / task['result_file']
            if valid_saved(source, task, guide):
                shutil.copyfile(str(source), str(selected / task['result_file']))
                count += 1
        return submitter(selected, push=True) if count else 0


def worker_command(settings, provider, job):
    # Executable allowlist is LOCAL configuration, never downloaded from GitHub.
    entry = settings['workers'].get(provider)
    if not entry or not isinstance(entry.get('argv'), list) or not entry['argv']:
        raise ValueError('No local worker configured for provider: ' + provider)
    args = [part.replace('{workspace}', str(job)) for part in entry['argv']]
    if not all(isinstance(a, str) and a for a in args) or not Path(args[0]).is_file():
        raise ValueError('Worker executable is unavailable')
    return args


def run_worker(settings, provider, job, prompt):
    args = worker_command(settings, provider, job)
    env = dict(os.environ)
    # Codex uses the existing ChatGPT login; no fallback to billable API auth.
    if provider == 'codex':
        for key in ('OPENAI_API_KEY', 'CODEX_API_KEY', 'OPENAI_BASE_URL'):
            env.pop(key, None)
    with (job / 'worker.jsonl').open('w') as out, (job / 'worker.stderr').open('w') as err:
        process = subprocess.Popen(args, cwd=str(job), stdin=subprocess.PIPE,
                                   stdout=out, stderr=err, env=env, start_new_session=True)
        try:
            process.communicate(prompt.encode('utf-8'), timeout=settings.get('timeout_seconds', 1800))
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise RuntimeError('AI worker timed out; retained local files, no automatic restart')
        if process.returncode:
            raise RuntimeError('AI worker failed; see private local worker log')


def run(settings, downloader=sync.download, submitter=sync.submit, invoke=run_worker):
    base = Path(settings['state_dir']).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    os.chmod(str(base), 0o700)
    with (base / 'gate.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Another editorial gate is already running; no AI started')
            return {'status': 'locked', 'ai_starts': 0}
        report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'ai_starts': 0,
                  'pending': 0, 'submitted': 0}
        try:
            # Network/Git/JSON work only. No AI executable, login, SDK or model.
            bundle_dir = base / 'download'
            count = downloader(bundle_dir)
            report['pending'] = count
            if not count:
                report['status'] = 'empty'
                return report
            bundle = json.loads((bundle_dir / 'input.json').read_text())
            guide = (bundle_dir / 'TAIGI_EDITORIAL.md').read_text()
            provider = bundle['provider']
            state_path = base / 'attempts.json'
            attempts = json.loads(state_path.read_text()) if state_path.exists() else {}
            pool = base / 'results'
            pool.mkdir(exist_ok=True)
            eligible, blocked = [], []
            for task in bundle['items']:
                if valid_saved(pool / task['result_file'], task, guide):
                    continue  # Retry network publication without paying for rewriting.
                key = task['source_hash'] + ':' + bundle['guide_hash']
                if attempts.get(key, 0) >= settings.get('max_attempts', 2):
                    blocked.append(task['activity_id'])
                else:
                    eligible.append(task)
            report['submitted'] += submit_saved(pool, bundle['items'], guide, submitter)
            size = settings.get('batch_size', 5)
            if not isinstance(size, int) or not 1 <= size <= 20:
                raise ValueError('Invalid local batch size')
            for offset in range(0, len(eligible), size):
                batch = eligible[offset:offset + size]
                stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
                job = base / 'jobs' / stamp
                job.mkdir(parents=True)
                (job / 'results').mkdir()
                save_json(job / 'input.json', dict(bundle, items=batch))
                for name in ('TAIGI_EDITORIAL.md', 'EDITORIAL_HANDOFF.md'):
                    shutil.copyfile(str(bundle_dir / name), str(job / name))
                prompt = (ROOT / 'scripts/editorial_worker_prompt.txt').read_text().replace(
                    '{dictionary_script}', str(ROOT / 'scripts/lookup_taiwanese.py')).replace(
                    '{python}', sys.executable)
                # Confirm configured executable before consuming an attempt.
                worker_command(settings, provider, job)
                for task in batch:
                    key = task['source_hash'] + ':' + bundle['guide_hash']
                    attempts[key] = attempts.get(key, 0) + 1
                save_json(state_path, attempts)
                report['ai_starts'] += 1
                save_json(base / 'latest-run.json', dict(report, status='editing'))
                try:
                    invoke(settings, provider, job, prompt)
                finally:
                    # Retain completed files even if the worker later times out.
                    for task in batch:
                        source = job / 'results' / task['result_file']
                        if valid_saved(source, task, guide):
                            shutil.copyfile(str(source), str(pool / task['result_file']))
                # A successful process exit does not mean it produced valid copy.
                for task in batch:
                    if not valid_saved(pool / task['result_file'], task, guide):
                        raise ValueError('AI did not produce validated copy: ' + task['activity_id'])
                report['submitted'] += submit_saved(pool, batch, guide, submitter)
            report['needs_attention'] = blocked
            report['status'] = 'needs_attention' if blocked else 'submitted'
            return report
        except Exception as exc:
            report['status'] = 'failed'
            report['error_type'] = type(exc).__name__
            raise
        finally:
            save_json(base / 'latest-run.json', report)
            print(json.dumps(report, ensure_ascii=False))


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--settings', type=Path, required=True)
    args = parser.parse_args()
    settings = json.loads(args.settings.read_text())
    run(settings)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # No raw provider/Git diagnostics in shared launchd output.
        print('Editorial gate stopped: ' + type(exc).__name__, file=sys.stderr)
        sys.exit(1)
