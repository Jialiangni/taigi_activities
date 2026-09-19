"""Trusted Taigi activity directory with explicit North-Taiwan city filters.

The directory owner curates Taigi activities.  Language is therefore a source
property; dates, times, locations and duplicate sessions remain fail-closed.
"""
import html as html_module
import re
from datetime import date, datetime, timedelta
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

from ..collection import (Collector, CollectionError, Document, Result, TAIPEI,
                          candidate, canonical, city_of)


LIST_URL = 'https://www.gameislearning.url.tw/taigi.php'
DETAIL_RE = re.compile(r'https://www\.gameislearning\.url\.tw/taigi-info\.php\?news=([a-z0-9]+)')
CITY_FILTERS = {'b': '臺北市', 'c': '新北市', 'd': '桃園市'}
URL_RE = re.compile(r'https?://[^\s<>"\']+')


def clean_url(value):
    value = html_module.unescape(value or '').replace('\u200b', '').strip()
    value = value.rstrip('。．，、；;！!？?）)]}〉》」』')
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError
        return urlunsplit((parsed.scheme, parsed.netloc, quote(parsed.path, safe='/%:@='),
                           quote(parsed.query, safe='=&%/:@,+;?'), ''))
    except (ValueError, UnicodeError):
        return None


def text_lines(fragment):
    value = re.sub(r'(?i)<br\s*/?>|</(?:p|div|li|tr|h[1-6])>', '\n', fragment or '')
    value = re.sub(r'<[^>]+>', '', value)
    return '\n'.join(re.sub(r'[ \t\r\f\v]+', ' ', html_module.unescape(line)).strip()
                     for line in value.split('\n') if line.strip())


def _first(pattern, value, flags=re.I | re.S):
    matched = re.search(pattern, value or '', flags)
    return matched.group(1).strip() if matched else ''


def poster_url(page, url):
    """Use the detail page's event image, never navigation art or guessed thumbnails."""
    for node in Document(page).root.all('img'):
        if node.attrs.get('id') != 'myPic':
            continue
        try:
            image = clean_url(urljoin(url, node.attrs.get('src') or ''))
        except ValueError:
            continue
        if not image:
            continue
        parsed = urlsplit(image)
        if (parsed.scheme == 'https'
                and parsed.netloc in ('files.gameislearning.url.tw', 'www.gameislearning.url.tw')
                and re.fullmatch(r'/taigi/info-pic/[^/]+\.(?:jpe?g|png|webp|gif)', parsed.path, re.I)):
            return image
    return ''


def parse_detail(page, url, evidence, card=None, now=None):
    """Parse only explicit fields; the live reviewer repeats this parser."""
    now = now or datetime.now(TAIPEI)
    card = card or {}
    title = text_lines(_first(r'<h1[^>]*>(.*?)</h1>', page))
    body_html = _first(r'<h1[^>]*>.*?</h1>\s*<p[^>]*>(.*?)</p>', page)
    body = text_lines(body_html)
    address = text_lines(_first(r'活動地址.*?<a[^>]+href=["\'][^"\']+["\'][^>]*>(.*?)</a>', page))
    source_href = _first(r'<td[^>]+id=["\']titleTD["\'][^>]*>.*?<a[^>]+href=["\']([^"\']+)', page)
    links = []
    for raw in [source_href] + URL_RE.findall(body):
        link = clean_url(urljoin(url, raw))
        if link and link not in links and urlsplit(link).scheme == 'https':
            links.append(link)
    registration = choose_registration_url(links)
    city = city_of(address + ' ' + body) or card.get('city')
    district = card.get('district', '')
    if not district:
        matched = re.search(r'(?:臺北市|台北市|新北市|桃園市)([^\s]{1,4}區)', address)
        district = matched.group(1) if matched else ''
    venue = venue_of(body, address)
    organizer = organizer_of(body)
    sessions = sessions_of(body, card.get('published_at'), now)
    return {'title': title, 'text': body, 'address': address, 'venue': venue,
            'organizer': organizer, 'city': city, 'district': district,
            'category': category_of(card.get('type', ''), title + ' ' + body),
            'is_free': card.get('is_free'), 'registration_url': registration,
            'content_links': links, 'sessions': sessions, 'evidence': evidence,
            'source_url': url, 'cover_image': poster_url(page, url)}


