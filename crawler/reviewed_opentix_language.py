"""AI-reviewed program language evidence, bound to the complete program prose.

This supplements labelled-language rules; it does not bypass session, change,
ticket, source agreement, or editorial checks.
"""
import json
from datetime import datetime
from pathlib import Path
from .candidate_triage import digest
from .collection import plain, TAIPEI


def omits_end(claim, session):
    """An explicit, session-bound conflict may omit an end, never invent one."""
    return (claim.get('origin') == 'reviewed_program'
            and session.get('session_id') in claim.get('session_ids', [])
            and any(r.get('session_id') == session.get('session_id')
                    and r.get('start_time') == session.get('start_time')
                    and r.get('api_end_time') == session.get('end_time')
                    and r.get('quote') and r.get('rationale')
                    for r in claim.get('end_time_conflicts', [])))


def content(program, group):
    return '\n'.join([program['name'], plain(program.get('description')),
                      plain(group.get('eventNoteContent'))])


def validate(claim, program, group, client=None):
    text = content(program, group)
    selected = claim.get('session_ids')
    if selected is not None and (not isinstance(selected, list) or not selected
            or any(s not in {str(e['id']) for e in group['events']} for s in selected)):
        return False
    conflicts = claim.get('end_time_conflicts', [])
    if not isinstance(conflicts, list):
        return False
    for row in conflicts:
        if not isinstance(row, dict) or row.get('quote', '') not in text or not row.get('quote'):
            return False
        event = next((e for e in group['events'] if str(e['id']) == row.get('session_id')), None)
        if not event or not omits_end(claim, {
                'session_id': str(event['id']),
                'start_time': datetime.fromtimestamp(event['startDateTime'], TAIPEI).isoformat(),
                'end_time': datetime.fromtimestamp(event['endDateTime'], TAIPEI).isoformat()}):
            return False
    context = claim.get('context_quotes', [])
    if (not isinstance(context, list) or any(not isinstance(q, str) or not q
            or not any(q in r.get('quotes', []) for r in claim.get('supporting_evidence', []))
            for q in context)):
        return False
    from .reviewed_supporting_evidence import valid as supporting_valid
    return (claim.get('origin') == 'reviewed_program'
            and claim.get('program_id') == str(program['id'])
            and claim.get('group_id') == str(group['id'])
            and claim.get('content_sha256') == digest(text)
            and bool(claim.get('quote')) and claim['quote'] in text
            and bool(claim.get('rationale')) and bool(claim.get('reviewed_at'))
            and (not claim.get('supporting_evidence') or selected is not None)
            and supporting_valid(claim.get('supporting_evidence'), client))


def notice_valid(claim, program, session_id):
    return (claim.get('origin') == 'reviewed_program'
            and session_id in claim.get('session_ids', [])
            and claim.get('change_notice_sha256') == digest(plain(program.get('changeNotification')))
            and bool(claim.get('change_notice_rationale')))


def claims(root, program, group, session_id=None, client=None):
    path = Path(root) / 'data/reviewed_opentix_language.json'
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if data.get('schema_version') != 1:
        raise ValueError('Invalid reviewed OPENTIX language version')
    return [c for c in data['claims']
            if ('session_ids' not in c or session_id in c['session_ids'])
            and validate(c, program, group, client)]
