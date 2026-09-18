"""Authorized Page feeds plus all API-visible comment levels; review candidates only."""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from ..social import SocialCrawler, read_pages, post_candidate
from ..collection import CollectionError, Result, relevant

WATCHLIST = Path(__file__).resolve().parents[2] / 'data/facebook_pages.json'


def watched_pages():
    return json.loads(WATCHLIST.read_text(encoding='utf-8'))['pages']


def link_urls(item):
    """Keep link evidence, including FB redirect wrappers; never visit arbitrary links."""
    values = re.findall(r'https?://[^\s<>"\u3000]+', item.get('message') or '')
    stack = [item.get('attachment'), item.get('attachments')]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                if key == 'url' and isinstance(value, str):
                    values.append(value)
                elif key in ('data', 'target', 'subattachments'):
                    stack.append(value)
        elif isinstance(node, list):
            stack.extend(node)
    output = []
    for url in values:
        url = url.rstrip('.,;!?)\u3002\uff0c\uff1b\uff01\uff09\u300d\u300f')
        try:
            p = urlsplit(url)
            if p.hostname in ('l.facebook.com', 'lm.facebook.com', 'www.facebook.com') and p.path == '/l.php':
                url = parse_qs(p.query).get('u', [url])[0]
                p = urlsplit(url)
            if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
                continue
            if url not in output:
                output.append(url)
        except ValueError:
            continue
    return output


@dataclass
class FacebookResult(Result):
    page_status: list = field(default_factory=list)


