"""Build a portable, redacted review snapshot from an authorized Facebook run."""
import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def _compact(value, limit):
    value = re.sub(r'\s+', ' ', value or '').strip()
    return value if len(value) <= limit else value[:limit - 1].rstrip() + '…'


def _public_url(value):
    """Drop common tracking parameters while preserving the public event target."""
    try:
        parsed = urlsplit(value or '')
    except ValueError:
        return None
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        return None
    query = [(key, item) for key, item in parse_qsl(parsed.query, keep_blank_values=True)
             if not key.lower().startswith('utm_') and key.lower() not in ('fbclid', 'gclid')]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ''))


def _evidence(rows):
    """Retain integrity metadata, never authorized endpoint URLs or request data."""
    output = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = {key: row[key] for key in ('fetched_at', 'http_status', 'sha256') if row.get(key) is not None}
        if item and item not in output:
            output.append(item)
    return output


def build_facebook_review(raw):
    """Create reviewable candidates without commenter text, identity, or API credentials."""
    handles = {}
    for state in raw.get('page_status', []):
        if state.get('page_id') and state.get('handle'):
            handles[str(state['page_id'])] = state['handle']
    candidates = []
    for source in raw.get('candidates', []):
        source_url = _public_url(source.get('source_url'))
        if not source_url:
            continue
        excerpt = _compact(source.get('post_text'), 600)
        title = _compact(source.get('title'), 160) or 'Facebook 粉專活動公告候選'
        links = []
        seen = set()
        for found in source.get('discovered_links', []):
            url = _public_url(found.get('url'))
            if not url or url in seen:
                continue
            seen.add(url)
            links.append({'url': url, 'origin': found.get('origin') if found.get('origin') in ('post', 'comment') else 'unknown',
                          'is_page_author': found.get('is_page_author') if found.get('origin') == 'comment' else True})
        official_links = [row['url'] for row in links if row['is_page_author'] is True]
        if excerpt:
            description = '粉專公告摘要：' + excerpt
        else:
            description = '粉專以圖片或附件發布活動訊息，文字內容仍待人工核對。'
        if official_links:
            description += ' 已找到粉專貼文或粉專本人留言提供的活動連結，仍須逐項核實。'
        elif links:
            description += ' 留言中找到活動線索，但留言者身分未能確認，不能當作官方證據。'
        else:
            description += ' 尚未找到可供核實的活動連結。'
        evidence = _evidence([source.get('evidence', {})] + source.get('comment_requests', []))
        review_context = {
            'page_handle': handles.get(str(source.get('page_id'))) or None,
            'post_excerpt': excerpt,
            'comment_status': source.get('comment_status'),
            'comments_read': source.get('comments_read', 0),
            'discovered_links': links,
            'official_link_count': len(official_links),
            'snapshot_evidence': evidence,
            'draft': {
                'title': title,
                'description': description,
                'unverified_fields': ['start_time', 'end_time', 'venue', 'city', 'address',
                                      'organizer', 'language', 'price_info', 'status']
            }
        }
        stable = 'facebook_review:' + str(source.get('id') or source_url)
        candidates.append({
            'id': hashlib.sha256(stable.encode()).hexdigest()[:24],
            'source_id': 'facebook_review', 'source_url': source_url, 'title': title,
            'text': description, 'kind': 'social_snapshot', 'review_status': 'pending',
            'fields': {}, 'language_hits': list(source.get('language_hits') or []),
            'issues': ['facebook_snapshot_needs_manual_review',
                       'official_event_fields_must_be_verified_before_publication'],
            'evidence': evidence, 'review_context': review_context
        })
    errors = [{'code': row.get('code', 'facebook_collection_error')}
              for row in raw.get('errors', []) if isinstance(row, dict)]
    return {
        'source_id': 'facebook_review',
        'method': 'redacted_public_page_snapshot_and_comment_link_discovery',
        'status': raw.get('status', 'failed'), 'candidates': candidates,
        'errors': errors,
        'notes': [
            'Only public Page excerpts, discovered URLs, authorship confidence and response hashes are retained.',
            'Commenter names, IDs, comment text, Graph API request URLs and credentials are excluded.',
            'Draft text is a review aid; all event facts require official-source verification before publication.'
        ],
        'coverage_complete': False,
        'requests': [], 'started_at': raw.get('started_at'), 'completed_at': raw.get('completed_at')
    }
