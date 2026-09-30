"""Replay editor-reviewed official session evidence through the ordinary editorial queue.

Extraction discovers facts; a reviewed contract selects eligible sessions and terms.
Any change to the official article invalidates the contract before publication.
"""
import json
import re
from pathlib import Path
from .accupass_text_review import digest, require
from .collection import Document, plain, candidate
from .sources.accupass import event_jsonld, activity_intro, parse_event
from .sources.accupass_block_schedule import block_schedule
from .models import Activity

MODE = 'reviewed_session_blocks_v1'


def contracts(root):
    p = Path(root)/'data/reviewed_session_blocks.json'
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    require(data.get('schema_version') == 1, 'reviewed_blocks_version')
    return data['events']


def extract(html, url):
    doc = Document(html)
    events = list(event_jsonld(doc))
    require(len(events) == 1, 'reviewed_blocks_identity_missing')
    event = events[0]
    rows, issue = block_schedule(html,event)
    require(not issue, issue)
    require(rows, 'reviewed_blocks_disappeared')
    live = parse_event(html,url,{})[0]
    return live, rows, plain(event.get('description') or '')


def validate(html, url, contract):
    live, rows, summary = extract(html,url)
    f = live['fields']
    require(live['title'] == contract['title'], 'reviewed_blocks_title_changed')
    require(digest(f['official_summary']) == contract['article_sha256'] and digest(summary) == contract['summary_sha256'],
            'reviewed_blocks_content_changed')
    require(f['event_status'] == 'https://schema.org/EventScheduled', 'reviewed_blocks_event_status')
    text = f['official_summary']+' '+summary
    require(contract['language_quote'] in text, 'reviewed_blocks_language_changed')
    require(all(re.sub(r'\s+','',q) in re.sub(r'\s+','',text) for q in contract['common_quotes']), 'reviewed_blocks_terms_changed')
    require(contract['organizer'] in text, 'reviewed_blocks_organizer_missing')
    for selected in contract['sessions']:
        require(selected['session'] in rows, 'reviewed_blocks_session_changed')
        require(selected['session']['city'] in ('臺北市','新北市','桃園市'), 'outside_region')
    return live


def expand(parent, client, contract):
    url = parent['source_url']
    require(re.fullmatch(r'https://www\.accupass\.com/event/\d+',url), 'reviewed_blocks_url_not_supported')
    html, evidence = client.get(url)
    require(evidence['final_url'] == url, 'official_page_redirected')
    live = validate(html,url,contract)
    require(live['title'] == parent['title'], 'candidate_title_changed')
    children=[]
    for selected in contract['sessions']:
        s=selected['session']
        fields=dict(s, reviewed_block_key=s['session_key'])
        children.append(candidate('accupass',url,parent['title'],live['text'],evidence,fields,'session',
                                  key=url+':block:'+s['session_key']))
    return children


def verify(c, client, contract, now):
    from .verified import parse_time, REVIEWED_FIELDS
    html,evidence=client.get(c['source_url'])
    require(evidence['final_url']==c['source_url'],'official_page_redirected')
    live=validate(html,c['source_url'],contract)
    selected=next((s for s in contract['sessions'] if s['session']['session_key']==c['fields']['reviewed_block_key']),None)
    require(selected is not None,'reviewed_block_not_selected')
    s=selected['session']
    require(parse_time(s['end_time'])>now,'expired')
    description='\n'.join(filter(None,[s['date_quote'],s['context'],'主題：'+s['session_title'],
        '講師：'+s['performer'],'內容：'+s['content'],*contract['common_quotes'],*selected.get('notes',[])]))
    activity=Activity(id='acc_'+c['source_url'].rsplit('/',1)[-1]+'_'+s['start_time'][:10].replace('-','')+'_'+s['start_time'][11:16].replace(':','')+'_'+s['session_key'],
        title=live['title'],description=description,city=s['city'],category=selected['category'],
        start_time=s['start_time'],end_time=s['end_time'],venue=s['venue'],address=s['address'],
        organizer=contract['organizer'],source_platform='Accupass 活動通',source_url=c['source_url'],registration_url=c['source_url'],
        cover_image=live['fields'].get('cover_image',''),is_free=contract['is_free'],price_info=contract['price_info'],
        tags=['台語',s['session_title'],s['performer']],raw_metadata={'session_key':s['session_key']}).to_dict()
    key='block_'+activity['id']
    proof={'mode':MODE,'contract':contract,'session_key':s['session_key'],'activity':activity}
    source={'url':c['source_url'],'title':live['title'],'checked_at':evidence['fetched_at'],'snapshot_sha256':evidence['sha256'],
            'required_text':[live['title'],s['date_quote'],s['session_title'],s['performer'],s['content'],s['venue'],s['address'],*contract['common_quotes']],
            'reviewed_session_blocks':proof}
    row={'activity':activity,'verification':{'status':'verified','source_id':key,'mode':MODE,
         'method':('官方明示免費台語教學系列，完整標籤場次規則核對；發布前重查正文與場次。' if contract.get('review_basis') else 'Codex逐場核對官方主題、講師、時間、地點及參加條件；程式重查完整正文與場次綁定，非人類審定。'),
         'language_evidence':contract['language_quote'],'confirmed_fields':{k:activity[k] for k in REVIEWED_FIELDS}}}
    return key,source,row