def choose_registration_url(links):
    if not links:
        return ''
    preferred = ('forms.gle', 'docs.google.com', 'beclass.com', 'accupass.com',
                 'opentix.life', 'kktix.cc', 'linktr.ee', 'linktree.com',
                 'ppt.cc', 'reurl.cc', 'lin.ee')
    for host in preferred:
        found = next((u for u in links if (urlsplit(u).hostname or '').lower().endswith(host)), None)
        if found:
            return found
    return ''


def venue_of(body, address):
    matched = re.search(r'(?:地點|場地|所在)\s*[｜|：:]\s*([^\n]{2,100})', body)
    if matched:
        return matched.group(1).strip(' 。')
    for line in body.splitlines():
        if re.match(r'^[🏡📍]', line) and not re.search(r'時間|日期|報名', line):
            value = re.sub(r'^[🏡📍\s]+', '', line).strip()
            if 2 <= len(value) <= 100:
                return value
    # The directory's map label commonly appends the venue after a street number.
    matched = re.search(r'(?:號|樓)\s+(.{2,80})$', address)
    return matched.group(1).strip() if matched else address


def organizer_of(body):
    for pattern in (r'(?:主辦單位|主辦)\s*[｜|：:]\s*([^\n]{2,80})',
                    r'([^\n]{2,80}?(?:協會|基金會|圖書館|博物館|劇團|工作室|中心))\s*(?:邀請您|主辦)'):
        matched = re.search(pattern, body)
        if matched:
            return matched.group(1).strip(' ❤️📌')
    return '主辦單位請見活動公告'


def category_of(label, text):
    if re.search(r'繪本', text): return '台語繪本'
    if re.search(r'故事|講古', text): return '台語故事'
    if re.search(r'導覽|走讀', text): return '台語導覽'
    if re.search(r'戲劇|歌仔戲|布袋戲|掌中戲|舞臺劇|舞台劇', text): return '台語舞台劇'
    if label == '展演' or re.search(r'演出|音樂|表演', text): return '台語表演'
    if re.search(r'體驗|工作坊|課程|共學', text): return '台語體驗'
    return '台語活動'


def _year(value, fallback):
    if not value:
        return fallback
    number = int(value)
    return number + 1911 if number < 1900 else number


def _clock(ampm, hour, minute):
    h = int(hour)
    marker = (ampm or '').upper()
    if marker in ('PM', '下午', '下晡', '暗時') and h < 12: h += 12
    if marker in ('AM', '上午', '早起') and h == 12: h = 0
    return h, int(minute)


def _range_clocks(match):
    sh, sm = _clock(match.group(1), match.group(2), match.group(3))
    end_marker = match.group(4)
    if not end_marker and int(match.group(5)) != 12:
        end_marker = match.group(1)
    eh, em = _clock(end_marker, match.group(5), match.group(6))
    return sh, sm, eh, em


DATE_RE = re.compile(r'(?:(20\d{2}|1\d{2})\s*[/.年]\s*)?(\d{1,2})\s*(?:[/.月])\s*(\d{1,2})\s*日?')
TIME_RE = re.compile(r'(?:(AM|PM|上午|下午|下晡|暗時|早起)\s*)?(\d{1,2})\s*[:：]\s*(\d{2})\s*(?:[~～－—–-]|至|到)\s*(?:(AM|PM|上午|下午|下晡|暗時|早起)\s*)?(\d{1,2})\s*[:：]\s*(\d{2})', re.I)
START_TIME_RE = re.compile(r'(?:(AM|PM|上午|下午|下晡|暗時|早起)\s*)?(\d{1,2})\s*[:：]\s*(\d{2})', re.I)


