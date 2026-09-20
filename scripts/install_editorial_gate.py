"""Install a macOS launchd job that runs Python, not an AI scheduler."""
import argparse
import json
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABEL = 'com.codex.taigi.editorial-gate'


def configuration(base, codex):
    return {'schema_version': 1, 'state_dir': str(base / 'state'), 'batch_size': 5,
            'max_attempts': 2, 'timeout_seconds': 1800,
            'workers': {'codex': {'argv': [str(codex), 'exec', '--ephemeral', '--json',
                '--skip-git-repo-check', '--sandbox', 'workspace-write',
                '-c', 'sandbox_workspace_write.network_access=true',
                '-c', 'approval_policy="never"', '-c', 'forced_login_method="chatgpt"',
                '--cd', '{workspace}', '-']}}}


def launch_agent(base, settings):
    return {'Label': LABEL,
            'ProgramArguments': [sys.executable, str(ROOT / 'scripts/editorial_gate.py'), '--settings', str(settings)],
            'WorkingDirectory': str(ROOT),
            'EnvironmentVariables': {'TZ': 'Asia/Taipei', 'LANG': 'en_US.UTF-8',
                                     'PYTHONUNBUFFERED': '1',
                                     'PATH': '/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin'},
            'StartCalendarInterval': [{'Weekday': day, 'Hour': 8, 'Minute': 0} for day in (2, 5)],
            'RunAtLoad': False,
            'StandardOutPath': str(base / 'gate.log'), 'StandardErrorPath': str(base / 'gate.error.log')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true', help='Write and load the reviewed local configuration')
    args = parser.parse_args()
    base = Path.home() / 'Library/Application Support/TaigiEditorial'
    settings = base / 'runner.json'
    plist = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')
    codex = shutil.which('codex')
    if not codex:
        raise SystemExit('Codex CLI is unavailable')
    config = configuration(base, codex)
    agent = launch_agent(base, settings)
    if not args.install:
        print(json.dumps({'settings_path': str(settings), 'settings': config,
                          'launch_agent_path': str(plist), 'launch_agent': agent}, ensure_ascii=False, indent=2))
        return
    os.umask(0o077)
    base.mkdir(parents=True, exist_ok=True)
    os.chmod(str(base), 0o700)
    # Preserve custom alternative-provider commands on reinstall.
    if not settings.exists():
        settings.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n')
    plist.parent.mkdir(parents=True, exist_ok=True)
    with plist.open('wb') as handle:
        plistlib.dump(agent, handle)
    domain = 'gui/' + str(os.getuid())
    subprocess.run(['launchctl', 'bootout', domain + '/' + LABEL], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['launchctl', 'bootstrap', domain, str(plist)], check=True)
    print('Installed:', LABEL, '(Tuesday/Friday 08:00, system timezone Asia/Taipei)')
    print('Local worker configuration:', settings)


if __name__ == '__main__':
    main()
