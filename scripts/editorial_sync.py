"""Download pending work / validate / return prose, for any local AI editor.

Git credentials stay in the user's existing Git configuration. Never print Git
stderr or remote URLs: some checkouts contain credentials in their remote URL.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from crawler.ai_editorial import EditorialError, fingerprint, save_json
from crawler.editorial_queue import (pending, result_name, validate_result,
                                    read, RESULTS, RECEIPTS)


def git(*args, cwd=None):
    cwd = cwd or ROOT
    result = subprocess.run(['git'] + list(args), cwd=str(cwd),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=dict(os.environ, GIT_TERMINAL_PROMPT='0'))
    if result.returncode:
        raise RuntimeError('Git operation failed: ' + args[0] + ' (credentials, network or concurrent update; no force push)')
    return result.stdout.decode('utf-8').strip()


def snapshot(destination):
    git('fetch', '--quiet', 'origin', 'main')
    revision = git('rev-parse', 'refs/remotes/origin/main')
    git('clone', '--quiet', '--shared', '--no-checkout', str(ROOT), str(destination))
    git('checkout', '--quiet', '--detach', revision, cwd=destination)
    return revision


def download(output, provider=None):
    output = Path(output)
    with tempfile.TemporaryDirectory(prefix='taigi-editorial-') as temp:
        repo = Path(temp) / 'repo'
        revision = snapshot(repo)
        policy = read(repo, 'data/editorial/config.json')
        if not policy['enabled'] or (provider and provider != policy['provider']):
            save_json(output / 'input.json', {'schema_version': 1, 'items': [], 'disabled': True})
            print('Editor disabled or assigned to another provider; no writing required')
            return 0
        guide = (repo / 'TAIGI_EDITORIAL.md').read_text(encoding='utf-8')
        tasks = []
        for item in pending(repo):
            name = result_name(item)
            # A returned file is waiting on publication, not on another rewrite.
            if (repo / RESULTS / name).exists():
                try:
                    validate_result(read(repo, RESULTS + '/' + name), item, guide)
                except (ValueError, EditorialError):
                    pass  # A changed guide or rejected result needs correction.
                else:
                    continue
            tasks.append({'activity_id': item['activity_id'], 'source_hash': item['source_hash'],
                          'activity': item['activity'], 'result_file': name})
        save_json(output / 'input.json', {'schema_version': 1, 'git_revision': revision,
                                         'provider': policy['provider'], 'guide_hash': fingerprint(guide),
                                         'items': tasks})
        (output / 'TAIGI_EDITORIAL.md').write_text(guide, encoding='utf-8')
        (output / 'EDITORIAL_HANDOFF.md').write_bytes((repo / 'EDITORIAL_HANDOFF.md').read_bytes())
        (output / 'results').mkdir(exist_ok=True)
        print('Pending activities:', len(tasks), '; handoff:', output / 'input.json')
        return len(tasks)


def checked_files(folder, repo):
    files = sorted(Path(folder).glob('*.json'))
    if len(files) > 500:
        raise ValueError('Too many returned files')
    requests = {result_name(item): item for item in pending(repo)}
    receipts = read(repo, RECEIPTS)['results']
    guide = (repo / 'TAIGI_EDITORIAL.md').read_text(encoding='utf-8')
    selected = []
    for path in files:
        if path.is_symlink() or path.stat().st_size > 150000:
            raise ValueError('Unsafe result file')
        result = json.loads(path.read_text(encoding='utf-8'))
        if path.name in receipts:
            if receipts[path.name]['result_hash'] != fingerprint(result):
                raise ValueError('Already published copy is immutable: ' + path.name)
            continue
        target = repo / RESULTS / path.name
        if path.name not in requests:
            # Old local results may outlive their activity; never publish them.
            print('Skipped expired, superseded or no-longer-pending result:', path.name)
            continue
        validate_result(result, requests[path.name], guide)
        if target.exists() and json.loads(target.read_text()) == result:
            continue
        selected.append((path.name, result))
    return selected


def submit(folder, push=False):
    # Re-snapshot after a competing commit, then validate against the new queue.
    # The user's checkout/index/branch and unrelated edits remain untouched.
    for attempt in range(3 if push else 1):
        with tempfile.TemporaryDirectory(prefix='taigi-editorial-return-') as temp:
            repo = Path(temp) / 'repo'
            snapshot(repo)
            selected = checked_files(folder, repo)
            print('Validated new results:', len(selected))
            if not selected or not push:
                return len(selected)
            paths = []
            for name, result in selected:
                relative = RESULTS + '/' + name
                save_json(repo / relative, result)
                paths.append(relative)
            git('add', '--', *paths, cwd=repo)
            git('-c', 'user.name=Taigi Editorial', '-c', 'user.email=editorial@users.noreply.github.com',
                'commit', '--quiet', '-m', 'Publish reviewed Taiwanese activity introductions', cwd=repo)
            # Read privately, never log URL/credential or include it in an error.
            remote = git('remote', 'get-url', 'origin')
            git('remote', 'set-url', 'origin', remote, cwd=repo)
            try:
                git('push', '--quiet', 'origin', 'HEAD:main', cwd=repo)
            except RuntimeError:
                if attempt == 2:
                    raise
                continue
            print('Returned to GitHub; publication triggered by push to main')
            return len(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    get = sub.add_parser('download')
    get.add_argument('--output', type=Path, default=ROOT / '.editorial-work')
    get.add_argument('--provider', help='Only run when selected in data/editorial/config.json')
    for name in ('validate', 'submit'):
        sub.add_parser(name).add_argument('--results', type=Path, default=ROOT / '.editorial-work/results')
    args = parser.parse_args()
    if args.command == 'download':
        download(args.output, args.provider)
    else:
        submit(args.results, push=args.command == 'submit')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, EditorialError, OSError, KeyError) as exc:
        print('Editorial handoff stopped:', str(exc), file=sys.stderr)
        sys.exit(1)