def date_list_clocks(body):
    """Bind a shared time only to its contiguous date list, not later deadlines."""
    lines = body.splitlines(keepends=True)
    clocks, offset = {}, 0
    declared = list(TIME_RE.finditer(body)) if '時間都是' in body else []
    common = declared[0] if declared and len({_range_clocks(c) for c in declared}) == 1 else None
    for index, line in enumerate(lines):
        dates = list(DATE_RE.finditer(line))
        if (common and len(dates) == 1 and not line[:dates[0].start()].strip(' \t＊*・•')
                and not re.search(r'報名|截止|優惠|開賣', line)):
            clocks[offset + dates[0].start()] = common
        if len(dates) >= 2 and re.search(r'[、，,]', line):
            between = line[dates[0].start():dates[-1].end()]
            between = DATE_RE.sub('', between)
            between = re.sub(r'[（(](?:星期|禮拜|週)?[一二三四五六日天][）)]', '', between)
            if not re.sub(r'[\s、，,]', '', between):
                clock = TIME_RE.search(line, dates[-1].end())
                if not clock and index + 1 < len(lines):
                    following = re.sub(r'^\s*(?:時間|上課時間)\s*[：:]\s*', '', lines[index+1])
                    clock = TIME_RE.match(following.strip())
                if not clock and index and re.search(r'每月一次|時間都是', lines[index-1]):
                    clock = TIME_RE.search(lines[index-1])
                if clock:
                    clocks.update({offset + d.start(): clock for d in dates})
        offset += len(line)
    return clocks


def sessions_of(body, published_at=None, now=None):
    now = now or datetime.now(TAIPEI)
    fallback_year = now.year
    published_date = None
    if published_at:
        try:
            published_date = date.fromisoformat(published_at[:10])
            fallback_year = published_date.year
        except ValueError:
            pass

    recurring = re.search(
        r'(?:(20\d{2}|1\d{2})\s*[/.年]\s*)?(\d{1,2})\s*[/.月]\s*(\d{1,2})\s*日?\s*[~～－—–-]\s*'
        r'(?:(20\d{2}|1\d{2})\s*[/.年]\s*)?(\d{1,2})\s*[/.月]\s*(\d{1,2})\s*日?[^\n]{0,50}'
        r'(?:每週|每星期|逐週)[^\n]{0,20}', body)
    if recurring:
        y1 = _year(recurring.group(1), fallback_year)
        y2 = _year(recurring.group(4), y1)
        try:
            start_day = date(y1, int(recurring.group(2)), int(recurring.group(3)))
            end_day = date(y2, int(recurring.group(5)), int(recurring.group(6)))
        except ValueError:
            return []
        nearby = body[recurring.start():recurring.end()+100]
        clock = TIME_RE.search(nearby)
        if not clock:
            return []
        sh, sm, eh, em = _range_clocks(clock)
        result, day = [], start_day
        while day <= end_day and len(result) < 80:
            start = datetime(day.year, day.month, day.day, sh, sm, tzinfo=TAIPEI)
            end = datetime(day.year, day.month, day.day, eh, em, tzinfo=TAIPEI)
            if end > start:
                result.append({'start_time': start.isoformat(), 'end_time': end.isoformat()})
            day += timedelta(days=7)
        return result

    matches = list(DATE_RE.finditer(body))
    shared_clocks = date_list_clocks(body)
    result = []
    for index, matched in enumerate(matches):
        boundary = matches[index+1].start() if index+1 < len(matches) else min(len(body), matched.end()+180)
        clock = TIME_RE.search(body, matched.end(), boundary)
        clock = clock or shared_clocks.get(matched.start())
        year = _year(matched.group(1), fallback_year)
        try:
            day = date(year, int(matched.group(2)), int(matched.group(3)))
            if not matched.group(1) and published_date and day < published_date - timedelta(days=45):
                day = date(year + 1, day.month, day.day)
            if clock:
                sh, sm, eh, em = _range_clocks(clock)
            else:
                start_clock = START_TIME_RE.search(body, matched.end(), boundary)
                if not start_clock:
                    continue
                nearby = body[max(0, matched.start()-20):min(len(body), start_clock.end()+35)]
                if re.search(r'報名|截止|售票|開賣', nearby):
                    continue
                sh, sm = _clock(start_clock.group(1), start_clock.group(2), start_clock.group(3))
                eh = em = None
            start = datetime(day.year, day.month, day.day, sh, sm, tzinfo=TAIPEI)
            end = datetime(day.year, day.month, day.day, eh, em, tzinfo=TAIPEI) if eh is not None else None
        except ValueError:
            continue
        if (end is None or end > start) and not any(x['start_time'] == start.isoformat() for x in result):
            result.append({'start_time': start.isoformat(), 'end_time': end.isoformat() if end else None})
    return result


