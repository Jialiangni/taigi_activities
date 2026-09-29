"""Discover labelled text sessions; classification is not publication approval."""
import re
from datetime import datetime

from ..collection import local_time

MARKER = re.compile(r'20\d{2}/\d{1,2}/\d{1,2}\s*[（(][一二三四五六日天][）)]\s*\d{1,2}:\d{2}')
ROW = re.compile(r'(?P<date>20\d{2}/\d{1,2}/\d{1,2})\s*[（(](?P<weekday>[一二三四五六日天])[）)]\s*'
                 r'(?P<time>\d{1,2}:\d{2})\s*[〖【](?P<title>[^〗】\n]{1,80})[〗】]\s*[-－—]\s*'
                 r'(?P<performer>[^()（）\n]{1,80}?)\s*[（(](?P<approx>約)?(?P<duration>\d{1,3})分鐘[/／]堂[）)]')
CATEGORIES = {'台語劇場': '台語舞台劇', '臺語劇場': '台語舞台劇',
              '台語故事': '台語故事', '臺語故事': '台語故事',
              '台語導覽': '台語導覽', '臺語導覽': '台語導覽'}


def text_schedule(text, event):
    markers, matches = list(MARKER.finditer(text)), list(ROW.finditer(text))
    if not markers:
        return [], ''
    if [m.start() for m in markers] != [m.start() for m in matches]:
        return [], 'incomplete_text_schedule'
    start, end = local_time(event.get('startDate')), local_time(event.get('endDate'))
    if not start or not end:
        return [], 'text_schedule_period_missing'
    rows = []
    for m in matches:
        try:
            day = datetime.strptime(m['date'], '%Y/%m/%d')
            at = datetime.strptime(m['date'] + ' ' + m['time'], '%Y/%m/%d %H:%M').strftime('%Y-%m-%dT%H:%M:00+08:00')
        except ValueError:
            return [], 'invalid_text_schedule_date_time'
        if '一二三四五六日'[day.weekday()] != m['weekday'].replace('天', '日'):
            return [], 'text_schedule_weekday_mismatch'
        if not start <= at < end:
            return [], 'text_schedule_outside_period'
        if any(r['start_time'] == at for r in rows):
            return [], 'duplicate_text_schedule_start'
        if not 0 < int(m['duration']) <= 720:
            return [], 'invalid_text_schedule_duration'
        title = m['title'].strip()
        rows.append({'start_time': at, 'end_time': None, 'session_title': title,
                     'performer': m['performer'].strip(), 'duration_minutes': int(m['duration']),
                     'duration_approximate': bool(m['approx']), 'schedule_quote': m.group(0),
                     'language_classification': 'explicit_taigi_label' if title in CATEGORIES else 'not_established',
                     'category': CATEGORIES.get(title),
                     'language_evidence': title if title in CATEGORIES else None})
    return rows, ''
