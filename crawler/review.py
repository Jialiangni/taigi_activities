"""Conservative official-evidence review, before publication; never trust candidate fields.

Only supported, explicit official session evidence can be accepted automatically.
Unstructured announcements, ambiguous language and changed sessions stay pending.
"""
import argparse
import json
import re
import tempfile
import unicodedata
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from .collection import Client, CollectionError, TAIPEI, plain
from .models import Activity, CategoryEnum, SourcePlatformEnum
from .sources.accupass import parse_event as parse_accupass_event
from .sources.opentix import parse_program
from .sources.gameislearning import (DETAIL_RE, parse_detail as parse_gameislearning_detail,
                                    supplement_registration)
from .verified import REVIEWED_FIELDS, load_verified, normalized_text, parse_time

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = {'facebook', 'instagram', 'threads'}
SOCIAL_REVIEW = {'facebook_review', 'threads_review'}
MODE = 'official_rules_v1'


def load_manual_decisions(root):
    path = Path(root) / 'data/manual_candidate_decisions.json'
    if not path.is_file():
        return {}
    data = json.loads(path.read_text())
    if data.get('schema_version') != 1 or not isinstance(data.get('decisions'), list):
        raise ValueError('人工候選判讀格式錯誤')
    rows = {}
    for row in data['decisions']:
        required = ('candidate_id', 'source_id', 'source_url', 'title', 'decision', 'reason', 'reviewed_at')
        if not all(row.get(k) for k in required) or row['decision'] != 'excluded':
            raise ValueError('人工候選判讀缺少必要欄位')
        if row['candidate_id'] in rows:
            raise ValueError('人工候選判讀 ID 重複')
        rows[row['candidate_id']] = row
    return rows


def normalize(value):
    return re.sub(r'[^\w]', '', unicodedata.normalize('NFKC', value or '').replace('台', '臺')).lower()


def source_url(value):
    p = urlsplit(value)
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')]
    return urlunsplit((p.scheme, p.netloc, p.path.rstrip('/'), urlencode(sorted(query)), ''))


def duplicate(activity, catalog, session_id=None):
    for row in catalog['activities']:
        other, review = row['activity'], row['verification']
        if session_id and str(review.get('opentix_session_id', '')) == session_id:
            return other['id']
        if activity.get('start_time') != other['start_time']:
            continue
        # The same official page and session time must never acquire another ID.
        if (source_url(activity.get('source_url', '')) == source_url(other['source_url']) and
                activity.get('end_time') == other.get('end_time')):
            return other['id']
        if (normalize(activity.get('title')) == normalize(other['title']) and
                normalize(activity.get('venue')) == normalize(other['venue']) and
                normalize(activity.get('city')) == normalize(other['city']) and
                activity.get('end_time') == other.get('end_time')):
            return other['id']
    return None


def published_accupass_series(candidate, catalog, now):
    """Return published IDs only when every still-live explicit ACCUPASS session is present."""
    if candidate.get('source_id') != 'accupass':
        return []
    sessions = candidate.get('fields', {}).get('sessions')
    if not isinstance(sessions, list):
        return []
    future = [row for row in sessions if isinstance(row, dict) and row.get('start_time')
              and row.get('end_time') and parse_time(row['end_time']) > now]
    if not future:
        return []
    by_time = {(source_url(row['activity'].get('source_url', '')), row['activity'].get('start_time'),
                row['activity'].get('end_time')): row['activity']['id'] for row in catalog['activities']}
    ids = [by_time.get((source_url(candidate['source_url']), row['start_time'], row['end_time']))
           for row in future]
    return ids if all(ids) else []


