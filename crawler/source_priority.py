"""ACCUPASS registration links identify the primary publisher of directory events."""
import re
from urllib.parse import urlsplit


def accupass_url(value):
    try:
        p = urlsplit(value or '')
        if p.scheme != 'https' or p.netloc.lower() not in ('accupass.com', 'www.accupass.com'):
            return ''
        m = re.fullmatch(r'/event/(\d+)/?', p.path)
        return 'https://www.accupass.com/event/' + m[1] if m else ''
    except ValueError:
        return ''


def directory_registration(activity):
    if not re.fullmatch(r'https://www\.gameislearning\.url\.tw/taigi-info\.php\?news=[a-z0-9]+', activity.get('source_url', '')):
        return ''
    return accupass_url(activity.get('registration_url'))


def primary_session(activity, catalog):
    url = directory_registration(activity)
    if not url or not activity.get('start_time') or not activity.get('city'):
        return None
    matches = [r for r in catalog['activities']
               if r['verification'].get('status') == 'verified'
               and accupass_url(r['activity'].get('source_url')) == url
               and r['activity']['start_time'] == activity['start_time']
               and r['activity']['city'] == activity['city']]
    return matches[0] if len(matches) == 1 else None


def publication_priority(catalog):
    """Keep historical rows, but publish only the verified primary sessions."""
    decisions = {}
    for row in catalog['activities']:
        a = row['activity']
        url = directory_registration(a)
        if not url:
            continue
        primary = primary_session(a, catalog)
        decisions[a['id']] = {
            'primary_url': url,
            'primary_activity_id': primary['activity']['id'] if primary else None,
            'reason': 'accupass_primary_session' if primary else 'accupass_session_not_verified'}
    return decisions
