"""Export official evidence for AI review; validate and persist reviewed closures.

No model/API calls, no prose generation, no direct publication.
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crawler.collection import Client, TAIPEI
from crawler.candidate_triage import PATH, document, digest, evidence_url, load, matches, validate
from crawler.ai_editorial import save_json

ROOT = Path(__file__).resolve().parents[1]


def export(root, output, limit=25, client=None):
    client = client or Client()
    backlog = json.loads((root / 'data/review_backlog.json').read_text())['candidates']
    cases_path = root / 'data/review_followups.json'
    cases = json.loads(cases_path.read_text()).get('cases', {}) if cases_path.exists() else {}
    now = datetime.now(TAIPEI)
    selected, urls = [], set()
    for c in backlog:
        followup = cases.get(c['id'], {})
        if followup.get('next_review_at') and datetime.fromisoformat(followup['next_review_at']) > now:
            continue
        url = evidence_url(c)
        if url not in urls and len(urls) >= limit:
            continue
        urls.add(url)
        row = {'candidate': c, 'evidence_url': url}
        try:
            body, ev = client.get(url)
            if ev['final_url'] != url:
                raise ValueError('Official page redirected; inspect destination before deciding')
            content = document(body, url, version=2)
            if not content:
                raise ValueError('Empty official evidence')
            row.update(content=content, content_sha256=digest(content), document_version=2, evidence=ev)
        except Exception as e:
            row['fetch_error'] = str(e)
        selected.append(row)
    save_json(output, {'schema_version': 1, 'exported_at': now.isoformat(), 'items': selected})
    print('Review candidates:', len(selected), 'Official sources:', len(urls))
    return selected


def apply(root, result, client=None):
    client = client or Client()
    backlog_path = root / 'data/review_backlog.json'
    backlog = json.loads(backlog_path.read_text())
    candidates = {(c['source_id'], c['id']): c for c in backlog['candidates']}
    existing = load(root)
    rows = result['decisions']
    closed = set()
    # Validate the whole batch before touching durable state.
    for row in rows:
        validate(row)
        key = (row['source_id'], row['candidate_id'])
        if key in closed or key not in candidates:
            raise ValueError('Duplicate or stale review result')
        if not matches(row, candidates[key], client):
            raise ValueError('Official evidence changed: ' + row['candidate_id'])
        closed.add(key)
    for row in rows:
        existing[(row['source_id'], row['candidate_id'])] = row
    # Save decisions first: an interrupted write can safely be rerun by normal review.
    save_json(root / PATH, {'schema_version': 1, 'decisions': list(existing.values())})
    backlog['candidates'] = [c for c in backlog['candidates'] if (c['source_id'], c['id']) not in closed]
    backlog['updated_at'] = datetime.now(TAIPEI).isoformat(timespec='seconds')
    save_json(backlog_path, backlog)
    print('Closed:', len(closed), 'Remaining:', len(backlog['candidates']))


def followup(root, result):
    """Persist an owned, dated next action; never label uncertainty an exclusion."""
    backlog = json.loads((root / 'data/review_backlog.json').read_text())['candidates']
    candidates = {c['id']: c for c in backlog}
    path = root / 'data/review_followups.json'
    data = json.loads(path.read_text()) if path.exists() else {'schema_version': 1, 'cases': {}}
    now = datetime.now(TAIPEI)
    for case in result['cases']:
        c = candidates.get(case.get('candidate_id'))
        if not c or case.get('source_url') != c['source_url']:
            raise ValueError('Stale follow-up identity')
        if case.get('owner') != 'Codex' or not all(case.get(k) for k in
                ('finding', 'missing_fields', 'next_action', 'reviewed_at', 'next_review_at')):
            raise ValueError('Follow-up must name findings, missing facts and next action')
        due = datetime.fromisoformat(case['next_review_at'])
        if due.tzinfo is None or not now < due <= now + timedelta(days=7):
            raise ValueError('Next review must be within seven days')
    for case in result['cases']:
        data['cases'][case['candidate_id']] = case
    data['updated_at'] = now.isoformat(timespec='seconds')
    save_json(path, data)
    print('Owned follow-ups:', len(result['cases']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    out = sub.add_parser('export')
    out.add_argument('--output', type=Path, required=True)
    out.add_argument('--limit', type=int, default=25)
    incoming = sub.add_parser('apply')
    incoming.add_argument('--results', type=Path, required=True)
    sub.add_parser('followup').add_argument('--results', type=Path, required=True)
    sub.add_parser('queue', help='Recheck persisted candidates using live official evidence, without a new collection')
    args = parser.parse_args()
    if args.command == 'export':
        if not 1 <= args.limit <= 100:
            parser.error('limit must be 1..100')
        export(ROOT, args.output, args.limit)
    elif args.command == 'apply':
        apply(ROOT, json.loads(args.results.read_text()))
    elif args.command == 'followup':
        followup(ROOT, json.loads(args.results.read_text()))
    else:
        from crawler.editorial_queue import prepare
        prepare(None, root=ROOT, backlog_only=True)


if __name__ == '__main__':
    main()
