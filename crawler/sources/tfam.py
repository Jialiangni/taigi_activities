"""Read the same public JSON listing used by TFAM's JavaScript activity page."""
from ..collection import Collector, CollectionError, Result, candidate, plain, relevant, KEYWORDS
from ..posters import image_url, poster_fields

ENDPOINT = 'https://www.tfam.museum/ashx/Event.ashx?ddlLang=zh-tw'


def parse_events(payload, evidence, keywords):
    if not isinstance(payload, dict) or str(payload.get('Status')) != '1' or not isinstance(payload.get('Data'), list):
        raise CollectionError('invalid_tfam_listing')
    rows = []
    for item in payload['Data']:
        if not isinstance(item, dict) or not str(item.get('EduID', '')).isdigit() or 'EduName' not in item:
            raise CollectionError('invalid_tfam_event')
        title, body = plain(item['EduName']), plain(item.get('Content', ''))
        if not relevant(title + ' ' + body, keywords):
            continue
        url = 'https://www.tfam.museum/Event/Event_page.aspx?ddlLang=zh-tw&id=' + str(item['EduID'])
        artwork = poster_fields('<article>' + (item.get('Content') or '') + '</article>', url)
        # The official page declares WebSiteFile=https://www.tfam.museum/File/.
        if item.get('PlayImg'):
            artwork['cover_image'] = image_url(item['PlayImg'], 'https://www.tfam.museum/File/') or artwork['cover_image']
        rows.append(candidate('tfam', url, title, body, evidence,
                              {'start_time': None, 'end_time': None, 'is_free': None,
                               **artwork},
                              issues=['manual_event_verification_required', 'recurring_dates_require_session_review']))
    return rows


class TfamCrawler(Collector):
    def __init__(self, keywords=None):
        self.keywords = keywords or KEYWORDS

    def collect(self, client):
        result = Result('tfam', 'official_current_activity_json')
        try:
            payload, ev = client.json(ENDPOINT, {'State': 'Now', 'JJMethod': 'GetEv'})
            result.candidates = parse_events(payload, ev, self.keywords)
            result.notes.append('current_listing_records=' + str(len(payload['Data'])))
        except CollectionError as e:
            result.error(ENDPOINT, e)
        result.notes.append('Official current activity listing; no historical/full-museum coverage claim. Chinese/sign-language tours are not Taiwanese tours.')
        return result
