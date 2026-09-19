"""Google Calendar links and standards-compliant iCalendar export (no API sync)."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode


def utc_stamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Calendar time must include a timezone')
    return dt.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def ics_text(value):
    return str(value).replace('\\', '\\\\').replace('\r\n', '\n').replace('\r', '\n').replace('\n', r'\n').replace(';', r'\;').replace(',', r'\,')


def fold_line(line):
    parts, part = [], ''
    for char in line:
        if len((part + char).encode('utf-8')) > 75:
            parts.append(part)
            part = ' '
        part += char
    parts.append(part)
    return '\r\n'.join(parts)


class GoogleWorkspaceSync:
    APPLE_IMPORT_GUIDE = (
        '【加入 Apple 日曆：兩步驟】\n'
        '第一步：先看預覽，猶未加入日曆。右上角 ✓ 干焦關閉預覽。\n'
        '請按下跤的「Add to Calendar」，進入第二步。\n'
        '第二步：確認日曆，閣按「Add／加入」才完成。\n'
        '這段操作說明會保留佇活動備註。'
    )
    HEADER = ('BEGIN:VCALENDAR\r\nVERSION:2.0\r\n'
              'PRODID:-//Taigi Activities//Verified Calendar//ZH_TW\r\n'
              'CALSCALE:GREGORIAN\r\nMETHOD:PUBLISH\r\n'
              'X-WR-CALNAME:北北桃台語活動行事曆\r\nX-WR-TIMEZONE:Asia/Taipei\r\n')

    def generate_google_calendar_url(self, act):
        start = utc_stamp(act.start_time)
        end = utc_stamp(act.end_time) if act.end_time else start
        return 'https://calendar.google.com/calendar/render?' + urlencode({
            'action': 'TEMPLATE', 'text': act.title, 'dates': f'{start}/{end}',
            'ctz': 'Asia/Taipei', 'details': f'{act.description}\n{act.price_info}\n{act.source_url}',
            'location': ' '.join(filter(None, [act.venue, act.address]))
        })

    @staticmethod
    def single_event_filename(act):
        # Stable, URL-safe names never interpret source IDs as filesystem paths.
        return sha256(act.id.encode('utf-8')).hexdigest() + '.ics'

    def event_content(self, act, preview_help=False):
        stamp = act.raw_metadata.get('verified_at') or datetime.now(timezone.utc).isoformat()
        lines = ['BEGIN:VEVENT', f'UID:{act.id}@taigiactivities.tw',
                 f'DTSTAMP:{utc_stamp(stamp)}', f'DTSTART:{utc_stamp(act.start_time)}']
        if act.end_time:
            lines.append(f'DTEND:{utc_stamp(act.end_time)}')
        description = act.description + chr(10) + act.price_info + chr(10) + act.source_url
        if preview_help:
            description = self.APPLE_IMPORT_GUIDE + '\n\n' + description
        lines.extend([
            f'SUMMARY:{ics_text(act.title)}',
            f'DESCRIPTION:{ics_text(description)}',
            f'LOCATION:{ics_text(" ".join(filter(None, [act.venue, act.address])))}',
            f'URL:{act.source_url}', 'END:VEVENT'
        ])
        return '\r\n'.join(fold_line(line) for line in lines) + '\r\n'

    def export_ics(self, activities, output_path='taigi_activities.ics', preview_help=False):
        content = self.HEADER + ''.join(self.event_content(a, preview_help=preview_help) for a in activities) + 'END:VCALENDAR\r\n'
        Path(output_path).write_bytes(content.encode('utf-8'))
        return str(output_path)

    def sync_to_google_calendar_api(self, activities, calendar_id='primary'):
        raise NotImplementedError('本專案提供 ICS 訂閱與 Google Calendar 加入連結，尚未實作 API 同步')