def listing_cards(page, base, city):
    rows = []
    for node in Document(page).root.all('div'):
        if not node.has_class('theme'):
            continue
        link = next(((u, t) for u, t, _ in Document(node_html(node)).links(base)
                     if DETAIL_RE.fullmatch(u)), None)
        if not link:
            continue
        title = next((h.text().strip() for h in node.all('h3') if h.text().strip()), link[1])
        text = re.sub(r'\s+', ' ', node.text()).strip()
        published = _first(r'(20\d{2}-\d{2}-\d{2})', text, 0)
        place = re.search(r'(台北市|臺北市|新北市|桃園市)\s*([^\s]{1,4}區)?', text)
        rows.append({'url': link[0], 'title': title, 'published_at': published,
                     'city': city_of(place.group(0)) if place else city,
                     'district': place.group(2) if place and place.group(2) else '',
                     'type': next((x for x in ('展演','親子','課程','講座','導覽','其他') if x in text), ''),
                     'is_free': True if '免費' in text else False if '付費' in text or '收費' in text else None})
    return rows


def node_html(node):
    # Listing parsing only needs links and headings; reconstruct the relevant tree.
    def render(value):
        if isinstance(value, str): return html_module.escape(value)
        attrs = ''.join(' {}="{}"'.format(k, html_module.escape(v or '', quote=True)) for k, v in value.attrs.items())
        return '<{0}{1}>{2}</{0}>'.format(value.tag, attrs, ''.join(render(c) for c in value.children))
    return render(node)


class GameIsLearningCrawler(Collector):
    def __init__(self, max_pages=20, max_details=200, now=None):
        self.max_pages, self.max_details = max_pages, max_details
        self.now = now or datetime.now(TAIPEI)

    def collect(self, client):
        result = Result('gameislearning', 'trusted_taigi_directory')
        cards = {}
        for code, city in CITY_FILTERS.items():
            for page_number in range(1, self.max_pages + 1):
                try:
                    if page_number == 1:
                        page, _ = client.get(LIST_URL, form={'pubORPri':'N', 'sel_city':code,
                            'sel_area':'', 'isSrch':'', 'issPay':'', 'overdue':'N'})
                    else:
                        page, _ = client.get(LIST_URL + '?gtpg=' + str(page_number))
                except CollectionError as error:
                    result.error(LIST_URL, error)
                    break
                found = listing_cards(page, LIST_URL, city)
                new_count = 0
                for row in found:
                    if row['url'] not in cards:
                        cards[row['url']] = row
                        new_count += 1
                next_url = LIST_URL + '?gtpg=' + str(page_number + 1)
                if not found or next_url not in page or new_count == 0:
                    break
            else:
                result.status = 'partial'
                result.notes.append('listing_page_limit_reached:' + code)
        for index, (url, card) in enumerate(cards.items()):
            if index >= self.max_details:
                result.status = 'partial'
                result.notes.append('detail_limit_reached')
                break
            try:
                page, evidence = client.get(url)
                parsed = parse_detail(page, url, evidence, card, self.now)
                if not parsed['title'] or not parsed['city']:
                    raise CollectionError('invalid_activity_detail')
                if parsed['city'] not in CITY_FILTERS.values():
                    continue
                if not parsed['sessions']:
                    result.candidates.append(candidate('gameislearning', url, parsed['title'], parsed['text'],
                        evidence, fields=parsed, issues=['explicit_session_time_missing'], key=url))
                    continue
                for session in parsed['sessions']:
                    fields = dict(parsed, **session)
                    fields.pop('sessions', None)
                    row = candidate('gameislearning', url, parsed['title'], parsed['text'], evidence,
                                    fields=fields, kind='session', issues=['trusted_taigi_directory'],
                                    key=url + ':' + session['start_time'])
                    row['trusted_language_source'] = True
                    result.candidates.append(row)
            except CollectionError as error:
                result.error(url, error)
        result.coverage_complete = result.status == 'ok'
        return result
