"""Bounded, read-only discovery of public registration session evidence."""
import re
import math
import unicodedata
from datetime import datetime, timedelta
from urllib.parse import urlsplit, unquote

from .collection import CollectionError, Document, TAIPEI

LINK_HOSTS = {'forms.gle', 'docs.google.com', 'ppt.cc', 'reurl.cc',
              'linktr.ee', 'www.linktr.ee', 'linktree.com', 'www.linktree.com',
              'beclass.com', 'www.beclass.com', 'www.accupass.com'}
LINK_PAGES = {'linktr.ee', 'www.linktr.ee', 'linktree.com', 'www.linktree.com', 'ppt.cc', 'reurl.cc'}


def supported_url(url):
    p = urlsplit(url or '')
    if p.scheme != 'https' or p.netloc not in LINK_HOSTS or p.username or p.password:
        return False
    if p.hostname == 'docs.google.com':
        return bool(re.fullmatch(r'/forms/d/(?:e/)?[\w-]+/viewform', p.path))
    if p.hostname in ('www.beclass.com', 'beclass.com'):
        return bool(re.fullmatch(r'/rid=[a-z0-9]+', unquote(p.path)))
    if p.hostname == 'www.accupass.com':
        return bool(re.fullmatch(r'/event/\d+', p.path))
    return True


def norm(text):
    return re.sub(r'[^\w]', '', unicodedata.normalize('NFKC', text).replace('台','臺')).lower()


def same_identity(parsed, text):
    """Require the source venue and a distinctive title fragment on the linked page."""
    body = norm(text)
    if not parsed.get('venue') or norm(parsed['venue']) not in body:
        return False
    title = re.sub(r'20\d{2}年?|\d+', '', norm(parsed['title']))
    for generic in ('臺語活動', '報名表', '活動報名', '強勢回歸'):
        title = title.replace(norm(generic), ' ')
    return any(len(token) >= 4 and (token in body or any(token[i:i+max(6,math.ceil(len(token)*0.65))] in body
                  for i in range(max(0,len(token)-max(6,math.ceil(len(token)*0.65))+1))))
               for token in title.split())


def text_sessions(parsed, text):
    """Dates must be explicit in the linked text; never use the crawl year."""
    from .sources.gameislearning import DATE_RE, TIME_RE, START_TIME_RE, _year, _range_clocks, _clock
    # Remove deadlines before binding dates to times. Keep paragraph boundaries.
    lines = [line.strip() for line in text.splitlines() if line.strip()
             and not re.search(r'報名截止|截止報名|報名期間|報名日期|報名時間|報名開始|開放報名|優惠|開賣|售票時間|填表時間', line)]
    text = '\n'.join(lines)
    dates = list(DATE_RE.finditer(text))
    full = {(_year(d[1],0),int(d[2]),int(d[3])) for d in dates if d[1]}
    if not full:
        explicit_years = set(re.findall(r'(?<!\d)(20\d{2})(?:年|(?=\s*(?:\n|$)))', text))
        if len(explicit_years) == 1 and dates:
            full = {(int(next(iter(explicit_years))), int(d[2]), int(d[3])) for d in dates}
        else:
            raise CollectionError('registration_date_not_explicit')
    years = {d[0] for d in full}
    source_dates = list(DATE_RE.finditer(parsed['text']))
    source_years = re.findall(r'20\d{2}', parsed['title'])
    rows = {}
    for index, line in enumerate(lines):
        if re.search(r'兩場|兩個場次|全部場次|全場次|都參加|皆參加', line):
            continue
        clocks = list(TIME_RE.finditer(line))
        starts_only = False
        if not clocks and (re.search(r'活動時間|開始時間|開演|第[一二三四五六七八九十\d]+場', line)
                           or START_TIME_RE.match(line)):
            clocks = list(START_TIME_RE.finditer(line)); starts_only = True
        if not clocks:
            continue
        date_line = line
        local_dates = list(DATE_RE.finditer(line))
        if not local_dates and index and re.search(r'日期|時間|場次', lines[index-1]):
            date_line = lines[index-1]
            local_dates = list(DATE_RE.finditer(date_line))
        if len(local_dates) == 1:
            d = local_dates[0]
            if not d[1] and len(years) != 1:
                raise CollectionError('registration_ambiguous_year')
            day = (_year(d[1], next(iter(years))), int(d[2]), int(d[3]))
        elif not local_dates and len(full) == 1:
            day = next(iter(full))
        else:
            raise CollectionError('registration_date_time_ambiguous')
        if (source_years and str(day[0]) not in source_years) or (source_dates and not any(
                int(d[2]) == day[1] and int(d[3]) == day[2] and (not d[1] or _year(d[1],0)==day[0])
                for d in source_dates)):
            raise CollectionError('registration_identity_mismatch')
        # A written weekday is a separate consistency check.
        weekday = re.search(r'[（(](?:星期|禮拜|週)?([一二三四五六日天])[）)]', date_line)
        if weekday and '一二三四五六日'[datetime(*day).weekday()] != weekday[1].replace('天','日'):
            raise CollectionError('registration_weekday_mismatch')
        for clock in clocks:
            sh,sm,eh,em = (*_clock(clock[1],clock[2],clock[3]),None,None) if starts_only else _range_clocks(clock)
            start = datetime(*day, sh, sm, tzinfo=TAIPEI)
            end = datetime(*day, eh, em, tzinfo=TAIPEI) if eh is not None else None
            if end and not timedelta(0) < end-start <= timedelta(hours=12):
                raise CollectionError('registration_session_invalid')
            row = rows.setdefault(start.isoformat(), {'start_time':start.isoformat(), 'end_time':None,
                'registration_choice':line, 'end_time_variants':[]})
            if end and end.isoformat() not in row['end_time_variants']:
                row['end_time_variants'].append(end.isoformat())
    if not rows:
        raise CollectionError('registration_session_choices_missing')
    for row in rows.values():
        row['end_time_variants'].sort()
        if len(row['end_time_variants']) == 1: row['end_time'] = row['end_time_variants'][0]
    return list(rows.values())


