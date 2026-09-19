"""Load reviewed sessions; legacy seeds and crawler guesses cannot be published."""
import json
import re
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from .models import Activity, CityEnum, CategoryEnum, SourcePlatformEnum
from .collection import Client
from .sources.opentix import parse_program
from .posters import poster_url

TAIPEI = timezone(timedelta(hours=8))
DATA_PATH = Path(__file__).resolve().parents[1] / 'data/verified_activities.json'
REVIEWED_FIELDS = ('title', 'start_time', 'end_time', 'venue', 'city', 'organizer', 'price_info', 'is_free')


def parse_time(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+08:00', value):
        raise ValueError('活動時間須為完整 ISO-8601，含 +08:00；不可使用缺省日期')
    return datetime.fromisoformat(value)


def detail_url(value):
    p = urlsplit(value)
    if p.scheme != 'https' or not p.hostname or p.username or p.password:
        raise ValueError('來源須為不含憑證的 HTTPS 活動專頁')
    if p.path in ('', '/', '/ch', '/zh-tw') or p.hostname.endswith('google.com'):
        raise ValueError('首頁與搜尋頁不能作為活動證據')
    return value


def optional_external_url(value):
    if not value:
        return value
    p = urlsplit(value)
    if p.scheme != 'https' or not p.hostname or p.username or p.password:
        raise ValueError('報名連結須為不含憑證的 HTTPS 網址')
    return value


class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def normalized_text(html):
    parser = PageText()
    parser.feed(html)
    return re.sub(r'\s+', '', ' '.join(parser.parts))


def check_source_content(source, html):
    text = normalized_text(html)
    for expected in source['required_text']:
        if re.sub(r'\s+', '', expected) not in text:
            raise ValueError(f"來源內容異動，需重新人工核對：{source['url']}；缺少 {expected!r}")


def check_opentix_sessions(source, payload):
    program_id = source['url'].rsplit('/', 1)[-1]
    if not isinstance(payload, dict) or str((payload.get('result') or {}).get('id')) != program_id:
        raise ValueError('OPENTIX 節目識別異動，需重新核對')
    actual = {r['fields']['session_id']: r['fields'] for r in parse_program(payload['result'], {})}
    for expected in source['opentix_sessions']:
        session = actual.get(expected['session_id'])
        if not session or any(session.get(k) != v for k, v in expected.items()):
            raise ValueError('OPENTIX 場次時間、地點、票價或狀態異動，需重新核對：' + expected['session_id'])


def check_live_sources(sources):
    client = Client(timeout=30)
    posters = {}
    for source in sources.values():
        html, evidence = client.get(source['url'])
        detail_url(evidence['final_url'])
        if urlsplit(evidence['final_url']).hostname != urlsplit(source['url']).hostname:
            raise ValueError('來源轉址至不同網站，需重新核對')
        if len(html.encode('utf-8')) > 4_000_000:
            raise ValueError('來源回應超出限制')
        check_source_content(source, html)
        if 'opentix_sessions' in source:
            if not re.fullmatch(r'https://www\.opentix\.life/event/\d+', source['url']):
                raise ValueError('OPENTIX 場次查核來源不正確')
            payload, _ = client.json('https://csm.api.opentix.life/programs/' + source['url'].rsplit('/', 1)[-1])
            check_opentix_sessions(source, payload)
            if 'automated_review' in source:
                from .review import validate_auto_source
                validate_auto_source(source, payload['result'])
        elif source.get('automated_review', {}).get('source_type') in ('accupass', 'gameislearning'):
            from .review import validate_auto_source
            validate_auto_source(source, None, html, client=client)
        if urlsplit(source['url']).hostname != 'www.opentix.life':
            posters[source['url']] = {'url': poster_url(html, source['url']),
                                      'source_url': source['url'],
                                      'checked_at': evidence['fetched_at'],
                                      'snapshot_sha256': evidence['sha256']}
    return posters


def load_verified(path=DATA_PATH, now=None, check_sources=False):
    now = now or datetime.now(TAIPEI)
    if now.tzinfo is None:
        raise ValueError('建置時間必須包含時區')
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload.get('schema_version') != 1:
        raise ValueError('不支援的核實資料格式')
    sources = payload['sources']
    for source in sources.values():
        detail_url(source['url'])
        if not source.get('required_text') or not source.get('title'):
            raise ValueError('來源缺少可重查的公告內容')
        if parse_time(source['checked_at']) > now:
            raise ValueError('來源核對時間不可在未來')
        if not re.fullmatch(r'[a-f0-9]{64}', source.get('snapshot_sha256', '')):
            raise ValueError('來源缺少核查快照指紋')
        if 'opentix_sessions' in source:
            if not source['opentix_sessions'] or not re.fullmatch(r'[a-f0-9]{64}', source.get('api_snapshot_sha256', '')):
                raise ValueError('OPENTIX 缺少已核對場次或 API 指紋')
            if parse_time(source['api_checked_at']) > now:
                raise ValueError('API 核對時間不可在未來')
    activities, seen_ids, seen_sessions, active_source_ids = [], set(), set(), set()
    for row in payload['activities']:
        data, review = row['activity'], row['verification']
        if review.get('status') != 'verified' or not review.get('language_evidence'):
            raise ValueError('未核實活動或缺少台語內容證據，不可發布')
        source = sources[review['source_id']]
        if review.get('mode') == 'official_rules_v1':
            proof = source.get('automated_review', {})
            valid_proof = (proof.get('mode') == 'official_rules_v1' and proof.get('language_claims') and
                           (('opentix_sessions' in source and proof.get('source_type') in (None, 'opentix')) or
                            (proof.get('source_type') == 'accupass' and proof.get('session') and
                             proof.get('free_evidence')) or
                            (proof.get('source_type') == 'gameislearning' and proof.get('sessions') and
                             proof.get('trusted_language_source') is True)))
            if not valid_proof:
                raise ValueError('自動核實活動缺少可重查的官方證據')
        if 'opentix_sessions' in source:
            session = next((s for s in source['opentix_sessions'] if s['session_id'] == review.get('opentix_session_id')), None)
            if not session or any(data[k] != session[k] for k in ('start_time', 'end_time', 'venue', 'address', 'city', 'is_free')):
                raise ValueError('正式活動與已核對的 OPENTIX 場次不一致')
        if data['source_url'] != source['url']:
            raise ValueError('活動連結與核實來源不一致')
        optional_external_url(data.get('registration_url', ''))
        for field in REVIEWED_FIELDS:
            if field not in data or field not in review['confirmed_fields'] or review['confirmed_fields'][field] != data[field]:
                raise ValueError(f'活動欄位 {field} 異動，需重新核對')
        if not data['title'].strip() or not data['venue'].strip() or not data['organizer'].strip():
            raise ValueError('缺少標題、地點或主辦資訊')
        if data['city'] not in {'臺北市', '新北市', '桃園市'}:
            raise ValueError('活動不在北北桃')
        if data['is_free'] is not None and type(data['is_free']) is not bool:
            raise ValueError('費用狀態須為 true / false / null')
        if data['is_free'] is None and '未公告' not in data['price_info']:
            raise ValueError('未知費用必須明確標示')
        start = parse_time(data['start_time'])
        end = parse_time(data['end_time']) if data['end_time'] else None
        if end and end <= start:
            raise ValueError('結束時間須晚於開始時間')
        if not re.fullmatch(r'[a-z0-9_-]+', data['id']):
            raise ValueError('活動 ID 格式不正確')
        session = (data['source_url'], data['title'], data['start_time'], data['venue'])
        if data['id'] in seen_ids or session in seen_sessions:
            raise ValueError('重複活動 ID 或場次')
        seen_ids.add(data['id'])
        seen_sessions.add(session)
        if (end or start) <= now:
            continue
        act = Activity(**data)
        act.city = CityEnum(act.city)
        act.category = CategoryEnum(act.category)
        act.source_platform = SourcePlatformEnum(act.source_platform)
        act.raw_metadata = {'verified_at': source['checked_at'], 'source_title': source['title']}
        activities.append(act)
        active_source_ids.add(review['source_id'])
    if check_sources:
        # Historical records remain immutable, but an ended activity must not
        # block today's publication when its retired detail page changes.
        posters = check_live_sources({key: sources[key] for key in active_source_ids})
        for act in activities:
            if act.source_url in posters:
                proof = posters[act.source_url]
                act.cover_image = proof['url']
                act.raw_metadata['poster_evidence'] = proof
    return sorted(activities, key=lambda a: a.start_time)
