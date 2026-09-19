import copy
import json
import unittest
import tempfile
from datetime import datetime
from pathlib import Path

from crawler.source_priority import accupass_url, primary_session, publication_priority
from crawler.review import duplicate, review
from crawler.collection import CollectionError
from crawler.verified import load_verified


class SourcePriorityTests(unittest.TestCase):
    def setUp(self):
        self.directory={'id':'directory','source_url':'https://www.gameislearning.url.tw/taigi-info.php?news=abc123',
            'registration_url':'https://www.accupass.com/event/123?utm_source=ios&unknown=tracking',
            'title':'不同公告標題','venue':'另一種場地寫法','city':'臺北市',
            'start_time':'2026-10-17T10:00:00+08:00','end_time':None}
        self.primary=dict(self.directory,id='primary',title='官方標題',venue='主場館',
            source_url='https://www.accupass.com/event/123',registration_url='',end_time='2026-10-17T12:00:00+08:00')
        self.catalog={'activities':[{'activity':self.directory,'verification':{'status':'verified'}},
                                    {'activity':self.primary,'verification':{'status':'verified'}}]}

    def test_same_registration_id_and_start_time_ignore_title_venue_and_tracking(self):
        self.assertEqual(primary_session(self.directory,self.catalog)['activity']['id'],'primary')
        self.assertEqual(duplicate(self.directory,self.catalog),'primary')
        self.assertEqual(publication_priority(self.catalog)['directory']['primary_activity_id'],'primary')

    def test_primary_is_not_blocked_by_existing_directory_record(self):
        catalog={'activities':self.catalog['activities'][:1]}
        self.assertIsNone(duplicate(self.primary,catalog))
        self.assertEqual(publication_priority(catalog)['directory']['reason'],'accupass_session_not_verified')

    def test_never_merge_different_times_cities_event_ids_or_ambiguous_sessions(self):
        for changes in [{'start_time':'2026-10-17T13:30:00+08:00'}, {'city':'新北市'},
                        {'registration_url':'https://www.accupass.com/event/456'}]:
            self.assertIsNone(primary_session(dict(self.directory,**changes),self.catalog))
        catalog=copy.deepcopy(self.catalog)
        catalog['activities'].append(copy.deepcopy(catalog['activities'][1]))
        catalog['activities'][-1]['activity']['id']='second-venue'
        self.assertIsNone(primary_session(self.directory,catalog))

    def test_only_real_event_urls_are_primary_links(self):
        self.assertEqual(accupass_url('https://accupass.com/event/123/?x=1#top'),'https://www.accupass.com/event/123')
        for url in ['http://www.accupass.com/event/123','https://www.accupass.com.evil.test/event/123',
                    'https://user@www.accupass.com/event/123','https://www.accupass.com/go/foo','https://[']:
            self.assertEqual(accupass_url(url),'')

    def test_pipeline_follows_live_registration_and_publishes_primary_once(self):
        now=datetime.fromisoformat('2026-09-19T21:00:00+08:00')
        url='https://www.accupass.com/event/123'
        directory_url=self.directory['source_url']
        directory='<h1>公告的另一個標題</h1><p>報名：https://www.accupass.com/event/123?utm_source=ios</p>'
        html='''<script type="application/ld+json">{
        "@type":"Event","name":"走讀【台語場】",
        "startDate":"2026-10-17T10:00:00+08:00","endDate":"2026-10-17T12:00:00+08:00",
        "eventStatus":"https://schema.org/EventScheduled","location":{"name":"捷運公館站",
        "address":"台灣台北市捷運公館站"},"organizer":{"name":"走讀團隊"}}</script>
        <main>走讀時間【台語場】2026.10.17 10:00-12:00 本活動免費報名。</main>'''
        class Client:
            fail=False
            def get(self,requested):
                if self.fail and requested==url: raise CollectionError('http_503')
                return (directory if requested==directory_url else html), {
                    'final_url':requested,'fetched_at':now.isoformat(),'sha256':'a'*64}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'data').mkdir();folder=root/'candidates';folder.mkdir()
            def write(path,value): (root/path).write_text(json.dumps(value,ensure_ascii=False))
            empty={'schema_version':1,'sources':{},'activities':[]}
            write('data/verified_activities.json',empty)
            write('data/ui_taigi.json',{});write('data/ui_price_taigi.json',{})
            c={'id':'directory-candidate','source_id':'gameislearning','source_url':directory_url,
               'title':'公告的另一個標題','kind':'session','trusted_language_source':True,'fields':dict(self.directory)}
            write('candidates/gameislearning.json',{'source_id':'gameislearning','candidates':[c]})
            write('candidates/report.json',{'collected_at':now.isoformat(),'sources':[
                {'source_id':'gameislearning','status':'ok','candidate_count':1}]})
            client=Client();client.fail=True
            write('data/manual_candidate_decisions.json',{'schema_version':1,'decisions':[{
                'candidate_id':c['id'],'source_id':c['source_id'],'source_url':c['source_url'],
                'title':c['title'],'decision':'excluded','reason':'owner_excluded','reviewed_at':now.isoformat()}]})
            self.assertEqual(review(folder,root,client,now,apply=True)['counts'],{'excluded':1})
            (root/'data/manual_candidate_decisions.json').unlink()
            first=review(folder,root,client,now,apply=True)
            self.assertEqual(first['counts'],{'pending':1})
            self.assertEqual(json.loads((root/'data/verified_activities.json').read_text()),empty)
            client.fail=False
            result=review(folder,root,client,now,apply=True)
            self.assertEqual(result['counts'],{'duplicate':1,'approved':1})
            catalog=json.loads((root/'data/verified_activities.json').read_text())
            self.assertEqual(len(catalog['activities']),1)
            self.assertEqual(catalog['activities'][0]['activity']['source_url'],url)
            self.assertEqual(review(folder,root,client,now,apply=True)['counts'],{'duplicate':1})

    def test_current_publication_deduplicates_and_keeps_taiwanese_intro_evidence(self):
        catalog=json.loads((Path(__file__).resolve().parents[1]/'data/verified_activities.json').read_text())
        priorities=publication_priority(catalog)
        self.assertEqual(len(priorities),5)
        self.assertEqual(sum(bool(p['primary_activity_id']) for p in priorities.values()),4)
        events=load_verified()
        by_id={a.id:a for a in events}
        self.assertFalse(set(priorities)&set(by_id))
        for p in priorities.values():
            if p['primary_activity_id'] in by_id:
                self.assertTrue(by_id[p['primary_activity_id']].raw_metadata['supplemental_description'])
                self.assertEqual(by_id[p['primary_activity_id']].source_url,p['primary_url'])
