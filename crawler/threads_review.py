"""Build portable, redacted review snapshots from authorized Threads searches."""
import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def _compact(value, limit):
    value = re.sub(r'\s+', ' ', value or '').strip()
    return value if len(value) <= limit else value[:limit - 1].rstrip() + '…'


def _url(value):
    try:
        parsed = urlsplit(value or '')
    except ValueError:
        return None
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        return None
    query = [(key, item) for key, item in parse_qsl(parsed.query, keep_blank_values=True)
             if not key.lower().startswith('utm_') and key.lower() not in ('igshid', 'fbclid', 'gclid')]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ''))


def _evidence(rows):
    output = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = {key: row[key] for key in ('fetched_at', 'http_status', 'sha256') if row.get(key) is not None}
        if item and item not in output:
            output.append(item)
    return output


def build_threads_review(raw):
    candidates = []
    for source in raw.get('candidates', []):
        source_url = _url(source.get('source_url'))
        if not source_url:
            continue
        excerpt = _compact(source.get('post_text'), 600)
        title = _compact(source.get('title'), 160) or 'Threads 活動公告候選'
        links, seen = [], set()
        for found in source.get('discovered_links', []):
            url = _url(found.get('url'))
            if not url or url in seen:
                continue
            seen.add(url)
            links.append({'url': url, 'origin': found.get('origin'),
                          'is_page_author': found.get('is_page_author')})
        trusted = [row['url'] for row in links if row['is_page_author'] is True]
        description = 'Threads 公告摘要：' + excerpt
        description += (' 已找到帳號本人提供的活動連結，交由自動核實。' if trusted else
                        ' 尚未找到帳號本人提供的官方活動連結。')
        evidence = _evidence([source.get('evidence', {})] + source.get('reply_requests', []))
        context = {'page_handle': source.get('account_username'), 'post_excerpt': excerpt,
                   'comment_status': source.get('reply_status'), 'comments_read': source.get('replies_read', 0),
                   'discovered_links': links, 'official_link_count': len(trusted),
                   'snapshot_evidence': evidence,
                   'draft': {'title': title, 'description': description,
                             'unverified_fields': ['start_time', 'end_time', 'venue', 'city', 'address',
                                                   'organizer', 'language', 'price_info', 'status']}}
        stable = 'threads_review:' + str(source.get('id') or source_url)
        candidates.append({'id': hashlib.sha256(stable.encode()).hexdigest()[:24],
                           'source_id': 'threads_review', 'source_url': source_url, 'title': title,
                           'text': description, 'kind': 'social_snapshot', 'review_status': 'pending',
                           'fields': {}, 'language_hits': list(source.get('language_hits') or []),
                           'issues': ['threads_snapshot_needs_tiered_review'],
                           'evidence': evidence, 'review_context': context})
    errors = [{'code': row.get('code', 'threads_collection_error')}
              for row in raw.get('errors', []) if isinstance(row, dict)]
    return {'source_id': 'threads_review',
            'method': 'redacted_threads_account_snapshot_and_reply_link_discovery',
            'status': raw.get('status', 'failed'), 'candidates': candidates, 'errors': errors,
            'notes': ['Public account excerpts, links, authorship confidence and hashes only.',
                      'Other users names and reply text are excluded from this review artifact.'],
            'coverage_complete': False, 'requests': [],
            'started_at': raw.get('started_at'), 'completed_at': raw.get('completed_at')}
