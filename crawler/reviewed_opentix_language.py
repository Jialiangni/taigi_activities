"""AI-reviewed program language evidence, bound to the complete program prose.

This supplements labelled-language rules; it does not bypass session, change,
ticket, source agreement, or editorial checks.
"""
import json
from pathlib import Path
from .candidate_triage import digest
from .collection import plain


def content(program, group):
    return '\n'.join([program['name'], plain(program.get('description')),
                      plain(group.get('eventNoteContent'))])


def validate(claim, program, group):
    text = content(program, group)
    selected = claim.get('session_ids')
    if selected is not None and (not isinstance(selected, list) or not selected
            or any(s not in {str(e['id']) for e in group['events']} for s in selected)):
        return False
    return (claim.get('origin') == 'reviewed_program'
            and claim.get('program_id') == str(program['id'])
            and claim.get('group_id') == str(group['id'])
            and claim.get('content_sha256') == digest(text)
            and bool(claim.get('quote')) and claim['quote'] in text
            and bool(claim.get('rationale')) and bool(claim.get('reviewed_at')))


def notice_valid(claim, program, session_id):
    return (claim.get('origin') == 'reviewed_program'
            and session_id in claim.get('session_ids', [])
            and claim.get('change_notice_sha256') == digest(plain(program.get('changeNotification')))
            and bool(claim.get('change_notice_rationale')))


def claims(root, program, group, session_id=None):
    path = Path(root) / 'data/reviewed_opentix_language.json'
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if data.get('schema_version') != 1:
        raise ValueError('Invalid reviewed OPENTIX language version')
    return [c for c in data['claims'] if validate(c, program, group)
            and ('session_ids' not in c or session_id in c['session_ids'])]
