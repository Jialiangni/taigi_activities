"""Re-use explicitly reviewed mixed-session facts only while official content matches."""
import hashlib
import json
import re
from pathlib import Path

from .collection import CollectionError
from .models import Activity
from .sources.accupass import parse_event

MODE = 'reviewed_text_sessions_v1'


def digest(text):
    return hashlib.sha256(re.sub(r'\s+', '', text).encode()).hexdigest()


def require(condition, code):
    if not condition:
        raise CollectionError(code)


def check_contract(live, contract):
    fields = live['fields']
    require(not fields.get('text_schedule_issue'), 'text_schedule_changed')
    require(contract['title'] == live['title'], 'reviewed_title_changed')
    require(contract['article_sha256'] == digest(fields['official_summary']), 'reviewed_article_changed')
    require(all(fields.get(k) == v for k, v in contract['identity'].items()), 'reviewed_identity_changed')
    require(fields['city'] in ('臺北市', '新北市', '桃園市'), 'outside_region')
    require(fields['event_status'] == 'https://schema.org/EventScheduled', 'event_status_needs_review')
    require(contract['is_free'] is False and contract['ticket_quote'] in fields['official_summary'], 'reviewed_ticket_terms_missing')
    require(contract['venue'] and contract['venue'] in fields['official_summary'], 'reviewed_venue_missing')
    require(contract['language_quote'] in fields['official_summary'], 'reviewed_language_missing')
    require(contract['description_quotes'] and all(q in fields['official_summary'] for q in contract['description_quotes']),
            'reviewed_description_missing')
    for session in contract['sessions']:
        require(session in fields['text_schedule_rows'] and session['language_classification'] == 'explicit_taigi_label',
                'reviewed_session_changed')


def contract_for(live, root):
    path = Path(root) / 'data/accupass_text_reviews.json'
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    require(data.get('schema_version') == 1, 'unsupported_text_review_version')
    contract = data['events'].get(live['source_url'])
    if contract:
        check_contract(live, contract)
    return contract


def verify_session(candidate, client, root, now):
    url = candidate['source_url']
    require(re.fullmatch(r'https://www\.accupass\.com/event/\d+', url), 'unsupported_official_url')
    html, evidence = client.get(url)
    require(evidence['final_url'] == url, 'official_page_redirected')
    live_rows = parse_event(html, url, evidence)
    require(len(live_rows) == 1, 'program_identity_changed')
    live = live_rows[0]
    contract = contract_for(live, root)
    require(contract is not None, 'text_session_conditions_not_reviewed')
    selected = candidate['fields']['reviewed_text_session']
    require(selected in contract['sessions'], 'text_session_not_reviewed')
    from .verified import parse_time, REVIEWED_FIELDS
    require(parse_time(selected['start_time']) > now, 'expired')
    fields = live['fields']
    description = '\n'.join([selected['schedule_quote'], *contract['description_quotes']])
    activity = Activity(id='acc_' + url.rsplit('/', 1)[-1] + '_' + parse_time(selected['start_time']).strftime('%Y%m%d_%H%M'),
        title=live['title'], description=description, city=fields['city'], category=selected['category'],
        start_time=selected['start_time'], end_time=selected['end_time'], venue=contract['venue'],
        address=fields['address'], organizer=fields['organizer'], source_url=url, registration_url=url,
        source_platform='Accupass 活動通', cover_image=fields.get('cover_image', ''),
        price_info=contract['price_info'], is_free=contract['is_free'],
        tags=['台語', selected['performer']], raw_metadata={'text_session': selected}).to_dict()
    key = 'reviewed_text_' + activity['id']
    source = {'url': url, 'title': live['title'], 'checked_at': evidence['fetched_at'],
              'snapshot_sha256': evidence['sha256'],
              'required_text': [live['title'], selected['schedule_quote'], *contract['description_quotes']],
              'text_session_review': {'mode': MODE, 'contract': contract, 'session': selected, 'activity': activity}}
    row = {'activity': activity, 'verification': {'status': 'verified', 'source_id': key, 'mode': MODE,
           'method': 'Codex逐場核對官方混合場次、台語證據與購票限制；程式重查已核對正文及場次綁定，非人類審定。',
           'language_evidence': contract['language_quote'],
           'confirmed_fields': {k: activity[k] for k in REVIEWED_FIELDS}}}
    return key, source, row


def validate_live(source, html):
    proof = source['text_session_review']
    rows = parse_event(html, source['url'], {})
    require(len(rows) == 1, 'program_identity_changed')
    check_contract(rows[0], proof['contract'])
    require(proof['session'] in proof['contract']['sessions'], 'reviewed_session_changed')