class FacebookCrawler(SocialCrawler):
    source_id = 'facebook'
    required_env = ('FACEBOOK_ACCESS_TOKEN',)

    def __init__(self, keywords=None, max_pages=20, env=None, max_comment_pages=20, max_posts=200, pages=None):
        super().__init__(keywords, max_pages, env)
        self.max_comment_pages, self.max_posts = max_comment_pages, max_posts
        self.pages = watched_pages() if pages is None else pages

    def collect(self, client):
        result = FacebookResult(self.source_id, 'authorized_meta_api_feed_and_comments')
        try:
            mapping = json.loads(self.env.get('FACEBOOK_PAGE_ID_MAP') or '{}')
            if not isinstance(mapping, dict) or any(k not in {p['handle'] for p in self.pages} or not isinstance(v, str) or not re.fullmatch(r'\d+', v) for k, v in mapping.items()):
                raise CollectionError('invalid_facebook_page_id_map')
            legacy = [p.strip() for p in self.env.get('FACEBOOK_PAGE_IDS', '').split(',') if p.strip()]
            if any(not re.fullmatch(r'\d+', p) for p in legacy):
                raise CollectionError('numeric_facebook_page_ids_required')
        except (ValueError, CollectionError):
            result.error('facebook_configuration', CollectionError('invalid_facebook_page_configuration'))
            return result
        targets = {}
        for spec in self.pages:
            pid = mapping.get(spec['handle'])
            state = {'handle': spec['handle'], 'url': spec['url'], 'page_id': pid,
                     'status': 'pending' if pid else 'needs_configuration'}
            result.page_status.append(state)
            if pid:
                targets.setdefault(pid, []).append(state)
        for pid in legacy:
            if pid not in targets:
                state = {'page_id': pid, 'status': 'pending'}
                result.page_status.append(state)
                targets[pid] = [state]
        if not self.env.get('FACEBOOK_ACCESS_TOKEN'):
            for state in result.page_status:
                state['status'] = 'needs_configuration'
            result.status = 'needs_configuration'
            result.notes.append('FACEBOOK_ACCESS_TOKEN is missing; feed and comments have NOT been read.')
        else:
            try:
                base = self.graph_base()
                for pid, states in targets.items():
                    before = len(result.errors)
                    try:
                        count = self.read_page(client, result, base, pid, any('handle' in s for s in states))
                        for state in states:
                            state['posts_read'] = count
                    except CollectionError as e:
                        result.error('facebook_page:' + pid, e)
                    for state in states:
                        state['status'] = 'partial' if len(result.errors) > before else 'ok'
                        state['coverage_complete'] = False
            except CollectionError as e:
                result.error('facebook_api', e)
                for state in result.page_status:
                    if state['status'] == 'pending': state['status'] = 'failed'
        if any(s['status'] == 'needs_configuration' for s in result.page_status):
            result.notes.append('Map every watched handle to a verified numeric Page ID using FACEBOOK_PAGE_ID_MAP; bare FACEBOOK_PAGE_IDS do not prove watchlist coverage.')
            if result.status == 'ok':
                result.status = 'partial' if targets else 'needs_configuration'
        if not targets:
            result.status = 'needs_configuration'
        if result.errors and result.candidates:
            result.status = 'partial'
        result.notes.append('Comments use filter=stream and cursor pagination, including visible replies; permissions, hidden/deleted comments and configured limits prevent a complete-coverage claim. Empty comments are not proof of absence.')
        return result

    def read_page(self, client, result, base, pid, keep_all):
        token = self.env['FACEBOOK_ACCESS_TOKEN']
        params = {'fields': 'id,message,permalink_url,created_time,attachments{url,target,subattachments}', 'limit': 100}
        count = 0
        for posts, ev in read_pages(client, base + '/' + pid + '/feed', params, token, self.max_pages):
            for post in posts:
                if count >= self.max_posts:
                    raise CollectionError('facebook_post_limit_reached')
                count += 1
                try:
                    self.read_post(client, result, base, pid, post, ev, keep_all)
                except CollectionError as e:
                    result.error('facebook_page:' + pid, e)
        return count

    def read_post(self, client, result, base, pid, post, ev, keep_all):
        post_id = str(post.get('id') or '')
        if not re.fullmatch(r'\d+(?:_\d+)?', post_id):
            raise CollectionError('invalid_facebook_post_id')
        comments, comment_requests, links = [], [], []
        for url in link_urls(post):
            links.append({'url': url, 'origin': 'post', 'source_url': post.get('permalink_url'), 'evidence': ev})
        comment_count, status = 0, 'checked_visible_comments'
        params = {'fields': 'id,message,created_time,permalink_url,parent{id},from{id},attachment',
                  'filter': 'stream', 'order': 'chronological', 'limit': 100}
        try:
            for items, cev in read_pages(client, base + '/' + post_id + '/comments', params,
                                         self.env['FACEBOOK_ACCESS_TOKEN'], self.max_comment_pages):
                comment_requests.append(cev)
                for item in items:
                    comment_count += 1
                    urls = link_urls(item)
                    message = item.get('message') or ''
                    # Other commenters' names/IDs are not retained; page authorship may be unavailable.
                    author = (item.get('from') or {}).get('id')
                    by_page = str(author) == pid if author else None
                    if urls or relevant(message, self.keywords) or any(w in message for w in ('報名', '取消', '延期', '額滿')):
                        record = {'id': item.get('id'), 'parent_id': (item.get('parent') or {}).get('id'),
                                  'message': message, 'created_time': item.get('created_time'),
                                  'source_url': item.get('permalink_url') or post.get('permalink_url'),
                                  'is_page_author': by_page, 'evidence': cev}
                        comments.append(record)
                        for url in urls:
                            links.append({'url': url, 'origin': 'comment', 'comment_id': item.get('id'),
                                          'source_url': record['source_url'], 'is_page_author': by_page, 'evidence': cev})
        except CollectionError as e:
            status = 'partial'
            result.error('facebook_comments:' + post_id, e)
        if not comment_count and status != 'partial':
            status = 'no_visible_comments_not_proof_of_absence'
        text = '\n'.join([post.get('message') or ''] + [c['message'] for c in comments]).strip()
        if not (keep_all or relevant(text, self.keywords) or status == 'partial'):
            return
        merged = dict(post, message=text or '粉專貼文（文字未提供，須人工核對圖片或附件）')
        row = post_candidate(self.source_id, merged, ev, 'message', 'permalink_url', 'created_time')
        if not row:
            raise CollectionError('facebook_post_missing_permalink')
        row.update(page_id=pid, post_text=post.get('message') or '', comments=comments,
                   comment_status=status, comments_read=comment_count, comment_requests=comment_requests,
                   discovered_links=links)
        row['issues'].append('comment_links_require_organizer_and_event_verification')
        if status == 'partial': row['issues'].append('comments_incomplete')
        if not post.get('message'): row['issues'].append('image_or_attachment_requires_manual_review')
        result.candidates.append(row)