def language_claims(program, group):
    """Match labelled language declarations, not biographies, subtitles or keywords."""
    claims = []
    venue_text = plain(group.get('eventNoteContent'))
    # A venue-specific spoken language overrides a generic program declaration.
    labels = re.findall(r'(?<!字幕)(?:演出語言|發音|語言)\s*[：:]\s*([^。；]{1,75})', venue_text)
    if any(not re.match(r'(?:臺灣)?[台臺]語(?:\s|[、，,/／+（(。]|為主|$)', value) for value in labels):
        return []
    for origin, html in [('description', program.get('description', '')),
                         ('eventNoteContent', group.get('eventNoteContent', ''))]:
        # br and paragraph boundaries matter: do not join an unrelated biography.
        lines = re.split(r'</(?:p|li|div)>|<br\s*/?>', html or '', flags=re.I)
        for line in lines:
            text = plain(line).strip()
            if not text or len(text) > 220:
                continue
            if re.search(r'取消|延期|非台語|非臺語|不使用|不含|並非|並不是|部分場次|限定場次|台語指導|臺語指導|[台臺]語以外', text):
                continue
            labelled = re.search(r'(?:演出語言|發音|語言)\s*[：:]\s*((?:臺灣)?[台臺]語[^。；\n]{0,75})', text)
            ratio = re.search(r'((?:臺灣)?[台臺]語發音比例\s*[：:]\s*(\d+(?:\.\d+)?)\s*%)', text)
            # A subtitle label alone says nothing about the spoken language.
            if labelled and text[:labelled.start()].endswith('字幕'):
                labelled = None
            if labelled and re.match(r'(?:臺灣)?[台臺]語(?:\s|[、，,/／+（(。]|為主|$)', labelled[1]):
                quote = labelled.group(0).strip()
            elif ratio and 0 < float(ratio[2]) <= 100:
                quote = ratio[1]
            else:
                continue
            claims.append({'origin': origin, 'group_id': str(group['id']), 'quote': quote})
    return claims


def accupass_language_claim(title, text):
    """Accept an explicitly labelled Taigi session, never a loose keyword hit."""
    for value in (title or '', text or ''):
        matched = re.search(r'【(?:臺灣)?[台臺]語場(?:：[^】]{1,40})?】', value)
        if matched:
            return matched.group(0)
    return None


def validate_auto_source(source, program, html=None, client=None):
    """Recheck frozen language/status evidence on every future public build."""
    proof = source.get('automated_review', {})
    if proof.get('source_type') == 'accupass':
        require(isinstance(html, str), 'accupass_page_missing')
        rows = parse_accupass_event(html, source['url'], {})
        require(len(rows) == 1, 'accupass_identity_changed')
        live = rows[0]
        require(live['kind'] == 'event_period' and not live['fields'].get('sessions'),
                'accupass_series_needs_review')
        require(all(live['fields'].get(k) == proof['session'].get(k) for k in
                    ('start_time', 'end_time', 'venue', 'address', 'city', 'organizer', 'event_status')),
                'accupass_session_changed')
        require(normalize(live['title']) == normalize(source['title']), 'accupass_title_changed')
        quote = accupass_language_claim(live['title'], live['text'])
        require(quote == proof['language_claims'][0]['quote'], 'accupass_language_changed')
        require(proof['free_evidence'] in live['text'], 'accupass_price_changed')
        return
    if proof.get('source_type') == 'gameislearning':
        require(isinstance(html, str), 'gameislearning_page_missing')
        live = parse_gameislearning_detail(html, source['url'], {}, now=datetime.now(TAIPEI))
        if proof.get('registration_evidence'):
            live = supplement_registration(live, client or Client())
            require(live.get('registration_evidence', {}).get('final_url') ==
                    proof['registration_evidence']['final_url'], 'registration_destination_changed')
        require(normalize(live['title']) == normalize(source['title']), 'gameislearning_title_changed')
        require(proof.get('trusted_language_source') is True, 'trusted_language_source_missing')
        require(live['city'] in ('臺北市', '新北市', '桃園市'), 'outside_region')
        for expected in proof.get('sessions', []):
            actual = next((row for row in live['sessions']
                           if row.get('start_time') == expected.get('start_time')
                           and row.get('end_time') == expected.get('end_time')), None)
            require(actual, 'gameislearning_session_changed')
            if proof.get('registration_evidence'):
                require(all(actual.get(k) == expected.get(k) for k in
                            ('registration_choice', 'end_time_variants')),
                        'registration_session_evidence_changed')
        if proof.get('registration_url'):
            require(live['registration_url'] == proof['registration_url'],
                    'gameislearning_registration_changed')
        return
    if program.get('status') != 3 or plain(program.get('changeNotification')):
        raise ValueError('自動核實節目狀態或異動公告改變，停止發布')
    groups = {str(g['id']): g for g in program['eventVenues']}
    for claim in source['automated_review']['language_claims']:
        group = groups.get(claim['group_id'])
        if not group or claim not in language_claims(program, group):
            raise ValueError('自動核實語言證據異動，停止發布')


