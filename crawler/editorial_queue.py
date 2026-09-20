"""Provider-neutral handoff: verified candidates -> reviewed copy -> publication.

No model calls. Queue records are evidence, returned files are prose only.
"""
import argparse
import copy
import json
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from .ai_editorial import (ROOT, binding, fingerprint, load_state, save_json,
                          source_text, validate_copy, validate_shape, REVIEW_SCHEMA)
from .collection import TAIPEI
from .review import review, duplicate
from .verified import load_verified, parse_time

QUEUE = 'data/editorial/queue.json'
RESULTS = 'data/editorial/results'
RECEIPTS = 'data/editorial/receipts.json'


def read(root, name):
    return json.loads((Path(root) / name).read_text(encoding='utf-8'))


def alive(activity, now):
    return parse_time(activity.get('end_time') or activity['start_time']) > now


def request_for(row, source):
    activity = row['activity']
    source = copy.deepcopy(source)
    # Shared program evidence may contain ended or unselected siblings. Verify
    # the requested session, never require those siblings to remain on sale.
    if 'opentix_sessions' in source:
        sid = row['verification']['opentix_session_id']
        source['opentix_sessions'] = [s for s in source['opentix_sessions'] if s['session_id'] == sid]
    if source.get('automated_review', {}).get('source_type') == 'gameislearning':
        source['automated_review']['sessions'] = [s for s in source['automated_review']['sessions']
                                                 if s['start_time'] == activity['start_time']]
    return {'activity_id': activity['id'], 'source_hash': fingerprint(binding(activity)),
            'activity': binding(activity), 'row': row, 'source': source}


def check_request(item):
    activity = item['row']['activity']
    if (item['activity_id'] != activity['id'] or item['activity'] != binding(activity)
            or item['source_hash'] != fingerprint(binding(activity))):
        raise ValueError('Queue source binding mismatch')
    if not re.fullmatch(r'[a-z0-9_-]+', activity['id']):
        raise ValueError('Invalid activity ID')


def result_name(item):
    check_request(item)
    return item['activity_id'] + '-' + item['source_hash'] + '.json'


def pending(root=ROOT, now=None):
    now = now or datetime.now(TAIPEI)
    queue = read(root, QUEUE)
    if queue.get('schema_version') != 1:
        raise ValueError('Unsupported queue version')
    catalog = read(root, 'data/verified_activities.json')
    published_ids = {r['activity']['id'] for r in catalog['activities']}
    state = load_state(Path(root) / 'data/ai_taigi.json')
    receipts = read(root, RECEIPTS)['results']
    items, ids = [], set()
    for item in queue['items']:
        check_request(item)
        aid = item['activity_id']
        if aid in ids:
            raise ValueError('Duplicate queue ID')
        ids.add(aid)
        activity = item['row']['activity']
        if (aid in published_ids or aid in state['protected_activity_ids'] or not alive(activity, now)
                or duplicate(activity, catalog, item['row']['verification'].get('opentix_session_id'))
                or result_name(item) in receipts):
            continue
        items.append(item)
    return sorted(items, key=lambda i: (i['activity']['start_time'], i['activity_id']))


def prepare(folder, root=ROOT, now=None):
    """Run existing verification in isolation. Never publish the staged catalog."""
    root = Path(root)
    now = now or datetime.now(TAIPEI)
    before = read(root, 'data/verified_activities.json')
    before_ids = {row['activity']['id'] for row in before['activities']}
    existing = {i['activity_id']: i for i in pending(root, now)}
    with tempfile.TemporaryDirectory() as temp:
        staged = Path(temp)
        shutil.copytree(str(root / 'data'), str(staged / 'data'))
        audit = review(folder, root=staged, now=now, apply=True)
        after = read(staged, 'data/verified_activities.json')
        # Local structural validation of the full result; live evidence was
        # obtained by the source-specific verifiers above.
        active = {a.id for a in load_verified(staged / 'data/verified_activities.json', now=now)}
        for row in after['activities']:
            aid = row['activity']['id']
            if aid in before_ids or aid not in active:
                continue
            source = after['sources'][row['verification']['source_id']]
            existing[aid] = request_for(row, source)
    audit['applied_to_catalog'] = False
    audit['destination'] = QUEUE
    queue = {'schema_version': 1, 'prepared_at': now.isoformat(timespec='seconds'),
             'collection_run': audit.get('collection_run'),
             'items': sorted(existing.values(), key=lambda i: i['activity_id'])}
    save_json(root / QUEUE, queue)
    save_json(root / 'data/audit/latest-candidate-review.json', audit)
    print('Verified pending editorial:', len(queue['items']))
    return queue


