"""Official Meta API readers. Credentials only via environment; posts stay candidates."""
import os
import re
from urllib.parse import urlencode, urlsplit, parse_qs
from .collection import Collector, CollectionError, Result, candidate, relevant, KEYWORDS


def read_pages(client, url, params, token, max_pages, allow_same_cursor=False):
    seen = set()
    seen_pages = set()
    for _ in range(max_pages):
        data, evidence = client.json(url + '?' + urlencode(params), token=token)
        if not isinstance(data, dict) or data.get('error'):
            raise CollectionError('api_error')
        if not isinstance(data.get('data'), list):
            raise CollectionError('api_schema_changed')
        fingerprint = tuple(str(x.get('id')) for x in data['data'])
        if fingerprint and fingerprint in seen_pages:
            raise CollectionError('repeated_api_page')
        seen_pages.add(fingerprint)
        yield data['data'], evidence
        paging = data.get('paging') or {}
        next_url = paging.get('next')
        if not next_url:
            return
        # Never follow an arbitrary next URL or persist its embedded access_token.
        if urlsplit(next_url).hostname != urlsplit(url).hostname:
            raise CollectionError('unsafe_paging_host')
        after = (paging.get('cursors') or {}).get('after') or parse_qs(urlsplit(next_url).query).get('after', [None])[0]
        if not after or (after in seen and not allow_same_cursor):
            raise CollectionError('invalid_or_repeated_cursor')
        seen.add(after)
        params = dict(params, after=after)
    raise CollectionError('pagination_limit_reached')


def post_candidate(source, post, ev, text_field, url_field, published_field):
    text, url = post.get(text_field, ''), post.get(url_field, '')
    if not post.get('id') or not text or not url:
        return None
    if urlsplit(url).scheme != 'https':
        raise CollectionError('invalid_post_url')
    return candidate(source, url, text.splitlines()[0][:160], text, ev,
                     {'published_at': post.get(published_field), 'start_time': None,
                      'end_time': None, 'venue': None, 'city': None, 'is_free': None},
                     'post', ['manual_event_verification_required', 'post_timestamp_is_not_event_time'],
                     str(post['id']))


class SocialCrawler(Collector):
    source_id = ''
    required_env = ()

    def __init__(self, keywords=None, max_pages=20, env=None):
        self.keywords, self.max_pages = keywords or KEYWORDS, max_pages
        self.env = os.environ if env is None else env

    def collect(self, client):
        result = Result(self.source_id, 'authorized_meta_api')
        missing = [name for name in self.required_env if not self.env.get(name)]
        if missing:
            result.status = 'needs_configuration'
            result.notes.append('Required environment variables: ' + ', '.join(missing))
            return result
        try:
            self.read(client, result)
        except CollectionError as e:
            result.error('meta_api:' + self.source_id, e)
        result.notes.append('API access is limited to granted scopes and platform visibility; no full-platform coverage claim.')
        return result

    def graph_base(self):
        version = self.env.get('META_GRAPH_VERSION') or 'v26.0'
        if not re.fullmatch(r'v\d+\.0', version):
            raise CollectionError('invalid_graph_version')
        return 'https://graph.facebook.com/' + version

    def add_posts(self, result, items, ev, text, url, timestamp):
        for post in items:
            if relevant(post.get(text, ''), self.keywords):
                row = post_candidate(self.source_id, post, ev, text, url, timestamp)
                if row:
                    result.candidates.append(row)