def public_form_text(page, host):
    from .sources.gameislearning import text_lines, node_html
    doc = Document(page)
    if host in ('beclass.com', 'www.beclass.com'):
        # Only the activity description, not other registrations or input forms.
        nodes = [n for n in doc.root.all() if n.attrs.get('itemprop') == 'description' or n.has_class('BOXContent')]
        if not nodes:
            raise CollectionError('registration_description_missing')
        return doc.title(), text_lines(node_html(nodes[0]))
    # Keep display text and session choices. Do not read field values or responses.
    def render(node):
        if isinstance(node,str): return node
        if node.tag in ('script','style','noscript','input','textarea','nav','footer'): return ''
        role = node.attrs.get('role')
        if role == 'listitem':
            headings = [n.text() for n in node.all() if n.attrs.get('role') == 'heading']
            if not any(re.search(r'場次|活動日期|參加日期|活動時間', h) for h in headings): return ''
            return '\n' + '\n'.join(n.attrs.get('data-value') or n.attrs.get('aria-label') or n.text()
                                      for n in node.all() if n.attrs.get('role') in ('radio','checkbox')) + '\n'
        value = ''.join(render(c) for c in node.children)
        return value + ('\n' if node.tag in ('div','p','li','br','h1','h2','tr','title') else '')
    return doc.title(), render(doc.root)


