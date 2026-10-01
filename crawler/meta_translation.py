"""Checks for Muse API lineage and authorized terminology, not language scoring."""
import re
from .tw_hokkien import FIELDS, apply_edits, text_hash

PROVIDER = 'meta-model-api'
MODEL = 'muse-spark-1.3'


def validate_translation(result, activity):
    if result['editor'] != {'provider': PROVIDER, 'model': MODEL}:
        raise ValueError('Meta model/provider mismatch')
    data = result['translation']
    if (not isinstance(data, dict) or set(data) != {'model', 'transport', 'fields'}
            or data['model'] != MODEL or data['transport'] != 'muse-code'
            or not isinstance(data['fields'], dict) or set(data['fields']) != set(FIELDS)):
        raise ValueError('Missing Meta translation provenance')
    for field in FIELDS:
        record = data['fields'][field]
        if not isinstance(record, dict) or set(record) != {
                'verified_translation', 'input_sha256', 'report_sha256', 'output_sha256',
                'artifact_verified', 'run_id', 'protected_literals', 'user_overrides'}:
            raise ValueError('Invalid Meta field provenance')
        original = record['verified_translation']
        if (not isinstance(original, str) or not 1 <= len(original) <= 8000
                or record['artifact_verified'] is not True
                or not isinstance(record['run_id'], str)
                or not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', record['run_id'])):
            raise ValueError('Missing verified Muse run')
        literals = record['protected_literals']
        if (not isinstance(literals, list) or len(literals) > 200
                or any(not isinstance(s, str) or not s or len(s) > 2000 or s not in original for s in literals)):
            raise ValueError('Invalid or missing protected literals')
        for key in ('input_sha256', 'report_sha256', 'output_sha256'):
            if not isinstance(record[key], str) or not re.fullmatch('[0-9a-f]{64}', record[key]):
                raise ValueError('Missing Meta translation hash')
        expected = apply_edits(original, record['user_overrides'], activity, literals)
        if result[field] != expected or text_hash(expected) != record['output_sha256']:
            raise ValueError('Translation changed beyond authorized user terminology')
    if result['review']['natural_taiwanese'] is not False:
        raise ValueError('Model acceptance is not an independent naturalness review')
