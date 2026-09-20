"""Portable read-only lookup; parser shared with the local Taiwanese skill."""
import re
import unicodedata
from urllib.parse import quote
from .collection import Client, CollectionError

def clean(value):
    if not isinstance(value, str):
        raise ValueError('Expected text')
    return unicodedata.normalize('NFC', re.sub(r'`([^~]*)~', r'\1', value))


def parse_entry(data, word):
    if not isinstance(data, dict) or not isinstance(data.get('t'), str):
        raise ValueError('Missing title')
    hs = data.get('h')
    if not isinstance(hs, list) or not hs:
        raise ValueError('Missing readings')
    title = clean(data['t'])
    if title != word:
        raise ValueError('Returned headword does not match query')
    readings = []
    for h in hs:
        if not isinstance(h, dict) or not isinstance(h.get('T'), str) or not h['T'].strip():
            raise ValueError('Missing Taiwanese romanization')
        if not isinstance(h.get('d'), list):
            raise ValueError('Missing definitions array')
        definitions = []
        for d in h['d']:
            if not isinstance(d, dict) or not isinstance(d.get('f'), str):
                raise ValueError('Invalid definition')
            examples = d.get('e', [])
            if not isinstance(examples, list):
                raise ValueError('Invalid examples')
            parsed_examples = []
            for example in examples:
                example = clean(example)
                parts = re.fullmatch('￹(.*?)￺(.*?)￻(.*)', example, re.DOTALL)
                parsed_examples.append(dict(zip(['taiwanese', 'tailo', 'mandarin'], parts.groups())) if parts else {'text': example})
            definitions.append({'meaning_zh': clean(d['f']), 'part_of_speech': clean(d.get('type', '')), 'examples': parsed_examples})
        variants = h.get('B', [])
        if not isinstance(variants, list):
            raise ValueError('Invalid variants')
        readings.append({'tailo': clean(h['T']), 'entry_id': str(h.get('_', '')), 'variants': [clean(v) for v in variants], 'definitions': definitions})
    return {'title': title, 'readings': readings}



def lookup_taiwanese(word):
    if not isinstance(word, str) or not 1 <= len(word) <= 64 or any(unicodedata.category(c).startswith('C') for c in word):
        return {'status': 'invalid_input'}
    word = unicodedata.normalize('NFC', word.strip())
    url = 'https://www.moedict.tw/t/' + quote(word, safe='') + '.json'
    result = {'query': word, 'source_url': url,
              'notice': '萌典整理的教育部辭典資料；詞條收錄不等於現行推薦用字認證。'}
    try:
        data, proof = Client(allowed_hosts={'www.moedict.tw'}).json(url)
        return dict(result, status='ok', checked_at=proof['fetched_at'], **parse_entry(data, word))
    except CollectionError as exc:
        return dict(result, status='not_found' if exc.code == 'http_404' else 'service_error')
    except (ValueError, TypeError, KeyError):
        return dict(result, status='invalid_response')
