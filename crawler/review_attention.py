"""Make unresolved candidates actionable and recheck their source instead of hiding them."""
import re
from datetime import datetime
from .collection import CollectionError,TAIPEI


def annotate(item,c,client,catalog):
    from .review import source_url
    matches=[r['activity']['id'] for r in catalog['activities'] if source_url(r['activity']['source_url'])==source_url(c['source_url'])]
    if matches:
        item['published_session_ids']=matches
    if item['decision']!='pending':
        return
    reason=item.get('reason','')
    if c['source_id'] in ('facebook_review','facebook','instagram','threads_review','threads'):
        item['next_action']='核對具作者身分的官方活動連結；不抓取未授權社群內容。'
        item['missing_evidence']=['official_event_link']
        return
    if c['source_id']=='opentix':
        item['next_action']='核對官方場次語言／異動公告；未有明確證據前不進編輯佇列。'
        item['missing_evidence']=['spoken_language_or_change_notice']
        item['rechecked_at']=datetime.now(TAIPEI).isoformat(timespec='seconds')
        return
    try:
        html,evidence=client.get(c['source_url'])
        item['source_recheck']={k:evidence[k] for k in ('final_url','fetched_at','sha256','http_status') if k in evidence}
        item['rechecked_at']=evidence['fetched_at']
    except (CollectionError,ValueError,OSError) as error:
        item['source_recheck']={'status':'failed','code':getattr(error,'code',type(error).__name__)}
        item['next_action']='來源目前無法讀取，待恢復後重查；保留候選。'
        item['missing_evidence']=['reachable_official_source']
        return
    if 'language' in reason:
        missing=['explicit_taigi_content'];action='補核官方是否明確包含台語教學／演出，不能用人物簡介或關鍵字代替。'
    elif any(s in reason for s in ('series','schedule','labelled')):
        missing=['individual_session_and_participation_terms'];action='逐場核對日期、講師、地點與參加條件；查看已拆出的場次與解析問題。'
    elif 'duplicate' in reason:
        missing=['cross_source_session_identity'];action='比對另一來源的日期與場地，確認同場或不同場。'
    elif 'identity' in reason:
        missing=['venue_address_or_organizer'];action='從官方正文補核場地、地址及主辦單位。'
    else:
        missing=['complete_future_session_and_taigi_evidence'];action='核對正文中的未來場次、台語內容及參加條件；一般文章／展覽／導覽服務不直接作為單場活動。'
    item['missing_evidence']=missing;item['next_action']=action


def summary(audit):
    rows=[d for d in audit['decisions'] if d['decision']=='pending']
    return {'pending_candidates':len(rows),'already_has_published_sessions':sum(bool(r.get('published_session_ids')) for r in rows),
            'source_unavailable':sum(r.get('source_recheck',{}).get('status')=='failed' for r in rows),
            'message':'待編輯0筆不代表所有候選已核實；以下待核實項目仍須處理。' if rows else '本輪沒有未解決候選。'}
