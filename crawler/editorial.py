"""Source-grounded directory introductions and exact-text Taiwanese editions."""
import hashlib
import json
import re
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'data/directory_editorial.json'
CONFLICT_ZH = '報名表的結束時間有不同記載，僅列確定的開始時間，結束時間請向主辦確認。'
CONFLICT_TAIGI = '報名表的結束時間有無仝的記載，這頁干焦列確定的開始時間；結束時間請問主辦單位。'


def text_hash(text):
    return hashlib.sha256(re.sub(r'\s+', '', text).encode('utf-8')).hexdigest()


def editions():
    return json.loads(PATH.read_text(encoding='utf-8')) if PATH.exists() else []


def official_introduction(body, title=''):
    """Keep actual announcement prose, never replace it with a directory slogan."""
    lines = []
    for line in body.splitlines():
        line = re.sub(r'https?://\S+', '', line).strip(' \u200b\u2800📌📣👉🔸🌟❤️＊*｜')
        if len(line) < 10 or line == title or re.match(r'^(?:時間|日期|地點|場館|地址|報名|活動時間|活動地址|https?)[：:｜ ]', line):
            continue
        if re.search(r'加入.*(?:LINE|Line)|傳送貼圖|更多活動資訊|記得關注|報名由此去', line):
            continue
        if line not in lines:
            lines.append(line)
    text = '\n'.join(lines)
    if len(text) > 1400:
        boundary = max(text.rfind('。', 0, 1400), text.rfind('\n', 0, 1400))
        text = text[:boundary + 1] if boundary >= 0 else text[:1400]
    return text or body.strip() or title


def directory_introduction(parsed, session):
    for entry in editions():
        if (entry['source_url'] == parsed['source_url']
                and session['start_time'] in entry['sessions']
                and entry['body_sha256'] == text_hash(parsed['text'])):
            return dict(entry)
    description = official_introduction(parsed['text'], parsed['title'])
    return {'description': description, 'source_quotes': description.splitlines()}


def display_summary(description, translation):
    for entry in editions():
        if entry['description'] == description and entry['description_taigi'] == translation:
            return entry['summary_taigi']
    return translation or ''
