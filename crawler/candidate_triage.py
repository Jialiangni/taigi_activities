"""Evidence-bound dispositions for reviewed discovery candidates, never publication.

An exclusion applies only to the same identity AND the same official content.
Changed evidence reopens the candidate; fetch failures cannot certify an exclusion.
"""
import hashlib
import json
import re
from pathlib import Path

from .collection import CollectionError, Document, plain

PATH = 'data/reviewed_candidate_decisions.json'
REASONS = {'expired', 'not_event', 'outside_region', 'not_taigi',
           'already_covered', 'resource_only', 'irrelevant_keyword'}


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def document(body, url, version=1):
    if type(version) is not int or version not in (1, 2):
        raise ValueError('Unsupported disposition document version')
    text = _document(body, url)
    if version == 2:
        from urllib.parse import urlsplit
        # These sites include live visitor counters in the visible document.
        # Preserve all announcement text, dates and limits; remove only the
        # numeric value of their explicitly labelled page-view counters.
        if urlsplit(url).hostname in {
                'www.ceramics.ntpc.gov.tw', 'www.xzcac.ntpc.gov.tw',
                'www.gep.ntpc.gov.tw', 'www.tapo.gov.taipei'}:
            text = re.sub(r'((?:瀏覽人次|點閱數)\s*[:：]\s*)[0-9][0-9,]*',
                          r'\1[page views]', text)
    return text


def _document(body, url):
    if url.startswith('https://cloud.culture.tw/frontsite/trans/SearchShowAction.do'):
        return json.dumps(json.loads(body), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    if url.startswith('https://csm.api.opentix.life/programs/'):
        p = json.loads(body)['result']
        # Keep sessions and changes; a newly added session must reopen the case.
        return json.dumps(p, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    d = Document(body)
    if url.startswith('https://taigiloo.tw/') and not d.content().strip():
        # Article-index pages have a heading outside an empty entry-content.
        # Preserve that visible main section, rather than hashing an empty page.
        nodes = [n for n in d.root.all('div') if n.attrs.get('id') == 'content']
        if len(nodes) == 1:
            text = nodes[0].text() + ' ' + ' '.join(
                n.attrs.get('src', '') + ' ' + n.attrs.get('href', '') for n in nodes[0].all())
            return re.sub(r'\s+', ' ', text).strip()
    if url.startswith('https://www.xizhi.ntpc.gov.tw/home.jsp'):
        nodes = [n for n in d.root.all('div') if n.attrs.get('id') == 'home_content']
        if len(nodes) == 1:
            text = nodes[0].text() + ' ' + ' '.join(
                n.attrs.get('src', '') + ' ' + n.attrs.get('href', '') for n in nodes[0].all())
            return re.sub(r'\s+', ' ', text).strip()
    if 'www.tgb.org.tw/' in url:
        nodes = [n for n in d.root.all('div') if n.has_class('post-body')]
        if len(nodes) == 1:
            # Include media/link identity even for video-only announcements.
            titles = [n.text() for n in d.root.all() if n.has_class('post-title')]
            text = ' '.join(titles) + ' ' + nodes[0].text() + ' ' + ' '.join(
                n.attrs.get('src', '') + ' ' + n.attrs.get('href', '')
                for n in nodes[0].all())
            return re.sub(r'\s+', ' ', text).strip()
    if url.startswith('https://www.accupass.com/event/'):
        from .sources.accupass import event_jsonld, activity_intro
        events = list(event_jsonld(d))
        if len(events) == 1:
            return (json.dumps(events[0], ensure_ascii=False, sort_keys=True, separators=(',', ':'))
                    + '\n' + re.sub(r'\s+', ' ', activity_intro(events[0], d)).strip())
    return re.sub(r'\s+', ' ', d.content()).strip()


def evidence_url(candidate):
    url = candidate['source_url']
    if candidate['source_id'] == 'opentix':
        return 'https://csm.api.opentix.life/programs/' + url.rsplit('/', 1)[-1]
    return url


def validate(row):
    version = row.get('document_version', 1)
    if type(version) is not int or version not in (1, 2):
        raise ValueError('Unsupported disposition document version')
    required = ('candidate_id', 'source_id', 'source_url', 'title', 'reason',
                'rationale', 'reviewed_at', 'evidence_url', 'content_sha256', 'quotes')
    if not all(row.get(k) for k in required) or row['reason'] not in REASONS:
        raise ValueError('Incomplete candidate disposition')
    if not re.fullmatch(r'[a-f0-9]{64}', row['content_sha256']):
        raise ValueError('Invalid disposition evidence hash')
    if not isinstance(row['quotes'], list) or not all(isinstance(q, str) and q.strip() for q in row['quotes']):
        raise ValueError('Disposition needs actual source quotes')


def load(root):
    path = Path(root) / PATH
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if data.get('schema_version') != 1:
        raise ValueError('Invalid disposition version')
    result = {}
    for row in data['decisions']:
        validate(row)
        key = (row['source_id'], row['candidate_id'])
        if key in result:
            raise ValueError('Duplicate disposition identity')
        result[key] = row
    return result


def matches(row, candidate, client):
    if not all(row[k] == candidate[k] for k in ('source_id', 'source_url', 'title')):
        return False
    if row['candidate_id'] != candidate['id']:
        return False
    archived_html = row.get('evidence_kind') == 'opentix_archived_html'
    if archived_html:
        # Archived programs can retain a dated notice in HTML after the API
        # returns 400. Never turn an arbitrary API/network failure into closure.
        if (candidate['source_id'] != 'opentix' or row['reason'] != 'expired'
                or not re.fullmatch(r'https://www\.opentix\.life/event/\d+', candidate['source_url'])
                or row['evidence_url'] != candidate['source_url']):
            return False
        try:
            client.get(evidence_url(candidate))
        except CollectionError as error:
            if error.code != 'http_400':
                raise
        else:
            # An API restored with new sessions requires a new review.
            return False
    elif row['evidence_url'] != evidence_url(candidate):
        return False
    body, ev = client.get(row['evidence_url'])
    if ev['final_url'] != row['evidence_url']:
        return False
    content = document(body, row['evidence_url'], row.get('document_version', 1))
    if archived_html and ('本節目已下架' not in content or candidate['title'] not in content):
        return False
    from .reviewed_supporting_evidence import valid as supporting_valid
    return (digest(content) == row['content_sha256']
            and all(q in content for q in row['quotes'])
            and supporting_valid(row.get('supporting_evidence'), client))
