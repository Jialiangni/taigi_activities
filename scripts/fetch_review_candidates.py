"""Download only data from a recent, trusted main-branch collection run."""
import argparse
import io
import json
import os
import re
import ssl
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != 'https':
            raise ValueError('Insecure artifact redirect')
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new and urlsplit(req.full_url).hostname != urlsplit(newurl).hostname:
            new.remove_header('Authorization')
        return new


def trusted_run(run, repository, now):
    created = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
    return (run['head_repository']['full_name'] == repository and run['head_branch'] == 'main'
            and run['path'] == '.github/workflows/collect.yml'
            and run['event'] in ('schedule', 'workflow_dispatch') and run['status'] == 'completed'
            and run['conclusion'] in ('success', 'failure')
            and timedelta(0) <= now-created <= timedelta(hours=36))


def extract(raw, output):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if len(entries) > 1000 or sum(i.file_size for i in entries) > 100_000_000:
            raise ValueError('Artifact exceeds review limits')
        names = set()
        for entry in entries:
            name = entry.filename
            if not re.fullmatch(r'[a-z0-9_]+\.json', name) or name in names:
                raise ValueError('Unexpected artifact filename')
            names.add(name)
            if entry.file_size > 20_000_000 or name in ('facebook.json', 'instagram.json', 'threads.json'):
                raise ValueError('Disallowed artifact entry')
        if 'report.json' not in names:
            raise ValueError('Collection report missing')
        output.mkdir(parents=True, exist_ok=True)
        if any(output.iterdir()):
            raise ValueError('Candidate destination must be empty')
        for entry in entries:
            raw_json = archive.read(entry)
            json.loads(raw_json)  # Treat the entire archive as data, never execute it.
            (output / entry.filename).write_bytes(raw_json)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', default=os.environ.get('COLLECTION_RUN_ID', ''))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repository = os.environ['GITHUB_REPOSITORY']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid repository')
    token = os.environ['GITHUB_TOKEN']
    context = ssl.create_default_context()
    if Path('/etc/ssl/cert.pem').exists():
        context.load_verify_locations('/etc/ssl/cert.pem')
    opener = build_opener(HTTPSHandler(context=context), SafeRedirect())
    base = 'https://api.github.com/repos/' + repository + '/actions/'
    def read(path):
        req = Request(base + path, headers={'Authorization': 'Bearer ' + token,
                      'User-Agent': 'TaigiActivities-review', 'Accept': 'application/vnd.github+json'})
        with opener.open(req, timeout=45) as response:
            raw = response.read(30_000_001)
        if len(raw) > 30_000_000:
            raise ValueError('Artifact response too large')
        return raw
    def api(path):
        return json.loads(read(path))
    now = datetime.now(timezone.utc)
    if args.run_id:
        if not args.run_id.isdigit():
            raise ValueError('Invalid run ID')
        run = api('runs/' + args.run_id)
    else:
        runs = api('workflows/collect.yml/runs?branch=main&per_page=30')['workflow_runs']
        run = next((r for r in runs if trusted_run(r, repository, now)), None)
    if not run or not trusted_run(run, repository, now):
        raise ValueError('No fresh trusted collection run; publication stopped')
    artifacts = api('runs/' + str(run['id']) + '/artifacts')['artifacts']
    artifact = next((a for a in artifacts if a['name'] == 'event-review-candidates' and not a['expired']), None)
    if not artifact:
        raise ValueError('Collection artifact missing; publication stopped')
    extract(read('artifacts/' + str(artifact['id']) + '/zip'), args.output)
    (args.output / '_collection_run.json').write_text(json.dumps({
        'id': run['id'], 'head_sha': run['head_sha'], 'conclusion': run['conclusion'],
        'url': run['html_url'], 'artifact_id': artifact['id']}, indent=2) + '\n')
    print('Review input: run', run['id'], 'collection conclusion:', run['conclusion'])


if __name__ == '__main__':
    main()
