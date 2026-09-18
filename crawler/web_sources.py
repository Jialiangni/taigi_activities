"""Public announcement discovery via official RSS/Atom and bounded website traversal."""
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, urljoin, parse_qs, urlencode, urlunsplit
from .collection import Collector, CollectionError, Document, Result, candidate, relevant, plain, canonical

NAV = re.compile(r'活動|課程|研習|導覽|語音|展覽|特展|最新消息|新聞|藝文|展演|教育推廣|故事|訊息|消息|公告|下一頁|下頁|更多|next|news|event|activity', re.I)
BAD = re.compile(r'登入|註冊|隱私|採購|招標|徵才|決算|預算|人事|無障礙|列印|網站導覽|網站連結')

DETAIL = re.compile(r'News_Content|/(?:Event|News)_page\.aspx|/Exhibition_(?:page|Special)\.aspx|'
                    r'/ExhibitionAndEvent/Info/|/Content/\d|/post/|/\d{4}/\d{2}/|'
                    r'/mocweb/reg/[^/]+/Detail\.init\.ctr|/blog/articles/|/wSite/ct\?|/x(?:mdoc|ceventsnews)/cont\?|[?&](?:sid|s|cntId|xItem|dataserno)=', re.I)


def culture_portal_detail(doc, url):
    """Official registration pages have a logo h1 and JS-only related links."""
    title = next((n.text() for n in doc.root.all('div') if 'title_01' in n.attrs.get('class', '').split()), '')
    if not title:
        raise CollectionError('invalid_culture_portal_detail')
    body = doc.content().split('相關系列活動')[0]
    links = []
    for node in doc.root.all('a'):
        match = re.fullmatch(r"viewDetail\('([0-9]+)'\);?", node.attrs.get('onclick', '').strip())
        if match:
            links.append((url.split('?')[0] + '?actId=' + match.group(1), node.text(), node))
    return title, body, links


def parse_feed(text, source, evidence, keywords):
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise CollectionError('unsafe_xml')
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        raise CollectionError('invalid_feed') from None
    def leaf(tag):
        return tag.rsplit('}', 1)[-1]
    entries = [n for n in root.iter() if leaf(n.tag) in ('entry', 'item')]
    if leaf(root.tag) not in ('rss', 'feed', 'RDF'):
        raise CollectionError('invalid_feed')
    rows = []
    for entry in entries:
        fields = {}
        links = []
        for n in entry:
            name = leaf(n.tag)
            if name == 'link':
                if n.attrib.get('rel', 'alternate') == 'alternate':
                    links.append(n.attrib.get('href') or n.text or '')
            else:
                fields[name] = ''.join(n.itertext())
        title = plain(fields.get('title', ''))
        body = plain(fields.get('encoded') or fields.get('content') or fields.get('description') or fields.get('summary', ''))
        if not relevant(title + ' ' + body, keywords) or not links:
            continue
        url = canonical(links[0])
        rows.append(candidate(source, url, title, body, evidence,
                              {'published_at': fields.get('published') or fields.get('pubDate'),
                               'start_time': None, 'end_time': None, 'is_free': None}, kind='post'))
    next_urls = [n.attrib['href'] for n in root.iter() if leaf(n.tag) == 'link' and
                 n.attrib.get('rel') == 'next' and 'href' in n.attrib]
    # Blogger exposes OpenSearch counters but may omit rel=next on the Atom endpoint.
    counts = {leaf(n.tag): n.text for n in root if leaf(n.tag) in ('totalResults', 'startIndex', 'itemsPerPage')}
    if not next_urls and entries and all(str(counts.get(k, '')).isdigit() for k in ('totalResults', 'startIndex', 'itemsPerPage')):
        start, size, total = (int(counts[k]) for k in ('startIndex', 'itemsPerPage', 'totalResults'))
        if size > 0 and start + size <= total:
            parts = urlsplit(evidence['url'])
            query = parse_qs(parts.query)
            query['start-index'] = [str(start + size)]
            next_urls.append(urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), '')))
    return rows, next_urls


class FeedCrawler(Collector):
    def __init__(self, source_id, feed_url, keywords, max_pages=5, feed_mirrors=()):
        self.source_id, self.feed_url = source_id, feed_url
        self.keywords, self.max_pages = keywords, max_pages
        self.feed_mirrors = tuple(feed_mirrors)

    def collect(self, client):
        result = Result(self.source_id, 'official_feed')
        queue, seen = [self.feed_url], set()
        while queue and len(seen) < self.max_pages:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            try:
                text, ev = client.get(url)
                rows, more = parse_feed(text, self.source_id, ev, self.keywords)
                result.candidates.extend(rows)
                for target in more:
                    allowed = urlsplit(target).hostname == urlsplit(self.feed_url).hostname or any(
                        target.split('?')[0] == prefix for prefix in self.feed_mirrors)
                    if not allowed:
                        raise CollectionError('unapproved_feed_paging_host')
                    if target not in seen:
                        queue.append(target)
            except CollectionError as e:
                result.error(url, e)
        if queue:
            result.status = 'partial'
            result.notes.append('feed_page_limit_reached')
        result.notes.append('Feed coverage is limited to entries supplied by the publisher; publication dates are not event dates.')
        return result


