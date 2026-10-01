"""Portable checks for TW-Hokkien translation lineage, not language scoring."""
import hashlib
import re

PROVIDER = 'tw-hokkien'
MODEL = 'Taigi-Llama-2-Translator-13B:latest'
FIELDS = ('summary_taigi', 'description_taigi')
RULE = 'free-admission-mian-tsinn'


def text_hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def protected_spans(text, activity, literals=()):
    names = list(literals) + [activity.get(k) for k in
        ('title', 'organizer', 'venue', 'address', 'source_url', 'registration_url')]
    return [(m.start(), m.end()) for name in names if isinstance(name, str) and name
            for m in re.finditer(re.escape(name), text)]


def terminology_edits(text, activity, literals=()):
    protected = protected_spans(text, activity, literals)
    return [{'start': m.start(), 'end': m.end(), 'source': '免費', 'replacement': '免錢', 'rule_id': RULE}
            for m in re.finditer('免費', text)
            if not any(m.start() < end and m.end() > start for start, end in protected)]


def apply_edits(text, edits, activity, literals=()):
    if not isinstance(edits, list) or len(edits) > 100:
        raise ValueError('Invalid terminology edits')
    protected = protected_spans(text, activity, literals)
    previous = 0
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {'start', 'end', 'source', 'replacement', 'rule_id'}:
            raise ValueError('Invalid terminology edit')
        start, end = edit['start'], edit['end']
        if (type(start) is not int or type(end) is not int or not previous <= start < end <= len(text)
                or edit['source'] != '免費' or edit['replacement'] != '免錢' or edit['rule_id'] != RULE
                or text[start:end] != '免費'
                or any(start < b and end > a for a, b in protected)):
            raise ValueError('Unapproved terminology change or protected name')
        previous = end
    for edit in reversed(edits):
        text = text[:edit['start']] + edit['replacement'] + text[edit['end']:]
    return text


def validate_translation(result, activity):
    if result['editor'] != {'provider': PROVIDER, 'model': MODEL}:
        raise ValueError('TW-Hokkien model/provider mismatch')
    data = result['translation']
    if not isinstance(data, dict) or set(data) != {'model', 'model_digest', 'fields'} or data['model'] != MODEL:
        raise ValueError('Missing translation provenance')
    if not isinstance(data['model_digest'], str) or not re.fullmatch('[0-9a-f]{64}', data['model_digest']):
        raise ValueError('Missing model digest')
    if not isinstance(data['fields'], dict) or set(data['fields']) != set(FIELDS):
        raise ValueError('Missing translated field')
    for field in FIELDS:
        record = data['fields'][field]
        if not isinstance(record, dict) or set(record) != {
                'verified_translation', 'input_sha256', 'report_sha256', 'output_sha256',
                'cli_verified', 'protected_literals', 'user_overrides'}:
            raise ValueError('Invalid field provenance')
        original = record['verified_translation']
        if not isinstance(original, str) or not 1 <= len(original) <= 8000 or record['cli_verified'] is not True:
            raise ValueError('Missing CLI-verified translation')
        if (not isinstance(record['protected_literals'], list) or len(record['protected_literals']) > 200
                or any(not isinstance(s, str) or not s or len(s) > 2000 for s in record['protected_literals'])):
            raise ValueError('Invalid protected literals')
        for key in ('input_sha256', 'report_sha256', 'output_sha256'):
            if not isinstance(record[key], str) or not re.fullmatch('[0-9a-f]{64}', record[key]):
                raise ValueError('Missing translation hash')
        expected = apply_edits(original, record['user_overrides'], activity, record['protected_literals'])
        if result[field] != expected or text_hash(expected) != record['output_sha256']:
            raise ValueError('Translation changed beyond authorized user terminology')
    if result['review']['natural_taiwanese'] is not False:
        raise ValueError('Model acceptance must not claim an independent naturalness review')
