"""Shared collection primitives. Candidate documents never certify event facts."""
import hashlib
import gzip
import io
import json
import re
import ssl
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit, quote
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor

TAIPEI = timezone(timedelta(hours=8))
KEYWORDS = ['台語', '臺語', '台灣話', '臺灣話', '閩南語', '囡仔古', '歌仔戲', '布袋戲', '唸歌', '台文']


class CollectionError(Exception):
    def __init__(self, code, detail=''):
        super().__init__(code)
        self.code, self.detail = code, detail


def canonical(url):
    p = urlsplit(url)
    if p.scheme not in ('https', 'http') or not p.hostname or p.username or p.password:
        raise CollectionError('invalid_url')
    return urlunsplit((p.scheme, p.netloc, quote(p.path, safe='/%:@'), quote(p.query, safe='=&%/:@,+;?'), ''))


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).hostname != urlsplit(req.full_url).hostname:
            # Public website redirects are recorded; never forward API authorization.
            if req.has_header('Authorization'):
                raise CollectionError('unsafe_auth_redirect')
        if urlsplit(newurl).scheme != 'https':
            raise CollectionError('insecure_redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Client:
    def __init__(self, timeout=20, delay=0.25):
        ctx = ssl.create_default_context()
        # macOS's system trust store is additional trusted CA material, not verify=False.
        if Path('/etc/ssl/cert.pem').exists():
            ctx.load_verify_locations('/etc/ssl/cert.pem')
        self.opener = build_opener(HTTPSHandler(context=ctx), SafeRedirect(), HTTPCookieProcessor(CookieJar()))
        self.timeout, self.delay = timeout, delay
        self.cache, self.requests = {}, []
        self.progress = None

    def get(self, url, payload=None, token=None, form=None, ajax=False):
        url = canonical(url)
        if urlsplit(url).scheme != 'https':
            raise CollectionError('https_required')
        if form is not None and (payload is not None or token):
            raise CollectionError('mixed_request_encoding')
        from urllib.parse import urlencode
        body = urlencode(form).encode() if form is not None else json.dumps(payload).encode() if payload is not None else None
        key = (url, body, bool(token), ajax)
        if not token and key in self.cache:
            return self.cache[key]
        headers = {'User-Agent': 'TaigiActivities/1.0 (public event research)', 'Accept': '*/*'}
        if ajax:
            headers['X-Requested-With'] = 'SW'
        if body is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded' if form is not None else 'application/json'
        if token:
            headers['Authorization'] = 'Bearer ' + token
        for attempt in range(2):
            time.sleep(self.delay)
            try:
                with self.opener.open(Request(url, data=body, headers=headers), timeout=self.timeout) as r:
                    raw = r.read(20_000_001)
                    if len(raw) > 20_000_000:
                        raise CollectionError('response_too_large')
                    if not raw:
                        raise CollectionError('empty_body')
                    if r.headers.get('Content-Encoding', '').lower() == 'gzip' or raw.startswith(b'\x1f\x8b'):
                        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as zipped:
                            raw = zipped.read(20_000_001)
                        if len(raw) > 20_000_000:
                            raise CollectionError('response_too_large')
                    encoding = r.headers.get_content_charset() or 'utf-8'
                    try:
                        text = raw.decode(encoding)
                    except (UnicodeError, LookupError):
                        text = raw.decode('utf-8', errors='replace')
                    evidence = {'url': url, 'final_url': r.url, 'http_status': r.status,
                                'request_method': 'POST' if body is not None else 'GET',
                                'fetched_at': datetime.now(TAIPEI).isoformat(timespec='seconds'),
                                'sha256': hashlib.sha256(raw).hexdigest()}
                    if payload is not None and not token:
                        evidence['request_body'] = payload
                    if form is not None:
                        evidence['request_form'] = {k: v for k, v in form.items() if not re.search(r'token|password|secret', k, re.I)}
                    if ajax:
                        evidence['request_headers'] = {'X-Requested-With': 'SW'}
                    self.requests.append(evidence)
                    if self.progress and len(self.requests) % 25 == 0:
                        self.progress(len(self.requests))
                    result = (text, evidence)
                    if not token:
                        self.cache[key] = result
                    return result
            except HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt == 0:
                    time.sleep(min(3, max(1, int(e.headers.get('Retry-After', '1')) if e.headers.get('Retry-After', '1').isdigit() else 1)))
                    continue
                raise CollectionError('http_' + str(e.code)) from None
            except (URLError, TimeoutError, OSError):
                raise CollectionError('network_or_tls_error') from None

    def json(self, url, payload=None, token=None):
        text, evidence = self.get(url, payload, token)
        try:
            return json.loads(text), evidence
        except ValueError:
            raise CollectionError('invalid_json') from None


class Node:
    def __init__(self, tag='', attrs=(), parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []

    def text(self):
        # Government pages may contain thousands of nested/unclosed layout tags.
        # Traverse iteratively so a valid response cannot exhaust Python's stack.
        stack, parts = [self], []
        while stack:
            item = stack.pop()
            if isinstance(item, Node):
                if item.tag not in ('script', 'style', 'noscript', 'nav', 'footer'):
                    stack.extend(reversed(item.children))
            else:
                parts.append(item)
        return ' '.join(parts).strip()

    def all(self, tag=None):
        stack = list(reversed(self.children))
        while stack:
            child = stack.pop()
            if isinstance(child, Node):
                if tag is None or child.tag == tag:
                    yield child
                stack.extend(reversed(child.children))

    def has_class(self, value):
        return value in self.attrs.get('class', '').split()


class Document(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = self.current = Node('document')
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in self.VOID:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        node = self.current
        while node.parent:
            if node.tag == tag:
                self.current = node.parent
                return
            node = node.parent

    def handle_data(self, data):
        self.current.children.append(data)

    def links(self, base):
        for a in self.root.all('a'):
            href = a.attrs.get('href', '')
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            try:
                yield canonical(urljoin(base, href)), re.sub(r'\s+', ' ', a.text()), a
            except CollectionError:
                continue

    def title(self):
        for tag in ('h1', 'title'):
            for node in self.root.all(tag):
                if node.text():
                    return node.text()
        return ''

    def content(self):
        for tag in ('article', 'main'):
            nodes = list(self.root.all(tag))
            if nodes:
                return max((x.text() for x in nodes), key=len)
        return self.root.text()

    def jsonld(self):
        for node in self.root.all('script'):
            if node.attrs.get('type') == 'application/ld+json':
                try:
                    yield json.loads(''.join(c for c in node.children if isinstance(c, str)))
                except ValueError:
                    continue


def plain(html):
    return re.sub(r'\s+', ' ', Document(html or '').root.text()).strip()


def relevant(text, keywords=KEYWORDS):
    return any(k in text for k in keywords)


def city_of(address):
    for name in ('臺北市', '新北市', '桃園市'):
        if name in (address or '').replace('台北市', '臺北市'):
            return name
    return None


def local_time(value):
    """Only explicit date + time; epoch seconds are UTC. Never fabricate a date."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(value, timezone.utc).astimezone(TAIPEI).isoformat()
    if not isinstance(value, str) or not re.search(r'\d{2}:\d{2}', value):
        return None
    try:
        dt = datetime.fromisoformat(value.replace('/', '-').replace('Z', '+00:00'))
        return dt.replace(tzinfo=dt.tzinfo or TAIPEI).astimezone(TAIPEI).isoformat()
    except ValueError:
        return None


def candidate(source, url, title, text, evidence, fields=None, kind='announcement', issues=None, key=None):
    # Preserve event and publication times separately; defaults remain unknown.
    fields = fields or {}
    stable = source + ':' + (key or url)
    return {'id': hashlib.sha256(stable.encode()).hexdigest()[:24], 'source_id': source,
            'source_url': url, 'title': title, 'text': text,
            'kind': kind, 'review_status': 'pending', 'fields': fields,
            'language_hits': [k for k in KEYWORDS if k in title + ' ' + text],
            'issues': issues or ['manual_event_verification_required'], 'evidence': evidence}


@dataclass
class Result:
    source_id: str
    method: str
    status: str = 'ok'
    candidates: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    coverage_complete: bool = False

    def error(self, url, error):
        self.errors.append({'url': url, 'code': error.code})
        self.status = 'partial' if self.candidates else 'failed'

    def to_dict(self):
        return asdict(self)


class Collector:
    def fetch_activities(self):
        raise CollectionError('use_collect_candidates_then_review',
                              'Unreviewed candidates cannot be returned as publishable Activity objects')
