"""Extract complete labelled session blocks, keeping their individual places and teachers."""
import hashlib
import re
from datetime import datetime
from ..collection import Document, local_time, city_of

DATE = re.compile(r'(?<![\d/])(?P<m>\d{1,2})/(?P<d>\d{1,2})\s*[（(](?P<w>[一二三四五六日天])[）)]\s*(?P<a>\d{1,2}:\d{2})\s*[–－~～-]\s*(?P<b>\d{1,2}:\d{2})')
LABELS = {'主題':'session_title','講師':'performer','內容':'content','地點':'venue','地址':'address'}


def lines(node):
    if isinstance(node, str):
        return node
    if node.tag == 'br':
        return '\n'
    text = ''.join(lines(c) for c in node.children)
    return text + ('\n' if node.tag in ('p','li','h2','h3','h4','div') else '')


def block_schedule(html, event):
    articles = [n for n in Document(html).root.all('article')
                if 'EventContent_event-content__' in n.attrs.get('class','')]
    if len(articles) != 1:
        return [], ''
    text = lines(articles[0])
    if not all(label+'：' in text for label in ('主題','內容','地點','地址')):
        return [], ''
    matches = list(DATE.finditer(text))
    if not matches:
        return [], 'labelled_schedule_dates_missing'
    if len(matches) != len(re.findall(r'(?:^|\n)\s*主題[：:]',text)):
        return [], 'labelled_schedule_incomplete_dates'
    start, end = local_time(event.get('startDate')), local_time(event.get('endDate'))
    if not start or not end or start[:4] != end[:4]:
        return [], 'labelled_schedule_year_ambiguous'
    rows, context = [], ''
    for index, m in enumerate(matches):
        before = text[matches[index-1].end() if index else 0:m.start()]
        headings = re.findall(r'([^\n]{0,60}[AB]班[^\n]*)', before)
        if headings:
            context = headings[-1].strip()
        block = text[m.end():matches[index+1].start() if index+1<len(matches) else len(text)]
        fields = {}
        for line in block.splitlines():
            line = line.strip()
            found = re.fullmatch(r'(主題|講師|內容|地點|地址)[：:]\s*(.+)', line)
            if found:
                key = LABELS[found[1]]
                if key in fields:
                    return [], 'labelled_schedule_duplicate_field'
                fields[key] = found[2].strip()
        if 'performer' not in fields:
            teacher = re.search(r'[（(]\s*([^()（）]+老師)\s*[）)]', context)
            if teacher:
                fields['performer'] = teacher[1].strip()
        if any(not fields.get(k) for k in LABELS.values()):
            return [], 'labelled_schedule_incomplete_fields'
        try:
            day = datetime(int(start[:4]), int(m['m']), int(m['d']))
            a = local_time(day.strftime('%Y-%m-%dT')+m['a'].zfill(5)+':00+08:00')
            b = local_time(day.strftime('%Y-%m-%dT')+m['b'].zfill(5)+':00+08:00')
        except ValueError:
            return [], 'labelled_schedule_invalid_date'
        if not a or not b or a >= b or not start[:10] <= a[:10] <= end[:10]:
            return [], 'labelled_schedule_outside_dates_or_reversed'
        if '一二三四五六日'[day.weekday()] != m['w'].replace('天','日'):
            return [], 'labelled_schedule_weekday_mismatch'
        identity = '|'.join([a, fields['venue'],fields['session_title'],fields['performer']])
        key = hashlib.sha256(identity.encode()).hexdigest()[:12]
        if any(r['session_key'] == key for r in rows):
            return [], 'labelled_schedule_duplicate_session'
        fields.update(start_time=a,end_time=b,city=city_of(fields['address']),context=context,
                      session_key=key,date_quote=m.group(0))
        rows.append(fields)
    return rows, ''