def require(condition, reason):
    if not condition:
        raise Pending(reason)


class Pending(Exception):
    pass


def social_official_candidates(candidate, client):
    """Route trusted OPENTIX links from a social snapshot into the strict verifier."""
    context = candidate.get('review_context') or {}
    links = context.get('discovered_links') or []
    program_ids = []
    for link in links:
        if not isinstance(link, dict) or link.get('is_page_author') is not True:
            continue
        matched = re.fullmatch(r'https://www\.opentix\.life/event/(\d+)', source_url(link.get('url', '')))
        if matched and matched.group(1) not in program_ids:
            program_ids.append(matched.group(1))
    rows = []
    for program_id in program_ids:
        data, evidence = client.json('https://csm.api.opentix.life/programs/' + program_id)
        program = data.get('result') if isinstance(data, dict) else None
        require(isinstance(program, dict) and str(program.get('id')) == program_id,
                'social_official_program_identity_changed')
        for row in parse_program(program, evidence):
            row['issues'].append('discovered_from_social_account_official_link')
            row['social_parent_candidate_id'] = candidate['id']
            rows.append(row)
    return rows


def trusted_registration_link(value):
    """Account-authored Google Forms and Linktree URLs are accepted registration routes."""
    try:
        parsed = urlsplit(value or '')
    except ValueError:
        return False
    host = (parsed.hostname or '').lower().rstrip('.')
    if parsed.scheme != 'https' or parsed.username or parsed.password:
        return False
    if host == 'forms.gle':
        return True
    if host in ('docs.google.com', 'forms.google.com'):
        return parsed.path == '/forms' or parsed.path.startswith('/forms/')
    return host in ('linktr.ee', 'www.linktr.ee', 'linktree.com', 'www.linktree.com')


def verify_accupass(candidate, client, now):
    """Auto-verify only a single, explicitly labelled Taigi session with explicit free admission."""
    url = source_url(candidate['source_url'])
    matched = re.fullmatch(r'https://www\.accupass\.com/event/(\d+)', url)
    require(matched, 'unsupported_official_url')
    html, page = client.get(url)
    require(page['final_url'] == url, 'official_page_redirected')
    rows = parse_accupass_event(html, url, page)
    require(len(rows) == 1, 'program_identity_changed')
    live = rows[0]
    require(live['kind'] == 'event_period' and not live['fields'].get('sessions'),
            'series_or_duration_needs_review')
    f = live['fields']
    require(f['city'] in ('臺北市', '新北市', '桃園市'), 'outside_region')
    require(f['start_time'] and f['end_time'], 'missing_session_times')
    start, end = parse_time(f['start_time']), parse_time(f['end_time'])
    require(end > now, 'expired')
    require(timedelta(0) < end - start <= timedelta(hours=12), 'series_or_duration_needs_review')
    require(f['event_status'] == 'https://schema.org/EventScheduled', 'event_status_needs_review')
    require(f['venue'] and f['address'] and f['organizer'] and live['title'], 'missing_identity_fields')
    require(normalize(candidate['title']) == normalize(live['title']), 'candidate_title_changed')
    require(all(candidate['fields'].get(k) == f.get(k) for k in
                ('start_time', 'end_time', 'venue', 'address', 'city', 'organizer', 'event_status')),
            'candidate_session_changed')
    quote = accupass_language_claim(live['title'], live['text'])
    require(quote, 'explicit_session_language_missing')
    free = re.search(r'(?:本活動[^。\n]{0,40})?免費報名', live['text'])
    require(free, 'ticket_terms_need_review')
    free_evidence = free.group(0)
    title = live['title']
    category = CategoryEnum.TOUR if re.search(r'導覽|走讀', title + live['text'][:500]) else CategoryEnum.OTHER
    event_id = matched.group(1)
    act = Activity(id='acc_' + event_id + '_' + start.strftime('%Y%m%d_%H%M'), title=title,
                   description='官方公告明列為台語場；活動內容、報到方式與參加規定請看官方活動頁。',
                   city=f['city'], category=category, start_time=f['start_time'], end_time=f['end_time'],
                   venue=f['venue'], address=f['address'], organizer=f['organizer'],
                   source_platform=SourcePlatformEnum.ACCUPASS, source_url=url,
                   price_info='免費，需事先報名', is_free=True,
                   tags=['台語', '官方資料自動核實']).to_dict()
    session = {k: f[k] for k in
               ('start_time', 'end_time', 'venue', 'address', 'city', 'organizer', 'event_status')}
    key = 'auto_acc_' + event_id
    source = {'url': url, 'title': title, 'required_text': [title, f['venue'], quote, free_evidence],
              'checked_at': page['fetched_at'], 'snapshot_sha256': page['sha256'],
              'automated_review': {'mode': MODE, 'source_type': 'accupass',
                                   'language_claims': [{'origin': 'official_page', 'quote': quote}],
                                   'free_evidence': free_evidence, 'session': session}}
    row = {'activity': act, 'verification': {'status': 'verified', 'source_id': key,
           'mode': MODE,
           'method': 'ACCUPASS 官方頁重新核對；單一場次明列台語場、日期、時間、地點、主辦及免費報名。',
           'language_evidence': quote,
           'confirmed_fields': {k: act[k] for k in REVIEWED_FIELDS}}}
    return key, source, row


