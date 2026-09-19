"""District library listings: scoped links and the publishers' real pagination."""
import re
from urllib.parse import parse_qs, urlsplit
from .collection import Collector, CollectionError, Document, Result, candidate, relevant
from .posters import poster_fields


def listing_page(html, url, spec):
    doc = Document(html)
    kind = spec['listing_type']
    links, more = [], []
    if kind == 'taoyuan':
        items = [n for n in doc.root.all('div') if 'list-item' in n.attrs.get('class', '').split()]
        if not items and 'not-found' not in html:
            raise CollectionError('library_listing_schema_changed')
        for item in items:
            if item.attrs.get('data-area') not in spec['area_codes']:
                raise CollectionError('library_area_filter_ignored')
            for a in item.all('a'):
                href = a.attrs.get('href', '')
                if re.fullmatch(r'/zh-tw/Activity/Content/\d+', href, re.I):
                    links.append(('https://www.typl.gov.tw' + href, item.attrs.get('data-title') or a.text()))
        return links, more, doc
    if kind == 'taipei':
        scope = parse_qs(urlsplit(url).query).get('n')
        for target, label, node in doc.links(url):
            parts = urlsplit(target)
            query = parse_qs(parts.query)
            if parts.hostname not in {'reading.tpml.gov.taipei', 'tpml.gov.taipei'} or query.get('n') != scope:
                continue
            if parts.path.lower().endswith('/news_content.aspx'):
                links.append((target, label or node.attrs.get('title', '')))
            elif parts.path.lower().endswith('/news.aspx') and query.get('page', [''])[0].isdigit():
                if int(query['page'][0]) > int(parse_qs(urlsplit(url).query).get('page', ['1'])[0]):
                    more.append((int(query['page'][0]), target))
        if not list(doc.root.all('table')) and not links and not re.search(r'無資料|查無|沒有資料|共\s*0\s*筆', doc.content()):
            raise CollectionError('library_listing_schema_changed')
    else:
        if not any(n.attrs.get('id') == 'form1' for n in doc.root.all('form')):
            raise CollectionError('library_listing_schema_changed')
        areas = [n for n in doc.root.all('select') if n.attrs.get('name') == 'area']
        selected = [o.attrs.get('value') for n in areas for o in n.all('option') if 'selected' in o.attrs]
        if selected != [spec['area_code']]:
            raise CollectionError('library_area_filter_ignored')
        for target, label, node in doc.links(url):
            if urlsplit(target).hostname == 'www.library.ntpc.gov.tw' and '/singlehtml/ActvInfo' in target:
                links.append((target, label or node.attrs.get('title', '')))
        for a in doc.root.all('a'):
            match = re.fullmatch(r'(?:javascript:)?pagechange\(\s*(\d+)\s*\);?', a.attrs.get('onclick', '') or a.attrs.get('href', ''))
            if match:
                more.append((int(match.group(1)), url))
    return list(dict.fromkeys(links)), sorted(more), doc


class LibraryListingCrawler(Collector):
    def __init__(self, spec, keywords, max_pages=30):
        self.spec, self.keywords, self.max_pages = spec, keywords, max_pages

    def collect(self, client):
        result = Result(self.spec['id'], 'district_library_listing')
        queue = [(u, 1, None) for u in self.spec['urls']]
        details, seen, fingerprints = {}, set(), set()
        reads = 0
        kind = self.spec['listing_type']
        # Reserve half the budget for details; each initial branch list gets a turn.
        listing_limit = max(len(queue), self.max_pages // 2)
        while queue and reads < min(self.max_pages, listing_limit):
            url, page, form = queue.pop(0)
            key = (url, page)
            if key in seen:
                continue
            seen.add(key)
            reads += 1
            try:
                kwargs = {'ajax': True} if kind == 'taoyuan' else {}
                if form is not None:
                    kwargs['form'] = form
                html, ev = client.get(url, **kwargs)
                if urlsplit(ev['final_url']).hostname != urlsplit(url).hostname:
                    raise CollectionError('unapproved_redirect_host')
                links, more, doc = listing_page(html, ev['final_url'], self.spec)
                scope = tuple(parse_qs(urlsplit(url).query).get('n', [self.spec['id']]))
                fingerprint = (scope, tuple(u for u, title in links))
                if links and fingerprint in fingerprints:
                    raise CollectionError('library_repeated_listing_page')
                fingerprints.add(fingerprint)
                details.update(links)
                if kind == 'taoyuan':
                    if links:
                        queue.append((url, page + 1, {'CurrentPage': page + 1}))
                elif kind == 'new_taipei':
                    next_pages = [n for n, _ in more if n > page]
                    if next_pages:
                        allowed = {'csrfToken', 'page', 'isPage', 'pageSize', 'orderField', 'orderType', 'svcId'}
                        form = {n.attrs['name']: n.attrs.get('value', '') for n in doc.root.all('input') if n.attrs.get('name') in allowed}
                        form.update(area=self.spec['area_code'], branch='', page=str(min(next_pages)), isPage='true')
                        queue.append((url, min(next_pages), form))
                elif more:
                    queue.append((more[0][1], more[0][0], None))
            except CollectionError as e:
                result.error(url, e)
        if queue:
            result.notes.append('library_listing_page_limit_reached')
            result.status = 'partial'
        ordered = sorted(details.items(), key=lambda x: not relevant(x[1], self.keywords))
        for i, (url, title) in enumerate(ordered):
            if reads >= self.max_pages:
                result.notes.append('library_detail_page_limit_reached')
                result.status = 'partial'
                break
            reads += 1
            try:
                html, ev = client.get(url)
                if urlsplit(ev['final_url']).hostname != urlsplit(url).hostname:
                    raise CollectionError('unapproved_redirect_host')
                doc = Document(html)
                body = doc.content()
                if re.search(r'Just a moment|Access Denied|驗證您是人類', doc.title(), re.I):
                    raise CollectionError('blocked_page')
                if relevant(title + ' ' + body, self.keywords):
                    row = candidate(self.spec['id'], ev['final_url'], title or doc.title(), body[:30000], ev,
                                    {'start_time': None, 'end_time': None, 'is_free': None,
                                     **poster_fields(html, ev['final_url'])},
                                    issues=['manual_event_verification_required'] + (['text_truncated'] if len(body) > 30000 else []))
                    row['collection_scope'] = {'city': self.spec['city'], 'district': self.spec['district']}
                    result.candidates.append(row)
            except CollectionError as e:
                result.error(url, e)
        result.notes.extend(['pages_read=' + str(reads), 'discovered_details=' + str(len(details)),
                             'District listing scope is not a verified event location; publisher-only bounded coverage.'])
        if result.errors:
            result.status = 'partial' if result.candidates else 'failed'
        return result
