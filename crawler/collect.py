"""Collect review candidates from real sources; never write the published calendar."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from .collection import Client, CollectionError, Result, KEYWORDS, TAIPEI
from .culture import CultureCrawler
from .institutions import registry
from .web_sources import WebsiteCrawler
from .sources.accupass import AccupassCrawler
from .sources.opentix import OpentixCrawler
from .sources.eraticket import EraTicketCrawler
from .sources.facebook import FacebookCrawler
from .sources.instagram import InstagramCrawler
from .sources.threads import ThreadsCrawler
from .sources.li_kang_khiok import LiKangKhiokCrawler
from .sources.le_chang import LeChangCrawler
from .sources.tmofa import TmofaCrawler
from .sources.tfam import TfamCrawler


def collectors(config, selected=None):
    keywords = config.get('keywords') or KEYWORDS
    limits = config.get('limits', {})
    pages, details = limits.get('search_pages', 20), limits.get('details', 200)
    definitions = registry()
    sources = {
        'accupass': AccupassCrawler(keywords, pages, details),
        'opentix': OpentixCrawler(keywords, pages, details),
        'eraticket': EraTicketCrawler(keywords, pages, details),
        'culture_open_data': CultureCrawler(keywords, definitions),
        'facebook': FacebookCrawler(keywords, pages),
        'instagram': InstagramCrawler(hashtags=config.get('instagram_hashtags'), keywords=keywords, max_pages=pages),
        'threads': ThreadsCrawler(keywords, pages),
        'li_kang_khiok': LiKangKhiokCrawler(keywords, limits.get('feed_pages', 5)),
        'le_chang': LeChangCrawler(keywords, limits.get('feed_pages', 5)),
    }
    for spec in definitions:
        sources[spec['id']] = WebsiteCrawler(spec, keywords, limits.get('website_pages', 30))
    sources['tmofa'] = TmofaCrawler(keywords)
    sources['tfam'] = TfamCrawler(keywords)
    requested = set(selected or sources)
    for group in ('public_libraries', 'museums', 'government', 'organizations'):
        if group in requested:
            requested.remove(group)
            requested.update(s['id'] for s in definitions if s['group'] == group)
    unknown = requested - set(sources)
    if unknown:
        raise ValueError('Unknown sources: ' + ', '.join(sorted(unknown)))
    return {k: v for k, v in sources.items() if k in requested}


def run(config, output, selected=None, client_factory=Client):
    instances = collectors(config, selected)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    results = []
    def work(pair):
        key, instance = pair
        started_at = datetime.now(TAIPEI).isoformat(timespec='seconds')
        client = client_factory()
        client.progress = lambda count: print('{}: {} successful responses'.format(key, count), flush=True)
        try:
            result = instance.collect(client)
        except CollectionError as e:
            result = Result(key, 'collector')
            result.error(key, e)
        except Exception as e:
            # Preserve a failing source report while letting other independent sources finish.
            # Do not serialize exception values which may contain credentials.
            result = Result(key, 'collector', status='failed')
            result.errors.append({'code': 'unexpected_' + type(e).__name__})
        rows = {r['id']: r for r in result.candidates}
        result.candidates = list(rows.values())
        if result.errors and result.candidates:
            result.status = 'partial'
        data = result.to_dict()
        data['requests'] = client.requests
        data['started_at'] = started_at
        data['completed_at'] = datetime.now(TAIPEI).isoformat(timespec='seconds')
        return data
    workers = min(4, max(1, config.get('workers', 3)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, item) for item in instances.items()]
        for future in as_completed(futures):
            data = future.result()
            target = output / (data['source_id'] + '.json')
            tmp = target.with_suffix('.tmp')
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            tmp.replace(target)
            results.append(data)
            print('{}: {} / {} candidates'.format(data['source_id'], data['status'], len(data['candidates'])), flush=True)
    results.sort(key=lambda r: r['source_id'])
    report = {'schema_version': 1, 'collected_at': datetime.now(TAIPEI).isoformat(timespec='seconds'),
              'publication_changed': False, 'config': config,
              'sources': [dict({k: r[k] for k in ('source_id', 'method', 'status', 'errors', 'notes', 'coverage_complete')},
                              candidate_count=len(r['candidates']), successful_response_count=len(r['requests']),
                              started_at=r['started_at'], completed_at=r['completed_at']) for r in results]}
    # No tokens are accepted in config; only documented collection limits, keywords and tags.
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path('config.example.json'))
    parser.add_argument('--sources', help='Comma-separated source IDs or institution groups; default all')
    parser.add_argument('--output', type=Path, default=Path('data/candidates'))
    parser.add_argument('--max-details', type=int)
    parser.add_argument('--website-pages', type=int)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    allowed = {'schema_version', 'keywords', 'limits', 'workers', 'instagram_hashtags'}
    if set(config) - allowed:
        parser.error('Unsupported configuration fields; do not place tokens in config')
    if args.max_details is not None:
        config.setdefault('limits', {})['details'] = args.max_details
    if args.website_pages is not None:
        config.setdefault('limits', {})['website_pages'] = args.website_pages
    for v in config.get('limits', {}).values():
        if not isinstance(v, int) or v < 1:
            parser.error('All collection limits must be positive integers')
    report = run(config, args.output, args.sources.split(',') if args.sources else None)
    # Missing optional social authorization is reported, not silently called successful.
    return 1 if any(r['status'] == 'failed' or r['errors'] for r in report['sources']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