class WebsiteCrawler(Collector):
    def __init__(self, spec, keywords, max_pages=30):
        self.spec, self.keywords, self.max_pages = spec, keywords, max_pages

    def collect(self, client):
        result = Result(self.spec['id'], 'official_website_discovery')
        known = {canonical(x['url']): x for x in self.spec.get('known_pages', [])}
        seeds = list(dict.fromkeys([canonical(x) for x in self.spec['urls']] + list(known)))
        allowed = {urlsplit(x).hostname for x in seeds} | set(self.spec.get('redirect_hosts', []))
        queue = [(110 if x in known else 100, x, 0, '') for x in seeds]
        for feed_url in self.spec.get('feed_urls', []):
            feed = FeedCrawler(self.spec['id'], feed_url, self.keywords, max_pages=3).collect(client)
            result.candidates.extend(feed.candidates)
            result.errors.extend(feed.errors)
            result.notes.extend(feed.notes)
            if feed.status != 'ok':
                result.status = 'partial'
            result.notes.append('feed_is_publisher_limited_not_full_archive')
        seen, scheduled = set(), set(seeds)
        while queue and len(seen) < self.max_pages:
            queue.sort(key=lambda x: x[0], reverse=True)
            _, url, depth, link_title = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            try:
                html, ev = client.get(url)
                if urlsplit(ev['final_url']).hostname not in allowed:
                    raise CollectionError('unapproved_redirect_host')
                doc = Document(html)
                title, body = doc.title(), doc.content()
                extra_links = []
                is_portal = urlsplit(ev['final_url']).hostname == 'event.culture.tw' and '/Detail.init.ctr' in url
                if is_portal:
                    title, body, extra_links = culture_portal_detail(doc, ev['final_url'])
                # Many government templates use h1 for the agency logo; retain the actual listing headline.
                if not is_portal and link_title and (relevant(link_title, self.keywords) or self.spec.get('group') == 'community_centers'):
                    title = link_title
                if re.search(r'Just a moment|Access Denied|驗證您是人類', title, re.I):
                    raise CollectionError('blocked_page')
                # A home/list page is discovery material, never an activity candidate.
                detail_path = bool(DETAIL.search(url))
                page = known.get(url, {})
                is_listing = bool(re.search(r'/(?:tag|category)/|/blog/?(?:\?|$)', url, re.I))
                is_detail = bool(page) or (not is_listing and url not in seeds and (detail_path or relevant(link_title, self.keywords) or relevant(title, self.keywords)))
                if page.get('title'):
                    title = page['title']
                alias_text = title if self.spec.get('alias_in_title') else title + ' ' + body
                alias_ok = not self.spec.get('require_alias') or any(a in alias_text for a in self.spec['aliases'])
                center_ok = True
                if self.spec.get('group') == 'community_centers':
                    center_ok = any(term in body + title for term in ('活動中心', '市民中心', '區民中心', '里民中心', '社區中心'))
                    if re.search(r'租借辦法|使用管理|收費標準|場地租借|場地借用|開放時間', title) and not relevant(title, self.keywords):
                        center_ok = False
                if is_detail and alias_ok and center_ok and relevant(title + ' ' + body, self.keywords):
                    result.candidates.append(candidate(self.spec['id'], ev['final_url'], title, body[:30000], ev,
                        {'start_time': None, 'end_time': None, 'is_free': None},
                        kind=page.get('kind', 'announcement'),
                        issues=['manual_event_verification_required'] + (['text_truncated'] if len(body) > 30000 else [])))
                if depth >= 3:
                    continue
                for target, label, node in list(doc.links(ev['final_url'])) + extra_links:
                    label = label or node.attrs.get('title', '') or node.attrs.get('aria-label', '')
                    # Some official pages still publish HTTP links to their own HTTPS host.
                    if target.startswith('http://') and urlsplit(target).hostname in allowed:
                        target = 'https://' + target[len('http://'):]
                    if target in scheduled or urlsplit(target).hostname not in allowed or BAD.search(label):
                        continue
                    if re.search(r'/pageutil/download|/uploaddowndoc|\.(?:pdf|jpg|png|zip|docx?|xlsx?|mp4|css|js)(?:[?&]|$)', target, re.I):
                        continue
                    match = relevant(label, self.keywords)
                    nav = NAV.search(label)
                    detail_link = bool(DETAIL.search(target))
                    if not (match or nav or detail_link or any(a in label for a in self.spec.get('priority_terms', []))):
                        continue
                    next_page = bool(re.search(r'下一頁|下頁|next', label, re.I))
                    priority = any(a in label for a in self.spec.get('priority_terms', []))
                    score = 80 if match else 60 if priority else 30 if next_page else 20 if detail_link else 10
                    queue.append((score-depth, target, depth if next_page else depth+1, label))
                    scheduled.add(target)
            except CollectionError as e:
                result.error(url, e)
        if queue:
            result.status = 'partial' if result.status != 'failed' or result.candidates else result.status
            result.notes.append('website_page_limit_reached')
        if result.errors and result.candidates:
            result.status = 'partial'
        result.notes.append('Bounded official-site discovery; not an exhaustive full-site search. PDF/image-only notices need manual review.')
        result.notes.append('pages_read=' + str(len(seen)))
        return result
