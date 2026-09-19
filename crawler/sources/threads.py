"""Official Threads searches restricted to an exact account list, plus visible replies."""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from ..social import SocialCrawler, read_pages, post_candidate
from ..collection import CollectionError, Result

WATCHLIST = Path(__file__).resolve().parents[2] / 'data/threads_accounts.json'


def watched_accounts():
    return json.loads(WATCHLIST.read_text(encoding='utf-8'))['accounts']


def link_urls(text):
    output = []
    for value in re.findall(r'https?://[^\s<>"\u3000]+', text or ''):
        value = value.rstrip('.,;!?)\u3002\uff0c\uff1b\uff01\uff09\u300d\u300f')
        try:
            parsed = urlsplit(value)
            if (parsed.scheme in ('http', 'https') and parsed.hostname and
                    not parsed.username and not parsed.password and value not in output):
                output.append(value)
        except ValueError:
            continue
    return output


@dataclass
class ThreadsResult(Result):
    account_status: list = field(default_factory=list)


class ThreadsCrawler(SocialCrawler):
    source_id = 'threads'
    required_env = ('THREADS_ACCESS_TOKEN',)

    def __init__(self, keywords=None, max_pages=20, env=None, accounts=None, max_reply_pages=20):
        super().__init__(keywords, max_pages, env)
        self.accounts = watched_accounts() if accounts is None else accounts
        self.max_reply_pages = max_reply_pages

    def collect(self, client):
        result = ThreadsResult(self.source_id, 'threads_keyword_search_by_exact_author_and_conversations')
        for account in self.accounts:
            result.account_status.append({'username': account['username'], 'url': account['url'],
                                          'status': 'pending'})
        if not self.env.get('THREADS_ACCESS_TOKEN'):
            result.status = 'needs_configuration'
            for state in result.account_status:
                state['status'] = 'needs_configuration'
            result.notes.append('THREADS_ACCESS_TOKEN is missing; watched posts and replies have NOT been read.')
            return result
        seen = set()
        for account, state in zip(self.accounts, result.account_status):
            before_errors, before_posts = len(result.errors), len(seen)
            for keyword in self.keywords:
                params = {'q': keyword, 'author_username': account['username'],
                          'search_type': 'RECENT', 'search_mode': 'KEYWORD',
                          'fields': 'id,text,permalink,timestamp,username,has_replies,is_reply,is_quote_post',
                          'limit': 100}
                try:
                    for posts, evidence in read_pages(
                            client, 'https://graph.threads.com/v1.0/keyword_search', params,
                            self.env['THREADS_ACCESS_TOKEN'], self.max_pages):
                        for post in posts:
                            post_id = str(post.get('id') or '')
                            username = (post.get('username') or '').lower()
                            if (not post_id or username != account['username'].lower()
                                    or post.get('is_reply') is True or post_id in seen):
                                continue
                            seen.add(post_id)
                            self.read_post(client, result, account, post, evidence)
                except CollectionError as error:
                    result.error('threads_account:' + account['username'], error)
            state['posts_read'] = len(seen) - before_posts
            state['status'] = 'partial' if len(result.errors) > before_errors else 'ok'
            state['coverage_complete'] = False
        if result.errors and result.candidates:
            result.status = 'partial'
        result.notes.append('Exact author_username search still only returns posts matching configured keywords.')
        result.notes.append('Replies use the API-visible flattened conversation; hidden/deleted replies and limits prevent a complete-coverage claim.')
        return result

    def read_post(self, client, result, account, post, evidence):
        post_id = str(post['id'])
        replies, reply_requests = [], []
        links = [{'url': url, 'origin': 'post', 'is_page_author': True}
                 for url in link_urls(post.get('text'))]
        reply_count, status = 0, 'no_replies_reported'
        if post.get('has_replies'):
            status = 'checked_visible_conversation'
            params = {'fields': 'id,text,permalink,timestamp,username,has_replies,is_reply,replied_to',
                      'reverse': 'false', 'limit': 100}
            try:
                for items, reply_evidence in read_pages(
                        client, 'https://graph.threads.com/v1.0/' + post_id + '/conversation', params,
                        self.env['THREADS_ACCESS_TOKEN'], self.max_reply_pages):
                    reply_requests.append(reply_evidence)
                    for reply in items:
                        reply_count += 1
                        urls = link_urls(reply.get('text'))
                        by_account = (reply.get('username') or '').lower() == account['username'].lower()
                        if urls:
                            replies.append({'text': reply.get('text') or '', 'timestamp': reply.get('timestamp'),
                                            'is_account_author': by_account})
                            links.extend({'url': url, 'origin': 'reply', 'is_page_author': by_account}
                                         for url in urls)
            except CollectionError as error:
                status = 'partial'
                result.error('threads_conversation:' + post_id, error)
        row = post_candidate(self.source_id, post, evidence, 'text', 'permalink', 'timestamp')
        if not row:
            return
        row.update(account_username=account['username'], post_text=post.get('text') or '',
                   replies=replies, reply_status=status, replies_read=reply_count,
                   reply_requests=reply_requests, discovered_links=links)
        row['issues'].append('reply_links_require_event_verification')
        if status == 'partial':
            row['issues'].append('replies_incomplete')
        result.candidates.append(row)