def verify_gameislearning(candidate, client, now):
    """Trust this curated directory for language, while rechecking event facts."""
    url = source_url(candidate['source_url'])
    matched = DETAIL_RE.fullmatch(url)
    require(matched and candidate.get('kind') == 'session', 'unsupported_trusted_directory_candidate')
    require(candidate.get('trusted_language_source') is True, 'trusted_language_source_missing')
    page_html, page = client.get(url)
    require(page['final_url'] == url, 'official_page_redirected')
    fields = candidate['fields']
    live = parse_gameislearning_detail(page_html, url, page, {
        'city': fields.get('city'), 'district': fields.get('district'),
        'type': '', 'is_free': fields.get('is_free'),
        'published_at': fields.get('published_at')}, now)
    live = supplement_registration(live, client)
    require(normalize(live['title']) == normalize(candidate['title']), 'candidate_title_changed')
    require(live['city'] in ('臺北市', '新北市', '桃園市'), 'outside_region')
    require(live['venue'] and live['address'] and live['organizer'], 'missing_identity_fields')
    require(live['address'] == fields.get('address') and live['venue'] == fields.get('venue'),
            'candidate_location_changed')
    require(live['registration_url'] == fields.get('registration_url', ''),
            'candidate_registration_changed')
    session = next((row for row in live['sessions']
                    if row.get('start_time') == fields.get('start_time')
                    and row.get('end_time') == fields.get('end_time')), None)
    require(session, 'candidate_session_changed')
    start = parse_time(session['start_time'])
    end = parse_time(session['end_time']) if session.get('end_time') else None
    require((end or start) > now, 'expired')
    require(end is None or timedelta(0) < end - start <= timedelta(hours=12), 'invalid_session_duration')
    is_free = fields.get('is_free')
    require(is_free is None or type(is_free) is bool, 'invalid_ticket_terms')
    price = ('免費，報名方式請看活動公告' if is_free is True else
             '需付費，金額與報名方式請看活動公告' if is_free is False else
             '費用未公告，請查看活動公告')
    language = '台語站活動專頁全部列為台語活動（使用者指定信任來源）'
    description = '台語站收錄的台語活動；內容、參加資格與最新異動請查看活動公告。'
    if len(session.get('end_time_variants', [])) > 1:
        description += '報名表的結束時間有不同記載，僅列確定的開始時間，結束時間請向主辦確認。'
    activity_id = 'gameislearning_' + matched.group(1) + '_' + start.strftime('%Y%m%d_%H%M')
    act = Activity(id=activity_id, title=live['title'], description=description,
                   city=live['city'], district=fields.get('district', ''),
                   category=fields.get('category', CategoryEnum.OTHER.value),
                   start_time=session['start_time'], end_time=session['end_time'],
                   venue=live['venue'], address=live['address'], organizer=live['organizer'],
                   source_platform=SourcePlatformEnum.GAME_IS_LEARNING, source_url=url,
                   registration_url=live['registration_url'], price_info=price, is_free=is_free,
                   cover_image=live['cover_image'],
                   tags=['台語', '台語站信任來源', '自動核實場次']).to_dict()
    proof_session = {'start_time': session['start_time'], 'end_time': session['end_time'],
                     'venue': live['venue'], 'address': live['address'], 'city': live['city']}
    key = 'auto_gameislearning_' + matched.group(1)
    required = [live['title'], live['venue']]
    source = {'url': url, 'title': live['title'], 'required_text': required,
              'checked_at': page['fetched_at'], 'snapshot_sha256': page['sha256'],
              'automated_review': {'mode': MODE, 'source_type': 'gameislearning',
                  'trusted_language_source': True, 'language_claims': [
                      {'origin': 'trusted_directory_policy', 'quote': language}],
                  'registration_url': live['registration_url'], 'sessions': [proof_session]}}
    if live.get('registration_evidence'):
        source['automated_review']['registration_evidence'] = live['registration_evidence']
        proof_session['registration_choice'] = session['registration_choice']
        proof_session['end_time_variants'] = session['end_time_variants']
    row = {'activity': act, 'verification': {'status': 'verified', 'source_id': key,
           'mode': MODE,
           'method': '台語站為使用者指定信任的台語活動來源；重新核對單場日期、時間、地點、費用標示與報名網址。',
           'language_evidence': language,
           'gameislearning_session_key': session['start_time'],
           'confirmed_fields': {k: act[k] for k in REVIEWED_FIELDS}}}
    if live['cover_image']:
        row['verification']['poster_evidence'] = {
            'url': live['cover_image'], 'source_url': url,
            'checked_at': page['fetched_at'], 'snapshot_sha256': page['sha256']}
    return key, source, row


