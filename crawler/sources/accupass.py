"""ACCUPASS public website search POST + event-page JSON-LD, pending review."""
import re
from datetime import datetime
from ..posters import poster_fields

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


def parse_schedule(html, event):
    """Read explicit MM月DD日 + HH:MM-HH:MM rows without treating a series span as sessions."""
    start, end = local_time(event.get('startDate')), local_time(event.get('endDate'))
    if not start or not end or start[:4] != end[:4]:
        return []
    year = start[:4]
    text = Document(html).content()
    pattern = re.compile(
        r'(?P<month>\d{1,2})月(?P<day>\d{1,2})日[（(][一二三四五六日天][）)]\s*'
        r'(?P<start>\d{1,2}:\d{2})\s*[-–－~～]\s*(?P<end>\d{1,2}:\d{2})')
    rows = []
    for matched in pattern.finditer(text):
        date = '{}-{:02d}-{:02d}'.format(year, int(matched['month']), int(matched['day']))
        session_start = local_time(date + 'T' + matched['start'] + ':00+08:00')
        session_end = local_time(date + 'T' + matched['end'] + ':00+08:00')
        if not session_start or not session_end or not (start[:10] <= date <= end[:10]):
            continue
        row = {'start_time': session_start, 'end_time': session_end}
        if row not in rows:
            rows.append(row)
    return rows


def table_schedule(html, event):
    """Certify only complete date/time tables sharing one event location.

    Discovery can retain other formats; those must not silently become verified
    sessions. Explicit row/column spans are expanded before interpreting cells.
    """
    start, end = local_time(event.get('startDate')), local_time(event.get('endDate'))
    if not start or not end:
        return [], 'period_missing'
    if not (0 <= int(end[:4]) - int(start[:4]) <= 2):
        return [], 'period_too_long_or_reversed'
    rows = []
    for table in Document(html).root.all('table'):
        pending, grid = {}, []
        for tr in table.all('tr'):
            cells = {col:text for col,(text,_) in pending.items()}
            pending = {col:(text,count-1) for col,(text,count) in pending.items() if count>1}
            col = 0
            for cell in (n for n in tr.children if hasattr(n,'tag') and n.tag in ('td','th')):
                while col in cells: col += 1
                try:
                    height, width = int(cell.attrs.get('rowspan',1)), int(cell.attrs.get('colspan',1))
                except ValueError:
                    return [], 'invalid_table_span'
                if not (1 <= height <= 100 and 1 <= width <= 10):
                    return [], 'invalid_table_span'
                for c in range(col,col+width):
                    cells[c] = cell.text().strip()
                    if height>1: pending[c]=(cells[c],height-1)
                col += width
            grid.append([cells.get(c,'') for c in range(max(cells,default=-1)+1)])
        if not grid: continue
        headers = grid[0]
        if not ('日期' in headers and '時間' in headers): continue
        if pending: return [], 'incomplete_schedule_row'
        if len(headers) != len(set(headers)): return [], 'ambiguous_schedule_headers'
        if any(h not in ('月份','日期','時間','場次') for h in headers):
            return [], 'per_session_fields_need_review'
        di, ti = headers.index('日期'), headers.index('時間')
        for values in grid[1:]:
            if values == headers: continue
            if len(values) != len(headers): return [], 'incomplete_schedule_row'
            d = re.fullmatch(r'(?:(20\d{2})[年/.\-])?(\d{1,2})[月/.\-](\d{1,2})日?\s*(?:[（(](?:星期|週)?([一二三四五六日天])[）)])?', values[di])
            t = re.fullmatch(r'(\d{1,2}):(\d{2})\s*[-–－~～]\s*(\d{1,2}):(\d{2})',values[ti])
            if not d or not t: return [], 'incomplete_schedule_row'
            possible = []
            for year in range(int(start[:4]),int(end[:4])+1):
                if d[1] and int(d[1]) != year: continue
                try:
                    day = datetime(year,int(d[2]),int(d[3]))
                    date = day.strftime('%Y-%m-%d')
                    a = local_time(date+'T'+t[1].zfill(2)+':'+t[2]+':00+08:00')
                    b = local_time(date+'T'+t[3].zfill(2)+':'+t[4]+':00+08:00')
                    if a and b and start <= a < b <= end:
                        if d[4] and '一二三四五六日'[day.weekday()] != d[4].replace('天','日'):
                            return [], 'weekday_mismatch'
                        possible.append({'start_time':a,'end_time':b,'date_text':values[di], 'time_text':values[ti]})
                except ValueError: pass
            if len(possible)!=1: return [], 'ambiguous_or_outside_period'
            if any(r['start_time']==possible[0]['start_time'] for r in rows):
                return [], 'duplicate_schedule_start'
            rows.extend(possible)
    if not rows: return [], 'explicit_date_time_table_missing'
    if min(r['start_time'] for r in rows)[:10]!=start[:10] or max(r['end_time'] for r in rows)[:10]!=end[:10]:
        return [], 'schedule_does_not_cover_period'
    return rows, ''


def activity_intro(event, doc=None):
    """Retain the publisher's event article, including late speaker/cast credits.

    Only the known event-content article is eligible; generic main/article text
    may contain recommendations. Schema description is the safe fallback.
    """
    if doc is not None:
        articles = [node for node in doc.root.all('article')
                    if any(c.startswith('EventContent_event-content__')
                           for c in node.attrs.get('class', '').split())]
        if len(articles) == 1 and articles[0].text().strip():
            return articles[0].text().strip()
    return plain(event.get('description') or '')


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
        sessions = parse_schedule(html, event)
        schedule_rows, schedule_issue = table_schedule(html, event)
        if schedule_rows:
            sessions = [{k: r[k] for k in ('start_time','end_time')} for r in schedule_rows]
        fields = {'start_time': local_time(event.get('startDate')), 'end_time': local_time(event.get('endDate')),
                  'venue': location.get('name'), 'address': address, 'city': city_of(address),
                  'organizer': organizer.get('name') if isinstance(organizer, dict) else None,
                  'price_info': prices or None, 'is_free': None, 'event_status': event.get('eventStatus'),
                  'sessions': sessions, 'schedule_rows':schedule_rows,
                  'schedule_issue':schedule_issue, 'official_summary':activity_intro(event, doc),
                  **poster_fields(html, url)}
        # Aggregate schema dates do not establish individual session dates or universal free admission.
        issues = ['manual_event_verification_required', 'check_series_sessions_and_ticket_terms']
        if sessions:
            issues.append('explicit_session_rows_extracted_but_not_verified')
        rows.append(candidate('accupass', url, event.get('name') or doc.title(), doc.content(), evidence,
                              fields, 'event_series' if sessions else 'event_period', issues,
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
