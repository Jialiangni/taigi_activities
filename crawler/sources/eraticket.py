"""Era's actual public keyword-search pages and visible performance tables."""
import re
from urllib.parse import urlencode, urlsplit
from ..collection import Collector, CollectionError, Result, Document, candidate, local_time, city_of, KEYWORDS, relevant


def parse_era(html, url, evidence):
    doc = Document(html)
    rows = []
    for tr in doc.root.all('tr'):
        cells = [n.text() for n in tr.children if getattr(n, 'tag', '') in ('td', 'th')]
        if not cells:
            continue
        match = re.search(r'(20\d{2})/(\d{1,2})/(\d{1,2})\s*[（(][^）)]+[）)]\s*(\d{1,2}):(\d{2})', cells[0])
        if not match:
            continue
        y, m, d, h, minute = map(int, match.groups())
        start = local_time('{:04}-{:02}-{:02}T{:02}:{:02}:00+08:00'.format(y, m, d, h, minute))
        venue = cells[1] if len(cells) > 1 else None
        fields = {'start_time': start, 'end_time': None, 'venue': venue, 'city': city_of(venue),
                  'price_info': cells[2] if len(cells) > 2 else None, 'is_free': None}
        rows.append(candidate('eraticket', url, doc.title(), doc.content(), evidence, fields, 'session',
                              key=url + ':' + str(start) + ':' + str(venue)))
    if not rows:
        rows.append(candidate('eraticket', url, doc.title(), doc.content(), evidence,
                              {'start_time': None, 'end_time': None, 'is_free': None},
                              issues=['manual_event_verification_required', 'session_table_not_found']))
    return rows


class EraTicketCrawler(Collector):
    SEARCH_URL = 'https://ticket.com.tw/application/UTK01/UTK0101_06.aspx'

    def __init__(self, keywords=None, max_pages=20, max_details=200):
        self.keywords, self.max_pages, self.max_details = keywords or KEYWORDS, max_pages, max_details

    def collect(self, client):
        result = Result('eraticket', 'official_html_search_and_session_table')
        found = set()
        # Keyword search covers titles only. Also read the public complete program index,
        # then filter program descriptions so concerts mentioning 台語 are not missed.
        try:
            html, ev = client.get(self.SEARCH_URL)
            for target, label, node in Document(html).links(ev['final_url']):
                if urlsplit(target).hostname in ('ticket.com.tw', 'www.ticket.com.tw') and 'UTK0201_' in target and 'PRODUCT_ID=' in target:
                    found.add(target)
        except CollectionError as e:
            result.error(self.SEARCH_URL, e)
        for kw in self.keywords:
            queue = [self.SEARCH_URL + '?' + urlencode({'TYPE': '1', 'S': kw})]
            seen = set()
            while queue and len(seen) < self.max_pages:
                url = queue.pop(0)
                if url in seen:
                    continue
                seen.add(url)
                try:
                    html, ev = client.get(url)
                    doc = Document(html)
                    if '共找到' not in doc.content():
                        raise CollectionError('search_page_schema_changed')
                    for target, label, node in doc.links(ev['final_url']):
                        if urlsplit(target).hostname not in ('ticket.com.tw', 'www.ticket.com.tw'):
                            continue
                        if 'UTK0201_' in target and 'PRODUCT_ID=' in target:
                            found.add(target)
                        elif re.search(r'下一頁|下頁|next', label, re.I) and target not in seen:
                            queue.append(target)
                    if '__doPostBack' in html and re.search(r'下一頁|下頁', doc.content()):
                        result.status = 'partial'
                        result.notes.append('postback_pagination_requires_review')
                except CollectionError as e:
                    result.error(url, e)
            if queue:
                result.status = 'partial'
                result.notes.append('search_page_limit')
        for url in sorted(found)[:self.max_details]:
            try:
                html, ev = client.get(url)
                if relevant(Document(html).content(), self.keywords):
                    result.candidates.extend(parse_era(html, ev['final_url'], ev))
            except CollectionError as e:
                result.error(url, e)
        result.notes.append('discovered_programs=' + str(len(found)))
        if len(found) > self.max_details:
            result.status = 'partial'
            result.notes.append('detail_limit_reached')
        if result.errors and result.candidates:
            result.status = 'partial'
        return result
