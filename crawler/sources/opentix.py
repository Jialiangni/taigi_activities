"""OPENTIX current public search API and explicit per-venue performance sessions."""
from ..collection import Collector, CollectionError, Result, candidate, local_time, city_of, plain, KEYWORDS, relevant


def parse_program(program, evidence):
    if not isinstance(program, dict) or not program.get('id') or not isinstance(program.get('eventVenues'), list):
        raise CollectionError('program_schema_changed')
    rows = []
    url = 'https://www.opentix.life/event/' + str(program['id'])
    organizers = []
    for group in program.get('programOrganizers', []):
        if group.get('type') == '主辦單位':
            organizers.extend(x.get('name') for x in group.get('info', []) if x.get('name'))
    for group in program['eventVenues']:
        venue = group.get('venue') or {}
        city = city_of(venue.get('city', ''))
        if venue.get('city') and not city:
            continue
        events = group.get('events')
        if not isinstance(events, list):
            raise CollectionError('session_schema_changed')
        for event in events:
            if not event.get('id'):
                raise CollectionError('session_id_missing')
            prices = sorted({s['price'] for sections in (event.get('groupSections') or {}).values()
                             for s in sections if isinstance(s.get('price'), (int, float))})
            fields = {'start_time': local_time(event.get('startDateTime')), 'end_time': local_time(event.get('endDateTime')),
                      'venue': venue.get('name'), 'city': city,
                      'address': ''.join(venue.get(k) or '' for k in ('city', 'area', 'address')),
                      'organizer': organizers, 'price_info': prices or None,
                      'is_free': True if prices and all(x == 0 for x in prices) else False if prices and all(x > 0 for x in prices) else None,
                      'platform_session_status': event.get('status'), 'session_name': event.get('description'),
                      'session_id': str(event['id']), 'change_notification': program.get('changeNotification')}
            text = plain(program.get('description')) + '\n' + plain(group.get('eventNoteContent'))
            issues = ['manual_event_verification_required', 'check_language_for_this_session', 'check_ticket_terms_and_changes']
            if not fields['start_time']:
                issues.append('missing_start_time')
            rows.append(candidate('opentix', url, program.get('name', ''), text, evidence, fields,
                                  'session', issues, str(program['id']) + ':' + str(event['id'])))
    return rows


class OpentixCrawler(Collector):
    LEGACY_SEARCH_API = 'https://www.opentix.life/oapi/v1/search/program'
    SEARCH_API = 'https://search.opentix.life/search'
    DETAIL_API = 'https://csm.api.opentix.life/programs/'

    def __init__(self, keywords=None, max_pages=20, max_details=200):
        self.keywords, self.max_pages, self.max_details = keywords or KEYWORDS, max_pages, max_details

    def collect(self, client):
        result = Result('opentix', 'public_search_post_and_session_api')
        found = {}
        for kw in self.keywords:
            offset, seen = None, set()
            for page in range(self.max_pages):
                # Values verified against /search/criteria/cities (the suffix 市 is invalid here).
                body = {'queryString': kw, 'language': 'zh-CHT', 'cityFilter': ['臺北', '新北', '桃園']}
                if offset is not None:
                    body['offset'] = offset
                try:
                    data, ev = client.json(self.SEARCH_API, body)
                    data = data.get('result') if isinstance(data, dict) else None
                    if not isinstance(data, dict) or not isinstance(data.get('found'), list):
                        raise CollectionError('search_schema_changed')
                    for hit in data['found']:
                        item = hit.get('source', {})
                        if not str(item.get('id', '')).isdigit():
                            raise CollectionError('invalid_program_id')
                        if relevant(item.get('title', '') + ' ' + plain(item.get('description', '')), self.keywords):
                            found[str(item['id'])] = item
                    next_offset = data.get('nextOffset')
                    if next_offset is None:
                        break
                    if next_offset in seen or not data['found']:
                        raise CollectionError('repeated_search_cursor')
                    seen.add(next_offset)
                    offset = next_offset
                except CollectionError as e:
                    result.error(self.SEARCH_API, e)
                    break
            else:
                result.status = 'partial'
                result.notes.append('search_page_limit:' + kw)
        for program_id in list(found)[:self.max_details]:
            url = self.DETAIL_API + program_id
            try:
                data, ev = client.json(url)
                result.candidates.extend(parse_program(data.get('result'), ev))
            except CollectionError as e:
                result.error(url, e)
        result.notes.append('discovered_programs=' + str(len(found)))
        if len(found) > self.max_details:
            result.status = 'partial'
            result.notes.append('detail_limit_reached')
        if result.errors and result.candidates:
            result.status = 'partial'
        return result
