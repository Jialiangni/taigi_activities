"""Create or update one GitHub Issue containing Facebook candidates needing a person."""
import json
import os
import re
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

TITLE = '待判讀：Facebook 活動候選'


def clean(value, limit=180):
    value = re.sub(r'[\r\n\t]+', ' ', str(value or '')).strip()
    return value[:limit]


def pending_rows(audit):
    return [row for row in audit.get('decisions', [])
            if row.get('source_id') == 'facebook_review' and row.get('decision') == 'pending']


def build_body(audit, run_url=''):
    rows = pending_rows(audit)
    lines = [
        '<!-- taigi-facebook-manual-review -->',
        'Facebook 分級判讀後，以下候選仍缺少足以自動刊登的官方證據。',
        '',
        '- 待判讀：**{} 筆**'.format(len(rows)),
        '- 自動產生時間：{}'.format(clean(audit.get('reviewed_at'))),
    ]
    if run_url:
        lines.append('- [查看本次 GitHub Actions]({})'.format(run_url))
    lines.extend(['', '回覆時可直接寫：`排除 <候選 ID> 原因`、`保留待查 <候選 ID>`，或提供官方活動連結。', ''])
    for number, row in enumerate(rows, 1):
        context = row.get('review_context') or {}
        draft = context.get('draft') or {}
        lines.extend([
            '### {}. {}'.format(number, clean(row.get('title'))),
            '- 候選 ID：`{}`'.format(clean(row.get('candidate_id'), 64)),
            '- 粉專：{}'.format(clean(context.get('page_handle')) or '未識別'),
            '- [Facebook 原貼文]({})'.format(row.get('source_url')),
            '- 需要人工原因：`{}`'.format(clean(row.get('reason'))),
        ])
        links = context.get('discovered_links') or []
        if links:
            lines.append('- 找到的連結：')
            for link in links[:10]:
                trust = '粉專本人' if link.get('is_page_author') is True else '作者未確認'
                lines.append('  - [{}]({})（{}）'.format(clean(link.get('url'), 120), link.get('url'), trust))
        else:
            lines.append('- 找到的連結：無')
        missing = draft.get('unverified_fields') or []
        lines.append('- 尚未核實：{}'.format('、'.join(clean(x, 40) for x in missing) or '活動內容'))
        excerpt = clean(context.get('post_excerpt'), 400)
        if excerpt:
            lines.append('- 粉專摘錄：{}'.format(excerpt))
        lines.append('')
    return '\n'.join(lines).strip() + '\n'


def api(repository, token, method, path, payload=None):
    url = 'https://api.github.com/repos/{}/{}'.format(repository, path)
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(url, data=data, method=method, headers={
        'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
        'User-Agent': 'TaigiActivities-review-reminder', 'X-GitHub-Api-Version': '2022-11-28'})
    context = ssl.create_default_context()
    with urlopen(request, timeout=30, context=context) as response:
        return json.loads(response.read())


def main():
    audit = json.loads(Path(os.environ.get('REVIEW_AUDIT', 'data/audit/latest-candidate-review.json')).read_text())
    repository, token = os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_TOKEN']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid repository')
    issues = api(repository, token, 'GET', 'issues?state=open&per_page=100')
    issue = next((row for row in issues if row.get('title') == TITLE and 'pull_request' not in row), None)
    rows = pending_rows(audit)
    if rows:
        payload = {'title': TITLE, 'body': build_body(audit, os.environ.get('GITHUB_RUN_URL', ''))}
        if issue:
            api(repository, token, 'PATCH', 'issues/' + str(issue['number']), payload)
            print('Updated manual review issue #{}'.format(issue['number']))
        else:
            created = api(repository, token, 'POST', 'issues', payload)
            print('Created manual review issue #{}'.format(created['number']))
    elif issue:
        api(repository, token, 'PATCH', 'issues/' + str(issue['number']), {
            'state': 'closed', 'state_reason': 'completed',
            'body': build_body(audit, os.environ.get('GITHUB_RUN_URL', '')) + '\n目前沒有待人工判讀的 Facebook 候選。\n'})
        print('Closed manual review issue #{}'.format(issue['number']))
    else:
        print('No Facebook candidates need manual review')


if __name__ == '__main__':
    main()