def verify_opentix(candidate, client, now):
    url = candidate['source_url']
    require(re.fullmatch(r'https://www\.opentix\.life/event/\d+', url), 'unsupported_official_url')
    pid = url.rsplit('/', 1)[-1]
    data, api = client.json('https://csm.api.opentix.life/programs/' + pid)
    program = data.get('result') or {}
    require(str(program.get('id')) == pid, 'program_identity_changed')
    require(program.get('status') == 3, 'program_status_needs_review')
    require(not plain(program.get('changeNotification')), 'change_notice_needs_review')
    sid = str(candidate.get('fields', {}).get('session_id', ''))
    live = next((r for r in parse_program(program, api) if r['fields']['session_id'] == sid), None)
    require(live, 'session_missing')
    f = live['fields']
    group = next(g for g in program['eventVenues'] if any(str(e['id']) == sid for e in g['events']))
    require(f['city'] in ('臺北市', '新北市', '桃園市'), 'outside_region')
    require(f['start_time'] and f['end_time'], 'missing_session_times')
    start, end = parse_time(f['start_time']), parse_time(f['end_time'])
    require(end > now, 'expired')
    require(timedelta(0) < end - start <= timedelta(hours=12), 'series_or_duration_needs_review')
    require(f['platform_session_status'] == 0, 'session_status_needs_review')
    require(not re.search(r'取消|延期|改期|異動|場次限定|華語場|國語場|英語場|客語場', f['session_name'] or ''),
            'session_language_or_change_needs_review')
    claims = language_claims(program, group)
    require(claims, 'explicit_session_language_missing')
    # Mixed-version/series announcements need a person to associate language and dates.
    require(not re.search(r'雙版本|不同版本|各場.*語言|部分場次', plain(program.get('description'))),
            'multi_version_language_needs_review')
    require(f['venue'] and f['address'] and f['organizer'] and program.get('name'), 'missing_identity_fields')
    require(f['price_info'] and f['is_free'] is not None, 'ticket_terms_need_review')
    require(all(type(p) in (int, float) and 0 <= p <= 100000 for p in f['price_info']), 'invalid_prices')
    # Known candidate disagreement is not silently accepted as a correction.
    require(normalize(candidate['title']) == normalize(program['name']), 'candidate_title_changed')
    require(all(candidate['fields'].get(k) == f[k] for k in
                ('start_time', 'end_time', 'venue', 'city', 'address', 'organizer', 'price_info',
                 'is_free', 'platform_session_status', 'session_name', 'change_notification')),
            'candidate_session_changed')
    html, page = client.get(url)
    require(page['final_url'] == url, 'official_page_redirected')
    quote = claims[0]['quote']
    required = [program['name'], f['venue'], quote]
    require(all(normalized_text(x) in normalized_text(html) for x in required), 'page_api_disagree')
    prices = '、'.join(format(p, 'g') for p in f['price_info'])
    price = ('票面價格：' + prices + '元；折扣、贊助票與購票條件依官方頁面')
    description = '官方語言說明：' + quote + '\n入場規定、購票條件及節目詳情請查閱官方活動公告。'
    act = Activity(id='opentix_' + sid, title=program['name'], description=description,
                   city=f['city'], category=CategoryEnum.PERFORMANCE,
                   start_time=f['start_time'], end_time=f['end_time'], venue=f['venue'], address=f['address'],
                   organizer='、'.join(f['organizer']), source_platform=SourcePlatformEnum.OPENTIX,
                   source_url=url, price_info=price, is_free=f['is_free'], tags=['台語', '官方資料自動核實']).to_dict()
    key = 'auto_op_' + pid
    source = {'url': url, 'title': program['name'], 'required_text': required,
              'checked_at': page['fetched_at'], 'snapshot_sha256': page['sha256'],
              'api_checked_at': api['fetched_at'], 'api_snapshot_sha256': api['sha256'],
              'opentix_sessions': [f], 'automated_review': {'mode': MODE, 'language_claims': [claims[0]]}}
    row = {'activity': act, 'verification': {'status': 'verified', 'source_id': key,
           'mode': MODE, 'method': '官方活動頁與場次 API 重新核對；明列語言、日期、場地、主辦、票價及狀態。',
           'language_evidence': quote, 'opentix_session_id': sid,
           'confirmed_fields': {k: act[k] for k in REVIEWED_FIELDS}}}
    return key, source, row


