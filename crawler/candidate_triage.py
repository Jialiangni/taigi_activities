"""Evidence-bound dispositions for reviewed discovery candidates, never publication.

An exclusion applies only to the same identity AND the same official content.
Changed evidence reopens the candidate; fetch failures cannot certify an exclusion.
"""
import hashlib
import json
import re
from pathlib import Path

from .collection import Document, plain

PATH = 'data/reviewed_candidate_decisions.json'
REASONS = {'expired', 'not_event', 'outside_region', 'not_taigi',
           'already_covered', 'resource_only', 'irrelevant_keyword'}


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def document(body, url):
    if url.startswith('https://cloud.culture.tw/frontsite/trans/SearchShowAction.do'):
        return json.dumps(json.loads(body), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    if url.startswith('https://csm.api.opentix.life/programs/'):
        p = json.loads(body)['result']
        # Keep sessions and changes; a newly added session must reopen the case.
        return json.dumps(p, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    d = Document(body)
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
    if row['candidate_id'] != candidate['id'] or row['evidence_url'] != evidence_url(candidate):
        return False
    body, ev = client.get(row['evidence_url'])
    if ev['final_url'] != row['evidence_url']:
        return False
    content = document(body, row['evidence_url'])
    return (digest(content) == row['content_sha256']
            and all(q in content for q in row['quotes']))