def validate_live(source,html):
    proof=source['reviewed_session_blocks']
    validate(html,source['url'],proof['contract'])
    require(any(s['session']['session_key']==proof['session_key'] for s in proof['contract']['sessions']), 'reviewed_block_not_selected')


def automatic_contract(html, url):
    """Accept complete, explicitly free Taigi teaching series; ambiguous terms remain pending."""
    doc=Document(html)
    events=list(event_jsonld(doc))
    if len(events)!=1:
        return None
    e=events[0]
    rows,issue=block_schedule(html,e)
    if not rows or issue:
        return None
    article=activity_intro(e,doc); summary=plain(e.get('description') or '')
    title=e.get('name','')
    if not re.search(r'[台臺]語(?:說故事|主題)系列(?:課程|講座)',title):
        return None
    language=next((q for q in ('一起聽故事、講台語','免費台語主題講座') if q in summary),None)
    if not language or not re.search(r'活動全程免費|免費台語主題講座',summary):
        return None
    if re.search(r'取消|延期|改期|另收|另計|自付|(?:材料費|報名費|入場費|票價)\s*[：:]?\s*\d|非[台臺]語|華語場|英語場',article+' '+summary):
        return None
    if any(str(o.get('price')) not in ('None','0','0.0','0.00') for o in (e.get('offers') or []) if isinstance(o,dict)):
        return None
    f=parse_event(html,url,{})[0]['fields']
    if f['event_status']!='https://schema.org/EventScheduled' or not f.get('organizer') or f['organizer'] not in article:
        return None
    # Keep all common participation instructions and the exact original footer.
    from .sources.accupass_block_schedule import lines,DATE
    a=next(n for n in doc.root.all('article') if 'EventContent_event-content__' in n.attrs.get('class',''))
    body=lines(a);matches=list(DATE.finditer(body))
    prefix=body[:matches[0].start()].strip()
    last=body[matches[-1].end():]
    address=re.search(r'地址[：:]\s*[^\n]+',last)
    footer=last[address.end():].strip() if address else ''
    common=[re.sub(r'\s+',' ',x).strip() for x in (prefix,footer,summary) if x]
    selected=[]
    for row in rows:
        if row['city'] not in ('臺北市','新北市','桃園市'):
            return None
        vf=re.search(r'(\d+)樓',row['venue']);af=re.search(r'(\d+)樓',row['address'])
        if vf and af and vf[1]!=af[1]:
            return None
        if row['end_time']>f['end_time']:
            return None
        selected.append({'session':row,'category':'台語故事' if '說故事' in title else '台語活動'})
    return {'title':title,'article_sha256':digest(article),'summary_sha256':digest(summary),
            'language_quote':language,'organizer':f['organizer'],'common_quotes':common,
            'is_free':True,'price_info':'免費；報名及參加限制請見活動內容與官方報名頁。',
            'sessions':selected,'review_basis':'explicit_free_taigi_teaching_series'}
