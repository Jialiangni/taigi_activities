"""Taoyuan Museum's publicly embedded Next.js datasets (no challenge bypass)."""
import json
from ..collection import Collector, CollectionError, Result, Document, candidate, relevant, plain, KEYWORDS


def parse_home(html, evidence, keywords):
    doc = Document(html)
    data = None
    for node in doc.root.all('script'):
        if node.attrs.get('id') == '__NEXT_DATA__':
            try:
                data = json.loads(''.join(x for x in node.children if isinstance(x, str)))['props']['pageProps']
            except (ValueError, KeyError, TypeError):
                raise CollectionError('tmofa_state_schema_changed') from None
            break
    if not isinstance(data, dict) or not isinstance(data.get('news'), list) or not isinstance(data.get('info'), list):
        raise CollectionError('tmofa_state_missing')
    rows = []
    for kind in ('news', 'info'):
        for item in data[kind]:
            if item.get('lang') != 'ch' or item.get('state', 1) != 1:
                continue
            title, body = item.get('title', ''), plain(item.get('content', ''))
            if not relevant(title + ' ' + body, keywords):
                continue
            url = ('https://tmofa.tycg.gov.tw/ch/news/latest-news/' + str(item['id'])) if kind == 'news' else item.get('img_link')
            if not url or not url.startswith('https://'):
                continue
            rows.append(candidate('tmofa', url, title, body, evidence,
                                  {'start_time': None, 'end_time': None, 'is_free': None,
                                   'published_at': item.get('publish_up'), 'museum_id': item.get('museum_id')},
                                  'announcement', key=kind + ':' + str(item['id'])))
    return rows, {k: len(data[k]) for k in ('news', 'info')}


class TmofaCrawler(Collector):
    def __init__(self, keywords=None):
        self.keywords = keywords or KEYWORDS

    def collect(self, client):
        result = Result('tmofa', 'official_home_embedded_datasets')
        url = 'https://tmofa.tycg.gov.tw/ch'
        try:
            html, ev = client.get(url)
            result.candidates, counts = parse_home(html, ev, self.keywords)
            result.notes.append('Publisher embedded dataset rows: ' + json.dumps(counts))
            result.notes.append('Detail pages may require ordinary browser verification; embedded datasets supply announcement text, not certified sessions.')
        except CollectionError as e:
            result.error(url, e)
        return result
