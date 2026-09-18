"""Reviewed guide/exhibition information without invented calendar sessions."""
import json
import re
from datetime import datetime
from pathlib import Path
from .verified import TAIPEI, detail_url, parse_time, check_live_sources

PATH = Path(__file__).resolve().parents[1] / 'data/verified_resources.json'


def load_resources(path=PATH, now=None, check_sources=False):
    now = now or datetime.now(TAIPEI)
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('schema_version') != 1:
        raise ValueError('不支援的導覽資訊格式')
    rows, ids, sources = [], set(), {}
    for row in data['resources']:
        detail_url(row['url'])
        if row['id'] in ids or row['city'] not in ('臺北市', '新北市', '桃園市'):
            raise ValueError('重複資訊或地區錯誤')
        ids.add(row['id'])
        if row['kind'] not in ('audio_guide', 'reservation_guide', 'exhibition_resource'):
            raise ValueError('導覽資訊類型錯誤')
        if row.get('status') != 'verified' or not all(row.get(k) for k in ('title', 'description', 'language_evidence', 'required_text')):
            raise ValueError('導覽資訊未核實')
        if parse_time(row['checked_at']) > now or not re.fullmatch(r'[a-f0-9]{64}', row['snapshot_sha256']):
            raise ValueError('導覽資訊缺少有效核實紀錄')
        if row.get('expires_at') and parse_time(row['expires_at']) <= now:
            continue
        rows.append(row)
        sources[row['id']] = row
    if check_sources:
        check_live_sources(sources)
    return rows
