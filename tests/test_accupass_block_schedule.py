import copy,json,tempfile,unittest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
from crawler.collection import CollectionError
from crawler.sources.accupass import parse_event
from crawler.sources.accupass_block_schedule import block_schedule
from crawler.reviewed_sessions import automatic_contract,validate_live,expand,verify
from crawler.review import duplicate
from crawler.editorial_queue import prepare

URL='https://www.accupass.com/event/123456789'
NOW=datetime.fromisoformat('2026-09-30T10:00:00+08:00')
EVENT={'@type':'Event','name':'台語說故事系列課程','startDate':'2026-10-03T09:30:00+08:00',
 'endDate':'2026-10-03T11:30:00+08:00','eventStatus':'https://schema.org/EventScheduled',
 'organizer':{'name':'主辦團隊'},'location':{'address':'桃園市'},
 'description':'一起聽故事、講台語。活動全程免費。'}

def page(second='乙教室',extra=''):
 article='親子皆須報名。'+''.join('<p>10/3（六）09:30–11:30<br>主題：故事'+n+'<br>講師：老師'+n+'<br>內容：台語故事及互動。<br>地點：'+venue+'<br>地址：桃園市桃園區測試路'+n+'號</p>' for n,venue in [('1','甲教室'),('2',second)])+'<p>主辦團隊；限額20位。'+extra+'</p>'
 return '<script type="application/ld+json">'+json.dumps(EVENT,ensure_ascii=False)+'</script><article class="EventContent_event-content__abc">'+article+'</article>'

class Client:
 def __init__(self,html=None):self.html=html or page()
 def get(self,url):return self.html,{'final_url':url,'fetched_at':NOW.isoformat(),'sha256':'a'*64}

class BlockTests(unittest.TestCase):
 def test_same_time_different_places_are_distinct_and_source_changes_fail(self):
  h=page(); rows,issue=block_schedule(h,EVENT)
  self.assertEqual(len(rows),2);self.assertFalse(issue)
  self.assertNotEqual(rows[0]['session_key'],rows[1]['session_key'])
  c=automatic_contract(h,URL);self.assertIsNotNone(c)
  parent=parse_event(h,URL,{})[0];children=expand(parent,Client(),c)
  built=[verify(ch,Client(),c,NOW) for ch in children]
  self.assertIsNone(duplicate(built[1][2]['activity'],{'activities':[built[0][2]]}))
  validate_live(built[0][1],h)
  for changed in [h.replace('甲教室','丙教室'),h.replace('限額20位','限額10位'),h.replace('老師1','老師3')]:
   with self.assertRaises(CollectionError):validate_live(built[0][1],changed)
 def test_bad_rows_and_dates_do_not_silently_disappear(self):
  for old,new in [('10/3（六）','10/3（日）'),('10/3（六）','10/30（六）'),('09:30','25:30'),('地點：甲教室','未知'),('10/3（六）09:30–11:30','時間未定')]:
   h=page().replace(old,new);rows,issue=block_schedule(h,EVENT)
   self.assertFalse(rows);self.assertTrue(issue)
 def test_keyword_only_paid_or_cancelled_series_cannot_auto_approve(self):
  for h in [page().replace('活動全程免費','票價100元'),page(extra='本活動延期'),page(extra='材料費另收')]:
   self.assertIsNone(automatic_contract(h,URL))
 def test_pipeline_queues_both_and_preserves_catalog(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'data/editorial').mkdir(parents=True);(root/'candidates').mkdir()
   data={'data/verified_activities.json':{'schema_version':1,'sources':{},'activities':[]},
    'data/ai_taigi.json':{'schema_version':1,'protected_activity_ids':[],'editions':{},'attempts':{},'daily_usage':{}},
    'data/ui_taigi.json':{},'data/ui_price_taigi.json':{},'data/editorial/queue.json':{'schema_version':1,'items':[]},
    'data/editorial/receipts.json':{'schema_version':1,'results':{}},
    'candidates/report.json':{'collected_at':NOW.isoformat(),'sources':[{'source_id':'accupass','status':'ok','candidate_count':1}]},
    'candidates/accupass.json':{'source_id':'accupass','candidates':parse_event(page(),URL,{})}}
   for p,v in data.items():(root/p).write_text(json.dumps(v))
   with patch('crawler.review.Client',return_value=Client()):
    q=prepare(root/'candidates',root,NOW);q2=prepare(root/'candidates',root,NOW)
   self.assertEqual(len(q['items']),2);self.assertEqual(len(q2['items']),2)
   self.assertEqual(json.loads((root/'data/verified_activities.json').read_text())['activities'],[])
   # A failed/empty collector must not drop the previous unresolved candidates.
   (root/'data/editorial/queue.json').write_text(json.dumps({'schema_version':1,'items':[]}))
   (root/'data/review_backlog.json').write_text(json.dumps({'schema_version':1,'candidates':parse_event(page(),URL,{})}))
   (root/'candidates/report.json').write_text(json.dumps({'collected_at':NOW.isoformat(),'sources':[]}))
   with patch('crawler.review.Client',return_value=Client()):
    recovered=prepare(root/'candidates',root,NOW)
   self.assertEqual(len(recovered['items']),2)

class RecheckRegressionTests(unittest.TestCase):
 def test_library_announcement_wins_over_longer_login_article(self):
  from crawler.collection import Document
  html='<article>'+('登入說明'*100)+'</article><div class="article-page paging-content"><article>台語故事10/3</article><div class="info">點閱次數100</div></div>'
  self.assertEqual(Document(html).content(),'台語故事10/3')
 def test_explicit_spoken_taigi_without_colon_but_not_subtitles_or_biography(self):
  from crawler.review import language_claims
  for text in ['全台語演出，無中場休息。','國、台語演出；華語字幕。','字幕語言：中英文字幕、台語發音']:
   self.assertTrue(language_claims({},dict(id=1,eventNoteContent=text)))
  for text in ['非台語演出','字幕語言：台語文','演出語言：華語。台語指導：王老師。']:
   self.assertFalse(language_claims({},dict(id=1,eventNoteContent=text)))
  self.assertFalse(language_claims({'description':'曾以台語演出多部作品'},dict(id=1,eventNoteContent='')))
 def test_reviewed_announcement_rejects_changed_terms(self):
  from crawler.reviewed_announcements import check,content
  from crawler.accupass_text_review import digest
  h=page();c={'content_sha256':digest(content(h,URL)),'sessions':[{'activity':{'source_url':URL},'language_quote':'講台語','quotes':['限額20位']} ]}
  check(h,URL,c)
  with self.assertRaises(CollectionError):check(h.replace('限額20位','限額10位'),URL,c)
