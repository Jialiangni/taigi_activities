"""Recheck explicitly reviewed announcement sessions without guessing unknown fields."""
import json,hashlib
from pathlib import Path
from .collection import Document,candidate
from .accupass_text_review import require,digest
from .sources.accupass import parse_event,event_jsonld
from .verified import normalized_text,parse_time,REVIEWED_FIELDS

MODE='reviewed_announcement_sessions_v1'

def public_form_content(html, url):
 """Bind author content/settings, not Google's region-dependent UI labels.

 Versioned separately from old full-page contracts. Only an open, matching
 public form qualifies; missing payload, closed forms or identity changes fail.
 """
 import re
 from urllib.parse import urlsplit
 parts=urlsplit(url)
 match=re.fullmatch(r'/forms/d/e/([A-Za-z0-9_-]+)/viewform',parts.path)
 require(parts.scheme=='https' and parts.netloc=='docs.google.com' and match is not None,
         'reviewed_form_url_invalid')
 marker=re.search(r'\bFB_PUBLIC_LOAD_DATA_\s*=\s*',html)
 require(marker is not None,'reviewed_form_payload_missing')
 try:
  payload=json.JSONDecoder().raw_decode(html[marker.end():])[0]
  require(isinstance(payload,list) and len(payload)>14 and payload[14]=='e/'+match[1],
          'reviewed_form_identity_changed')
  require(isinstance(payload[1],list) and len(payload[1])>8 and payload[1][8],
          'reviewed_form_payload_invalid')
 except (ValueError,TypeError,IndexError):
  require(False,'reviewed_form_payload_invalid')
 forms=list(Document(html).root.all('form'))
 require(len(forms)==1 and urlsplit(forms[0].attrs.get('action','')).netloc==parts.netloc
         and urlsplit(forms[0].attrs.get('action','')).path==parts.path.replace('/viewform','/formResponse'),
         'reviewed_form_closed_or_changed')
 return json.dumps({'identity':payload[14],'form':payload[1]},ensure_ascii=False,sort_keys=True,separators=(',',':'))

def contracts(root):
 p=Path(root)/'data/reviewed_announcements.json'
 if not p.exists():return {}
 data=json.loads(p.read_text());require(data.get('schema_version')==1,'reviewed_announcements_version')
 return data['events']

def content(html,url):
 if url.startswith('https://www.accupass.com/event/'):
  rows=parse_event(html,url,{})
  require(len(rows)==1,'reviewed_announcement_identity_missing')
  require(rows[0]['fields']['event_status']=='https://schema.org/EventScheduled','reviewed_announcement_status_changed')
  from .collection import plain
  event=list(event_jsonld(Document(html)))[0]
  return rows[0]['fields']['official_summary']+' '+plain(event.get('description') or '')
 return Document(html).content()

def check(html,url,contract,client=None):
 from .candidate_triage import document
 version=contract.get('content_version',1)
 require(version in (1,2,3),'reviewed_announcement_content_version')
 bound = public_form_content(html,url) if version==3 else document(html,url) if version==2 else content(html,url)
 require(digest(bound)==contract['content_sha256'],'reviewed_announcement_content_changed')
 if contract.get('poster_evidence'):
  from urllib.parse import urljoin,urlsplit
  from .collection import Client
  posters=contract['poster_evidence']
  require(isinstance(posters,list) and 1<=len(posters)<=3,'reviewed_poster_limit')
  linked={urljoin(url,n.attrs.get('src','')) for n in Document(html).root.all('img')}
  client=client or Client()
  for p in posters:
   require(p.get('transcription') and p.get('reviewed_at'),'reviewed_poster_reading_missing')
   image_url=p['url']
   require(image_url in linked and urlsplit(image_url).scheme=='https' and
           urlsplit(image_url).netloc==urlsplit(url).netloc,'reviewed_poster_not_official_attachment')
   _,ev=client.scoped({urlsplit(url).netloc}).get(image_url)
   require(ev['final_url']==image_url and ev['sha256']==p['image_sha256'],'reviewed_poster_changed')
 full=normalized_text(html)
 import re
 for row in contract['sessions']:
  require(row['activity']['source_url']==url,'reviewed_announcement_wrong_source')
  require(row['language_quote'] and row['language_quote'] in content(html,url),'reviewed_announcement_language_missing')
  require(all(re.sub(r'\s+','',q) in full for q in row['quotes']),'reviewed_announcement_quote_missing')

def expand(parent,client,contract):
 h,e=client.get(parent['source_url']);require(e['final_url']==parent['source_url'],'official_page_redirected')
 check(h,parent['source_url'],contract,client)
 return [candidate(parent['source_id'],parent['source_url'],s['activity']['title'],content(h,parent['source_url']),e,
    dict(s['activity'],reviewed_announcement_id=s['activity']['id']),'session',key=s['activity']['id']) for s in contract['sessions']]

def verify(c,client,contract,now):
 h,e=client.get(c['source_url']);require(e['final_url']==c['source_url'],'official_page_redirected');check(h,c['source_url'],contract,client)
 selected=next((s for s in contract['sessions'] if s['activity']['id']==c['fields']['reviewed_announcement_id']),None)
 require(selected is not None,'reviewed_announcement_not_selected');a=selected['activity']
 require(parse_time(a.get('end_time') or a['start_time'])>now,'expired')
 key='announcement_'+a['id']
 source={'url':c['source_url'],'title':a['title'],'checked_at':e['fetched_at'],'snapshot_sha256':e['sha256'],
 'required_text':selected['quotes'],'reviewed_announcement':{'mode':MODE,'contract':contract,'activity':a}}
 row={'activity':a,'verification':{'status':'verified','source_id':key,'mode':MODE,
 'language_evidence':selected['language_quote'],'confirmed_fields':{k:a[k] for k in REVIEWED_FIELDS},
 'method':'Codex逐場核對官方公告及條件；發布前重查公告正文、引句與場次綁定，非人類審定。'}}
 return key,source,row

def validate_live(source,html,client=None):
 proof=source['reviewed_announcement'];check(html,source['url'],proof['contract'],client)
 require(any(s['activity']==proof['activity'] for s in proof['contract']['sessions']),'reviewed_announcement_not_selected')
