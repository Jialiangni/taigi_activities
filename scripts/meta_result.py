"""Package actual Muse API output plus a factual review; never publish."""
import argparse
import json
from pathlib import Path
import sys
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from crawler.ai_editorial import save_json
from crawler.editorial_queue import validate_result, result_name
from crawler.tw_hokkien import FIELDS, RULE, text_hash, terminology_edits, apply_edits
from crawler.meta_translation import MODEL, PROVIDER
from scripts.muse_translate import verify


def local_path(workspace, value):
    path = (workspace / value).resolve()
    if workspace not in path.parents or not path.is_file():
        raise ValueError('Input must be a file inside this batch')
    return path


def package(workspace, plan_path):
    workspace = Path(workspace).resolve()
    bundle = json.loads((workspace / 'input.json').read_text())
    if bundle['provider'] != PROVIDER:
        raise ValueError('Batch is not assigned to Meta Model API')
    terms = json.loads((workspace / 'translation_terminology.json').read_text())
    if not any(p['id'] == RULE and p['source_term'] == '免費' and p['preferred_taigi'] == '免錢'
               for p in terms['preferences']):
        raise ValueError('Missing user terminology policy')
    plan = json.loads(local_path(workspace, plan_path).read_text())
    task = next(t for t in bundle['items'] if t['activity_id'] == plan['activity_id'])
    if task['result_file'] != result_name(dict(task, row={'activity': task['activity']})):
        raise ValueError('Result filename does not match source binding')
    review = json.loads(local_path(workspace, plan['review_file']).read_text())
    fields, prose = {}, {}
    for field in FIELDS:
        path = local_path(workspace, plan['fields'][field])
        report_path = local_path(workspace, str(path) + '.translation.json')
        report = json.loads(report_path.read_text())
        check = verify(path)
        save_json(workspace / 'audit' / (task['activity_id'] + '.' + field + '.verify.json'), check)
        if (report.get('status') != 'ready' or report['model'] != MODEL
                or report.get('language_rewritten_by_codex') is not False):
            raise ValueError('Wrong model or unfinished translation')
        original = path.read_text()
        if original != report['translation'] or text_hash(original) != report['translation_sha256']:
            raise ValueError('Translation/report mismatch')
        if text_hash(report['source']) != report['source_sha256']:
            raise ValueError('Source/report mismatch')
        literals = report.get('protected_literals', [])
        edits = terminology_edits(original, task['activity'], literals)
        prose[field] = apply_edits(original, edits, task['activity'], literals)
        revision = workspace / 'user-revisions' / (task['activity_id'] + '.' + field + '.txt')
        revision.parent.mkdir(exist_ok=True)
        revision.write_text(prose[field])
        fields[field] = {'verified_translation': original, 'input_sha256': report['source_sha256'],
                         'report_sha256': text_hash(report_path.read_text()),
                         'output_sha256': text_hash(prose[field]), 'artifact_verified': True, 'run_id': report['run_id'],
                         'protected_literals': literals, 'user_overrides': edits}
    # Claims describe the delivered copy; official source quotations never change.
    for evidence in review['evidence']:
        if evidence['claim'] not in prose['summary_taigi'] + '\n' + prose['description_taigi']:
            revised = evidence['claim'].replace('免費', '免錢')
            if revised in prose['summary_taigi'] + '\n' + prose['description_taigi']:
                evidence['claim'] = revised
    result = {'schema_version': 3, 'activity_id': task['activity_id'],
              'source_hash': task['source_hash'], 'guide_hash': bundle['guide_hash'],
              **prose, 'uncertain_terms': [], 'dictionary_evidence': [], 'review': review,
              'editor': {'provider': PROVIDER, 'model': MODEL},
              'edited_at': datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
              'translation': {'model': MODEL, 'transport': 'muse-code', 'fields': fields}}
    audit_path = workspace / 'audit' / (task['activity_id'] + '.packaged.json')
    save_json(audit_path, result)
    validate_result(result, dict(task, row={'activity': task['activity']}),
                    (workspace / 'TAIGI_EDITORIAL.md').read_text())
    target = workspace / 'results' / task['result_file']
    if target.resolve().parent != (workspace / 'results').resolve():
        raise ValueError('Invalid result filename')
    save_json(target, result)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    parser.add_argument('--plan', required=True)
    args = parser.parse_args()
    print(package(args.workspace, args.plan))