def read_candidates(folder, now):
    report = json.loads((folder / 'report.json').read_text())
    collected = datetime.fromisoformat(report['collected_at'])
    require(collected.tzinfo is not None and timedelta(0) <= now-collected <= timedelta(hours=36),
            'candidate_report_stale_or_future')
    rows = []
    for entry in report['sources']:
        sid = entry['source_id']
        require(re.fullmatch(r'[a-z0-9_]+', sid), 'invalid_source_id')
        if sid in PRIVATE:
            continue
        path = folder / (sid + '.json')
        require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 20_000_000,
                'candidate_file_missing_or_invalid')
        data = json.loads(path.read_text())
        require(data['source_id'] == sid and len(data['candidates']) == entry['candidate_count'],
                'candidate_report_count_mismatch')
        for c in data['candidates']:
            require(c['source_id'] == sid and isinstance(c['fields'], dict), 'invalid_candidate')
            rows.append(c)
    require(len(rows) <= 20000, 'too_many_candidates')
    return report, rows


def review(folder, root=ROOT, client=None, now=None, apply=False):
    now, client = now or datetime.now(TAIPEI), client or Client(timeout=30)
    report, candidates = read_candidates(Path(folder), now)
    catalog_path = root / 'data/verified_activities.json'
    load_verified(catalog_path, now=now)  # Never repair/bypass an invalid existing catalog.
    catalog = json.loads(catalog_path.read_text())
    published_urls = {source_url(row['activity'].get('source_url', '')) for row in catalog['activities']}
    expanded = []
    for candidate_row in candidates:
        expanded.append(candidate_row)
        if candidate_row['source_id'] not in SOCIAL_REVIEW:
            continue
        context = candidate_row.get('review_context') or {}
        if any(isinstance(link, dict) and link.get('is_page_author') is True
               and source_url(link.get('url', '')) in published_urls
               for link in context.get('discovered_links', [])):
            continue
        try:
            routed = social_official_candidates(candidate_row, client)
            candidate_row['_social_routed_count'] = len(routed)
            expanded.extend(routed)
        except (CollectionError, Pending, ValueError, KeyError, TypeError) as error:
            candidate_row['_social_automation_error'] = (
                error.code if isinstance(error, CollectionError) else str(error) if isinstance(error, Pending)
                else type(error).__name__)
    candidates = expanded
    translations = json.loads((root / 'data/ui_taigi.json').read_text())
    prices = json.loads((root / 'data/ui_price_taigi.json').read_text())
    manual = load_manual_decisions(root)
    decisions, seen = [], set()
    for number, c in enumerate(candidates, 1):
        item = {'candidate_id': c['id'], 'source_id': c['source_id'], 'source_url': c['source_url'],
                'title': c['title'], 'decision': 'pending'}
        try:
            identity = (c['source_id'], c['id'])
            if identity in seen:
                item.update(decision='duplicate', reason='duplicate_candidate')
                continue
            seen.add(identity)
            manual_row = manual.get(c['id'])
            if manual_row:
                require(all(c[k] == manual_row[k] for k in ('source_id', 'source_url', 'title')),
                        'manual_decision_identity_changed')
                item.update(decision='excluded', reason=manual_row['reason'],
                            review_mode='owner_feedback', reviewed_at=manual_row['reviewed_at'])
                if manual_row.get('resource_id'):
                    item['resource_id'] = manual_row['resource_id']
                continue
            if c['source_id'] in SOCIAL_REVIEW:
                context = c.get('review_context')
                require(isinstance(context, dict) and isinstance(context.get('discovered_links'), list)
                        and isinstance(context.get('draft'), dict), 'invalid_social_review_snapshot')
                item['review_context'] = context
                published_urls = {source_url(row['activity'].get('source_url', '')): row['activity']['id']
                                  for row in catalog['activities']}
                matched = next((published_urls.get(source_url(link.get('url', '')))
                                for link in context['discovered_links'] if isinstance(link, dict)
                                and link.get('is_page_author') is True
                                and published_urls.get(source_url(link.get('url', '')))), None)
                if matched:
                    item.update(decision='duplicate', reason='official_link_already_published', activity_id=matched)
                    continue
                if c.get('_social_routed_count'):
                    item.update(decision='routed', reason='official_opentix_link_routed_to_automatic_verification',
                                routed_session_count=c['_social_routed_count'])
                    continue
                registration = [link['url'] for link in context['discovered_links']
                                if isinstance(link, dict) and link.get('is_page_author') is True
                                and trusted_registration_link(link.get('url'))]
                if registration:
                    item.update(decision='routed',
                                reason='page_authored_registration_link_accepted_for_automatic_followup',
                                accepted_registration_links=registration)
                    continue
                if c.get('_social_automation_error'):
                    raise Pending('official_link_verification_failed:' + c['_social_automation_error'])
                trusted = [link for link in context['discovered_links'] if isinstance(link, dict)
                           and link.get('is_page_author') is True]
                if trusted:
                    raise Pending('official_link_adapter_not_available')
                if context['discovered_links']:
                    raise Pending('comment_link_authorship_needs_review')
                raise Pending('official_event_link_missing')
            published_series = published_accupass_series(c, catalog, now)
            if published_series:
                item.update(decision='duplicate', reason='all_future_sessions_already_published',
                            activity_ids=published_series)
                continue
            hint = dict(c['fields'], title=c['title'], source_url=c['source_url'])
            existing = duplicate(hint, catalog, str(c['fields'].get('session_id', '')) if c['source_id']=='opentix' else None)
            if existing:
                item.update(decision='duplicate', reason='already_published', activity_id=existing)
                continue
            if c['source_id'] == 'accupass':
                if c.get('fields', {}).get('sessions'):
                    raise Pending('structured_sessions_need_review')
                key, source, row = verify_accupass(c, client, now)
            elif c['source_id'] == 'gameislearning':
                key, source, row = verify_gameislearning(c, client, now)
            else:
                require(c['source_id'] == 'opentix' and c['kind'] == 'session',
                        'unstructured_source_needs_review')
                key, source, row = verify_opentix(c, client, now)
            a = row['activity']
            existing = duplicate(a, catalog, row['verification'].get('opentix_session_id'))
            if existing:
                item.update(decision='duplicate', reason='already_published', activity_id=existing)
                continue
            # Same city/time and near-identical title or venue: hold rather than risk cross-platform duplicates.
            for old in catalog['activities']:
                b = old['activity']
                if a['city'] == b['city'] and a['start_time'] == b['start_time']:
                    require(normalize(a['venue']) != normalize(b['venue']) and
                            normalize(a['title']) not in normalize(b['title']) and
                            normalize(b['title']) not in normalize(a['title']), 'possible_cross_source_duplicate')
            if key in catalog['sources'] and c['source_id'] == 'opentix':
                old = catalog['sources'][key]
                source['opentix_sessions'] = old['opentix_sessions'] + source['opentix_sessions']
                source['required_text'] = list(dict.fromkeys(old['required_text'] + source['required_text']))
                source['automated_review']['language_claims'] = old['automated_review']['language_claims'] + source['automated_review']['language_claims']
            if key in catalog['sources'] and c['source_id'] == 'gameislearning':
                old = catalog['sources'][key]
                source['required_text'] = list(dict.fromkeys(old['required_text'] + source['required_text']))
                source['automated_review']['sessions'] = old['automated_review']['sessions'] + source['automated_review']['sessions']
            catalog['sources'][key] = source
            catalog['activities'].append(row)
            translations[a['description']] = '這場明列做台語場。活動內容、報到方式佮參加規定，請看官方活動頁。'
            if c['source_id'] == 'opentix':
                translations[a['description']] = '這場有台語內容。詳細節目紹介、入場規定佮報名狀況，請看活動公告。'
                amounts = '、'.join(format(p, 'g') for p in source['opentix_sessions'][-1]['price_info'])
                prices[a['price_info']] = '票價：' + amounts + '元；折扣佮買票規定請看官方公告。'
            elif c['source_id'] == 'accupass':
                prices[a['price_info']] = '毋免錢，愛事先報名'
            else:
                translations[a['description']] = '台語站收錄的台語活動；內容、參加資格佮最新異動，請看活動公告。'
                if '報名表的結束時間有不同記載' in a['description']:
                    translations[a['description']] += '報名表的結束時間有無仝的記載，這頁干焦列確定的開始時間；結束時間請問主辦單位。'
                prices[a['price_info']] = ('毋免錢，報名方式請看活動公告' if a['is_free'] is True else
                                           '愛納錢，金額佮報名方式請看活動公告' if a['is_free'] is False else
                                           '所費猶未公告，請看活動公告')
            item.update(decision='approved',
                        reason=('official_page_single_session_verified' if c['source_id'] == 'accupass'
                                else 'trusted_taigi_directory_session_verified' if c['source_id'] == 'gameislearning'
                                else 'official_page_and_session_api_verified'), activity_id=a['id'])
        except Pending as e:
            item['reason'] = str(e)
            if str(e) in ('expired', 'outside_region'):
                item['decision'] = 'excluded'
        except (CollectionError, ValueError, KeyError, TypeError, StopIteration) as e:
            item['reason'] = 'verification_failed:' + (e.code if isinstance(e, CollectionError) else type(e).__name__)
        finally:
            decisions.append(item)
            if number % 50 == 0:
                print('Reviewed', number, '/', len(candidates), dict(Counter(d['decision'] for d in decisions)), flush=True)
    audit = {'schema_version': 1, 'mode': MODE, 'reviewed_at': now.isoformat(timespec='seconds'),
             'applied_to_catalog': apply,
             'collected_at': report['collected_at'], 'candidate_count': len(candidates),
             'counts': dict(Counter(d['decision'] for d in decisions)),
             'collection_status_counts': dict(Counter(s['status'] for s in report['sources'])),
             'decisions': decisions}
    manifest = Path(folder) / '_collection_run.json'
    if manifest.is_file():
        audit['collection_run'] = json.loads(manifest.read_text())
    outputs = {'data/verified_activities.json': catalog, 'data/ui_taigi.json': translations,
               'data/ui_price_taigi.json': prices, 'data/audit/latest-candidate-review.json': audit}
    with tempfile.TemporaryDirectory() as temp:
        staged = Path(temp)
        for name, value in outputs.items():
            p = staged / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        load_verified(staged / 'data/verified_activities.json', now=max(now, datetime.now(TAIPEI)))
        # Publication remains gated by the separate full live-source/build/tests step.
        for name in outputs:
            if apply or name.endswith('latest-candidate-review.json'):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                tmp = target.with_suffix('.tmp')
                tmp.write_bytes((staged / name).read_bytes())
                tmp.replace(target)
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    audit = review(args.candidates, apply=args.apply)
    print(json.dumps({k: v for k, v in audit.items() if k != 'decisions'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
