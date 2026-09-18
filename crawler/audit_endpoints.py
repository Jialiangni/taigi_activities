"""Probe legacy ticket-search endpoints without treating failures as zero events.

This is a diagnostic, not a crawler acceptance test or publication input.
Run: python3 -m crawler.audit_endpoints --output /tmp/ticket-probes.json
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .sources.accupass import AccupassCrawler
from .sources.opentix import OpentixCrawler


def extract_items(data, field):
    if not isinstance(data, dict):
        raise ValueError('JSON response must be an object')
    # These are the shapes expected by the existing adapters, not a verified API contract.
    for parent in (data, data.get('data'), data.get('result')):
        if isinstance(parent, dict) and field in parent:
            if not isinstance(parent[field], list):
                raise ValueError('Expected an event list')
            return parent[field]
    raise ValueError('Expected event-list field is absent')


def probe(source, url, field, opener=urlopen):
    result = dict(source=source, url=url,
                  checked_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                  crawler_verified=False)
    try:
        request = Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
        with opener(request, timeout=20) as response:
            result['http_status'] = response.status
            result['content_type'] = response.headers.get('Content-Type', '')
            if response.status != 200:
                result['status'] = 'http_error'
                return result
            if response.geturl() != url:
                result['status'] = 'unexpected_redirect'
                return result
            raw = response.read(4_000_001)
            if len(raw) > 4_000_000:
                raise ValueError('Response exceeds size limit')
            result['sha256'] = hashlib.sha256(raw).hexdigest()
            items = extract_items(json.loads(raw), field)
            result['items_received'] = len(items)
            result['status'] = 'response_received' if items else 'empty_response'
    except HTTPError as exc:
        result.update(status='http_error', http_status=exc.code)
    except (URLError, TimeoutError, OSError):
        # Do not put request/exception strings into logs: later adapters may use credentials.
        result['status'] = 'network_error'
    except (ValueError, UnicodeError):
        result['status'] = 'invalid_response'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    targets = [
        ('accupass', AccupassCrawler.SEARCH_API + '?' + urlencode(dict(
            keyword='台語', page=1, size=20, city='all', sort='start_time')), 'events'),
        ('opentix', OpentixCrawler.SEARCH_API + '?' + urlencode(dict(
            keyword='台語', offset=0, limit=20, sort='ON_SALE_DATE_ASC')), 'programs'),
    ]
    results = [probe(*target) for target in targets]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for item in results:
        print('{}: {} (HTTP {})'.format(item['source'], item['status'], item.get('http_status', '-')))
    print('Only endpoint diagnostics; pagination, session accuracy and coverage are not certified.')
    return 1 if any(r['status'] not in ('response_received', 'empty_response') for r in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