def registration_page(parsed, page, evidence):
    from .sources.gameislearning import registration_sessions
    host = urlsplit(evidence['final_url']).hostname
    if host == 'docs.google.com':
        if not same_identity(parsed, Document(page).root.text()):
            raise CollectionError('registration_identity_mismatch')
        try:
            return registration_sessions(parsed, page, evidence)
        except CollectionError as error:
            if error.code not in ('registration_date_not_explicit','registration_session_choices_missing'):
                raise
    if host == 'www.accupass.com':
        from .sources.accupass import parse_event
        events = parse_event(page, evidence['final_url'], evidence)
        if len(events) != 1 or not same_identity(parsed, events[0]['title']+' '+events[0]['text']):
            raise CollectionError('registration_identity_mismatch')
        fields = events[0]['fields']
        if fields.get('event_status') != 'https://schema.org/EventScheduled':
            raise CollectionError('registration_event_status_changed')
        if fields.get('schedule_rows'):
            rows = fields['sessions']
        elif not fields.get('sessions') and fields.get('start_time') and fields.get('end_time'):
            rows = [{'start_time':fields['start_time'],'end_time':fields['end_time']}]
        else: raise CollectionError('registration_date_time_ambiguous')
        # Reuse explicit date validation against the announcement.
        text = '\n'.join(r['start_time'][:10].replace('-','/')+' '+r['start_time'][11:16]+'-'+r['end_time'][11:16] for r in rows)
        title = events[0]['title']
    else:
        title, text = public_form_text(page, host)
        if not same_identity(parsed, title+' '+text):
            raise CollectionError('registration_identity_mismatch')
    if re.search(r'活動已取消|活動取消|延期至|改期至', text):
        raise CollectionError('registration_event_status_changed')
    rows = text_sessions(parsed, title+'\n'+text)
    return dict(parsed, sessions=rows, registration_evidence={
        'url':parsed['registration_url'], 'final_url':evidence['final_url'],
        'checked_at':evidence['fetched_at'], 'snapshot_sha256':evidence['sha256'],
        'title':title, 'choices':[r['registration_choice'] for r in rows], 'method':'public_text_v2'})


def merge_sessions(parsed, resolved):
    original = parsed.get('sessions', [])
    if original:
        by_start = {s['start_time']:s for s in resolved['sessions']}
        if set(by_start) != {s['start_time'] for s in original}:
            raise CollectionError('registration_session_conflict')
        for old in original:
            new = by_start[old['start_time']]
            if old.get('end_time') and old['end_time'] != new.get('end_time'):
                raise CollectionError('registration_session_conflict')
    return resolved


def resolve_registration(parsed, client):
    """At most six public pages and two linked hops; no form submission."""
    if parsed['sessions'] and all(r.get('end_time') for r in parsed['sessions']):
        return parsed
    if hasattr(client, 'scoped'):
        client = client.scoped(LINK_HOSTS, supported_url)
    links = list(dict.fromkeys([parsed.get('registration_url','')] + parsed.get('content_links',[])))
    queue = [(url,0,[]) for url in links if supported_url(url)]
    seen, failures, successes = set(), [], []
    parsed['registration_attempts'] = failures
    while queue and len(seen) < 6:
        url, depth, chain = queue.pop(0)
        if url in seen: continue
        seen.add(url)
        try:
            page, ev = client.get(url)
            final = ev['final_url']
            if not supported_url(final): raise CollectionError('registration_form_not_supported')
            chain = chain + [{'url':url,'final_url':final,'snapshot_sha256':ev['sha256']}]
            if urlsplit(final).hostname in LINK_PAGES:
                if depth >= 2: raise CollectionError('registration_depth_limit')
                discovered = [u for u,_,_ in Document(page).links(final) if supported_url(u)]
                # Never silently choose one form from an overlarge link directory.
                if len(set(discovered)) > 6: raise CollectionError('registration_link_limit')
                queue.extend((u,depth+1,chain) for u in dict.fromkeys(discovered) if u not in seen)
                if not discovered: raise CollectionError('registration_links_missing')
                continue
            resolved = registration_page(dict(parsed, registration_url=url), page, ev)
            resolved['registration_evidence']['hops'] = chain
            resolved['registration_url'] = parsed['registration_url']
            successes.append(merge_sessions(parsed, resolved))
        except (CollectionError, ValueError) as error:
            failures.append({'url':url,'reason':getattr(error,'code','registration_invalid_data')})
    if any(url not in seen for url,_,_ in queue): failures.append({'url':'','reason':'registration_link_limit'})
    if successes:
        signatures = {tuple(sorted((r['start_time'],r.get('end_time')) for r in s['sessions'])) for s in successes}
        if len(signatures) != 1: raise CollectionError('registration_multiple_forms_conflict')
        hard = [f for f in failures if f['reason'] not in ('registration_identity_mismatch',)]
        if hard: raise CollectionError(hard[0]['reason'])
        return successes[0]
    if failures:
        raise CollectionError(failures[0]['reason'])
    return parsed