def validate_result(result, item, guide):
    """Mechanical checks supplement, never pretend to replace, AI editing."""
    check_request(item)
    required = {'schema_version', 'activity_id', 'source_hash', 'guide_hash',
                'summary_taigi', 'description_taigi', 'uncertain_terms',
                'review', 'dictionary_evidence', 'editor', 'edited_at'}
    if not isinstance(result, dict) or set(result) != required or result['schema_version'] != 1:
        raise ValueError('Invalid returned editorial format')
    if (result['activity_id'] != item['activity_id'] or result['source_hash'] != item['source_hash']
            or result['guide_hash'] != fingerprint(guide)):
        raise ValueError('Stale source or editorial guide')
    validate_copy({k: result[k] for k in ('summary_taigi', 'description_taigi', 'uncertain_terms')}, item['activity'])
    if result['uncertain_terms']:
        raise ValueError('Unresolved dictionary terms')
    editor = result['editor']
    if (not isinstance(editor, dict) or set(editor) != {'provider', 'model'}
            or not all(isinstance(v, str) and 0 < len(v.strip()) <= 100 for v in editor.values())):
        raise ValueError('Missing editor provenance')
    parse_time(result['edited_at'])
    evidence = result['dictionary_evidence']
    if not isinstance(evidence, list) or len(evidence) > 100:
        raise ValueError('Invalid dictionary evidence')
    for entry in evidence:
        if not isinstance(entry, dict) or entry.get('status') != 'ok' or not entry.get('readings'):
            raise ValueError('Dictionary lookup was not completed')
    review_data = result['review']
    validate_shape(review_data, REVIEW_SCHEMA)
    if (not all(review_data[k] for k in ('facts_match', 'natural_taiwanese', 'people_and_content_complete'))
            or review_data['issues'] or not review_data['evidence']):
        raise ValueError('Editorial review did not pass')
    prose = result['summary_taigi'] + '\n' + result['description_taigi']
    original = source_text(item['activity'])
    for evidence in review_data['evidence']:
        if (not evidence['claim'].strip() or evidence['claim'] not in prose
                or not evidence['quote'].strip() or evidence['quote'] not in original):
            raise ValueError('Editorial evidence mismatch')
    return result


def attach(catalog, item):
    # Use a per-session evidence key so a new session never overwrites another
    # session's historical source proof (including shared series sources).
    row = copy.deepcopy(item['row'])
    key = 'editorial_' + item['activity_id'] + '_' + item['source_hash'][:16]
    row['verification']['source_id'] = key
    catalog['sources'][key] = copy.deepcopy(item['source'])
    catalog['activities'].append(row)


def ingest(root=ROOT, now=None, live_check=True):
    """Apply valid returned files. Stale/expired results cannot publish anything.

    Writes are staged in memory until ALL selected files and new sources pass.
    CI commits only after the website and frontend tests also succeed.
    """
    root = Path(root)
    now = now or datetime.now(TAIPEI)
    catalog = read(root, 'data/verified_activities.json')
    state = load_state(root / 'data/ai_taigi.json')
    receipts = read(root, RECEIPTS)
    guide = (root / 'TAIGI_EDITORIAL.md').read_text(encoding='utf-8')
    new_catalog = {'schema_version': 1, 'sources': {}, 'activities': []}
    accepted = []
    for item in pending(root, now):
        name = result_name(item)
        path = root / RESULTS / name
        if not path.exists():
            continue
        if path.is_symlink() or path.stat().st_size > 150000:
            raise ValueError('Unsafe editorial file')
        result = validate_result(json.loads(path.read_text(encoding='utf-8')), item, guide)
        if duplicate(item['row']['activity'], new_catalog, item['row']['verification'].get('opentix_session_id')):
            raise ValueError('Duplicate returned session')
        attach(new_catalog, item)
        attach(catalog, item)
        state['editions'][item['activity_id']] = dict(result, status='approved', binding=item['activity'],
                                                     model=result['editor']['model'], generation=[])
        receipts['results'][name] = {'activity_id': item['activity_id'], 'source_hash': item['source_hash'],
                                     'result_hash': fingerprint(result), 'accepted_at': now.isoformat(timespec='seconds')}
        accepted.append(item['activity_id'])
    if not accepted:
        print('No new completed editorial to publish')
        return []
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        save_json(temp / 'new.json', new_catalog)
        # Only incoming sessions are live-rechecked. Daily expiration has no
        # incoming sessions and never depends on external source availability.
        checked = load_verified(temp / 'new.json', now=now, check_sources=live_check)
        posters = {a.id: a.cover_image for a in checked}
        for row in catalog['activities']:
            if row['activity']['id'] in posters:
                row['activity']['cover_image'] = posters[row['activity']['id']]
        save_json(temp / 'catalog.json', catalog)
        load_verified(temp / 'catalog.json', now=now)
    save_json(root / 'data/verified_activities.json', catalog)
    save_json(root / 'data/ai_taigi.json', state)
    save_json(root / RECEIPTS, receipts)
    queue = read(root, QUEUE)
    queue['items'] = [i for i in queue['items'] if i['activity_id'] not in accepted]
    save_json(root / QUEUE, queue)
    print('Accepted editorial:', len(accepted))
    return accepted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('prepare').add_argument('--candidates', type=Path, required=True)
    sub.add_parser('ingest')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.candidates)
    else:
        ingest()


if __name__ == '__main__':
    main()
