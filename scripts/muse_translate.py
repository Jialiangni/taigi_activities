"""Translate through Muse Code's authenticated Meta API transport, without GUI."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.meta_translate import MODEL, INSTRUCTIONS, digest, payload, save

CLI = Path.home() / '.local/bin/muse'


def extract_events(raw, prompt):
    events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    def selected(kind):
        return [e['payload'] for e in events if e.get('payload_type') == kind]
    terminal = selected('run.terminal.completed')
    models = selected('run.model.configured')
    inputs = selected('turn.input.user')
    if (len(terminal) != 1 or len(models) != 1 or len(inputs) != 1
            or terminal[0].get('terminal') != 'completed'
            or models[0].get('model_id') != MODEL or models[0].get('provider_id') != 'meta'
            or inputs[0].get('prompt') != prompt):
        raise ValueError('Incomplete, mismatched or ambiguous Muse run')
    run = terminal[0]['command_id']
    if any(p.get('command_id') != run for p in [models[0], inputs[0]]):
        raise ValueError('Mixed Muse run IDs')
    if any(e.get('payload_type', '').startswith(('tool.', 'run.terminal.failed', 'run.terminal.cancelled')) for e in events):
        raise ValueError('Tool use or failed run cannot be accepted as translation')
    text = terminal[0].get('text')
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Empty Muse reply')
    return text, run


def verify(output):
    output = Path(output)
    report = json.loads(Path(str(output) + '.translation.json').read_text())
    folder = Path(str(output) + '.audit')
    raw = (folder / 'events.jsonl').read_text()
    prompt = (folder / 'prompt.txt').read_text()
    text, run = extract_events(raw, prompt)
    expected = make_prompt(report['source'], report['protected_literals'])
    if (report.get('status') != 'ready' or report.get('model') != MODEL
            or report.get('transport') != 'muse-code' or report.get('run_id') != run
            or report.get('language_rewritten_by_codex') is not False
            or report.get('source_sha256') != digest(report['source'])
            or prompt != expected or report.get('events_sha256') != digest(raw)
            or report.get('translation') != text or output.read_text() != text
            or report.get('translation_sha256') != digest(text)
            or not all(s in text for s in report['protected_literals'])):
        raise ValueError('Translation evidence mismatch')
    return {'ok': True, 'model': MODEL, 'run_id': run, 'language_rewritten_by_codex': False}


def make_prompt(source, facts):
    body = payload(source, facts)  # Validates source and protected literals.
    return body['instructions'] + '\n不要使用工具、讀寫檔案或上網。\n\n原文：\n' + source


def translate(source, facts, output, cli=CLI):
    output = Path(output).resolve()
    prompt = make_prompt(source, facts)
    folder = Path(str(output) + '.audit')
    report_path = Path(str(output) + '.translation.json')
    if output.exists() or report_path.exists():
        check = verify(output)
        old = json.loads(report_path.read_text())
        if old['source'] != source or old['protected_literals'] != facts:
            raise ValueError('Existing translation belongs to another input')
        return dict(check, reused=True)
    folder.mkdir(parents=True, exist_ok=False)
    os.chmod(folder, 0o700)
    (folder / 'prompt.txt').write_text(prompt)
    (folder / 'source.txt').write_text(source)
    report = {'schema_version': 1, 'status': 'submitting', 'model': MODEL, 'transport': 'muse-code',
              'source': source, 'source_sha256': digest(source), 'protected_literals': facts,
              'started_at': datetime.now(timezone.utc).isoformat(),
              'language_rewritten_by_codex': False, 'independent_naturalness_review': False}
    save(report_path, report)
    try:
        version = subprocess.run([str(cli), '--version'], capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        report['cli_version'] = version
        args = [str(cli), 'exec', '--model', MODEL, '--reasoning-effort', 'low', '--json',
                '--prompt-file', str(folder / 'prompt.txt'), '--workspace', str(folder),
                '--disable-shell', '--disable-write', '--disable-web-tools',
                '--no-foreign-personal-context', '--no-session-log', '--max-model-steps', '1']
        with (folder / 'events.jsonl').open('w') as out, (folder / 'stderr.txt').open('w') as err:
            process = subprocess.Popen(args, cwd=folder, stdout=out, stderr=err, start_new_session=True)
            try:
                code = process.wait(timeout=120)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                raise ValueError('Muse timed out; no automatic resubmission') from None
        if code:
            raise ValueError('Muse failed; see local audit/stderr.txt; no automatic resubmission')
        raw = (folder / 'events.jsonl').read_text()
        text, run = extract_events(raw, prompt)
        # This is a fixed-data check, not a semantic or naturalness assessment.
        report.update(run_id=run, translation=text, translation_sha256=digest(text),
                      events_sha256=digest(raw), missing_literals=[s for s in facts if s not in text])
        report['status'] = 'needs_fact_review' if report['missing_literals'] else 'ready'
        target = Path(str(output) + '.draft.txt') if report['missing_literals'] else output
        target.write_text(text)
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__)
        if isinstance(exc, ValueError):
            report['error'] = str(exc)
        raise
    finally:
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        save(report_path, report)
    return report


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--facts', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    try:
        if args.verify:
            result = verify(args.verify)
        else:
            if not all((args.input, args.facts, args.output)):
                parser.error('--input, --facts and --output are required')
            result = translate(args.input.read_text(), json.loads(args.facts.read_text()), args.output)
        print(json.dumps({k: v for k, v in result.items() if k not in ('source', 'translation')}, ensure_ascii=False))
        return 3 if result.get('status') == 'needs_fact_review' else 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
