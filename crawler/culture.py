"""Ministry of Culture documented category feeds; preserve showInfo sessions."""
from .collection import Collector, CollectionError, Result, candidate, relevant, city_of, local_time

CATEGORIES = [1, 2, 3, 4, 5, 6, 7, 8, 11, 13, 14, 15, 17, 19]
API = 'https://cloud.culture.tw/frontsite/trans/SearchShowAction.do?method=doFindTypeJ&category='


def parse_culture(data, evidence, keywords, registry):
    if not isinstance(data, list) or any(not isinstance(x, dict) for x in data):
        raise CollectionError('unexpected_culture_schema')
    rows = []
    for item in data:
        title, body = item.get('title', ''), item.get('descriptionFilterHtml', '')
        if not relevant(title + ' ' + body, keywords):
            continue
        if not item.get('UID') or not isinstance(item.get('showInfo'), list):
            raise CollectionError('culture_session_schema_changed')
        units = ' '.join(item.get('masterUnit', []) + item.get('subUnit', [])) + ' ' + item.get('showUnit', '')
        for session in item['showInfo']:
            address, venue = session.get('location', ''), session.get('locationName', '')
            city = city_of(address)
            if not city:
                continue
            start, end = local_time(session.get('time')), local_time(session.get('endTime'))
            issues = ['manual_event_verification_required']
            if not start:
                issues.append('missing_start_time')
            if start and end and start[:10] != end[:10]:
                issues.append('multi_day_period_requires_session_review')
            price = session.get('price', '')
            # onSales=N means no ticket sales, not necessarily free admission.
            free = True if price.strip() in ('免費', '免費入場', '0') else None
            fields = {'start_time': start, 'end_time': end, 'city': city, 'venue': venue,
                      'address': address, 'organizer': item.get('masterUnit', []),
                      'price_info': price or None, 'is_free': free,
                      'on_sales': session.get('onSales'), 'published_at': None}
            url = item.get('sourceWebPromote') or item.get('webSales') or evidence['url']
            row = candidate('culture_open_data', url, title, body, evidence, fields, 'session', issues,
                            item['UID'] + ':' + str(session.get('time')) + ':' + venue)
            row['matched_sources'] = [s['id'] for s in registry if any(a in units+' '+venue for a in s.get('aliases', []))]
            rows.append(row)
    return rows


class CultureCrawler(Collector):
    def __init__(self, keywords, registry, categories=None):
        self.keywords, self.registry = keywords, registry
        self.categories = categories or CATEGORIES

    def collect(self, client):
        result = Result('culture_open_data', 'documented_open_data')
        for category in self.categories:
            url = API + str(category)
            try:
                data, ev = client.json(url)
                result.candidates.extend(parse_culture(data, ev, self.keywords, self.registry))
            except CollectionError as e:
                result.error(url, e)
        if result.errors and result.candidates:
            result.status = 'partial'
        result.notes.append('Publisher-supplied coverage only; onSales=N does not establish free admission.')
        return result
