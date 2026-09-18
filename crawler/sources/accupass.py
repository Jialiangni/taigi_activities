"""ACCUPASS public website search POST + event-page JSON-LD, pending review."""
from ..collection import Collector, CollectionError, Result, Document, candidate, local_time, city_of, plain, KEYWORDS, relevant


def event_jsonld(doc):
    def walk(obj):
        if isinstance(obj, list):
            for x in obj:
                yield from walk(x)
        elif isinstance(obj, dict):
            types = obj.get('@type', [])
            if types == 'Event' or (isinstance(types, list) and 'Event' in types):
                yield obj
            for key in ('@graph', 'subEvent'):
                if key in obj:
                    yield from walk(obj[key])
    for obj in doc.jsonld():
        yield from walk(obj)


def parse_event(html, url, evidence):
    doc = Document(html)
    rows = []
    for i, event in enumerate(event_jsonld(doc)):
        location = event.get('location') or {}
        if not isinstance(location, dict):
            location = {}
        address = location.get('address', '')
        if isinstance(address, dict):
            address = ' '.join(str(address.get(k, '')) for k in ('addressRegion', 'addressLocality', 'streetAddress'))
        organizer = event.get('organizer') or {}
        offers = event.get('offers') or []
        offers = offers if isinstance(offers, list) else [offers]
        prices = [o.get('price') for o in offers if isinstance(o, dict) and o.get('price') is not None]
        fields = {'start_time': local_time(event.get('startDate')), 'end_time': local_time(event.get('endDate')),
                  'venue': location.get('name'), 'address': address, 'city': city_of(address),
                  'organizer': organizer.get('name') if isinstance(organizer, dict) else None,
                  'price_info': prices or None, 'is_free': None, 'event_status': event.get('eventStatus')}
        # Aggregate schema dates do not establish individual session dates or universal free admission.
        rows.append(candidate('accupass', url, event.get('name') or doc.title(), doc.content(), evidence,
                              fields, 'event_period', ['manual_event_verification_required', 'check_series_sessions_and_ticket_terms'],
                              url + ':' + str(i)))
    if not rows:
        raise CollectionError('event_jsonld_missing')
    return rows


class AccupassCrawler(Collector):
    LEGACY_SEARCH_API = 'https://api.accupass.com/v3/search'
    SEARCH_API = 'https://api.accupass.com/v3/search/SearchEvents'

    def __init__(self, keywords=None, max_pages=20, max_details=200):
        self.keywords = keywords or KEYWORDS
        self.max_pages, self.max_details = max_pages, max_details

    def collect(self, client):
        result = Result('accupass', 'public_search_post_and_jsonld')
        found, external = {}, set()
        for kw in self.keywords:
            previous = set()
            for page in range(self.max_pages):
                body = {'keyword': kw, 'currentIndex': page, 'categoryTypeList': [],
                        'simpleEventPlaceTypeList': [], 'cityLocationList': ['1', '2', '3'],
                        'sortBy': '4', 'timeType': '0'}
                try:
                    data, ev = client.json(self.SEARCH_API, body)
                    if not isinstance(data, dict) or not isinstance(data.get('items'), list) or not isinstance(data.get('total'), int):
                        raise CollectionError('search_schema_changed')
                    items = data['items']
                    ids = {x.get('eventIdNumber') for x in items}
                    if items and (None in ids or ids <= previous):
                        raise CollectionError('invalid_or_repeated_search_page')
                    previous |= ids
                    for item in items:
                        if not item.get('isExternalLink'):
                            found[item['eventIdNumber']] = item
                        else:
                            external.add(item['eventIdNumber'])
                    if len(previous) >= data['total']:
                        break
                    if not items:
                        raise CollectionError('search_truncated_before_total')
                except CollectionError as e:
                    result.error(self.SEARCH_API, e)
                    break
            else:
                result.status = 'partial'
                result.notes.append('search_page_limit:' + kw)
        unmatched_details = 0
        for event_id in list(found)[:self.max_details]:
            if not str(event_id).isdigit():
                result.error(self.SEARCH_API, CollectionError('invalid_event_id'))
                continue
            url = 'https://www.accupass.com/event/' + str(event_id)
            try:
                html, ev = client.get(url)
                rows = [r for r in parse_event(html, url, ev)
                        if relevant(r['title'] + ' ' + r['text'], self.keywords)]
                result.candidates.extend(rows)
                if not rows:
                    unmatched_details += 1
            except CollectionError as e:
                result.error(url, e)
        result.notes.append('discovered_programs=' + str(len(found)))
        result.notes.append('detail_pages_without_exact_keyword=' + str(unmatched_details))
        if external:
            result.status = 'partial'
            result.notes.append('external_programs_require_separate_source_review=' + str(len(external)))
        if len(found) > self.max_details:
            result.status = 'partial'
            result.notes.append('detail_limit_reached')
        if result.errors and result.candidates:
            result.status = 'partial'
        return result
