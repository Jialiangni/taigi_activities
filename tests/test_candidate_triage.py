import copy
import json
import tempfile
import unittest
from pathlib import Path
from crawler.candidate_triage import document, digest, matches, load, PATH
from crawler.collection import relevant
from crawler.reviewed_opentix_language import content, validate, claims, notice_valid
from scripts.review_triage import apply, export, followup, recheck_closed
from datetime import datetime, timedelta
from crawler.collection import TAIPEI


class Client:
    def __init__(self, body):
        self.body = body

    def get(self, url):
        return self.body, {'final_url': url}


class TriageTests(unittest.TestCase):
    def test_saved_closures_do_not_starve_overdue_and_new_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'data').mkdir()
            due = dict(self.c, id='due', source_url='https://example.org/due')
            new = dict(self.c, id='new', source_url='https://example.org/new')
            (root/'data/review_backlog.json').write_text(json.dumps({'candidates':[self.c, new, due]}))
            (root/PATH).write_text(json.dumps({'schema_version':1, 'decisions':[self.row]}))
            past = (datetime.now(TAIPEI)-timedelta(days=1)).isoformat()
            (root/'data/review_followups.json').write_text(json.dumps({'cases':{'due':{'next_review_at':past}}}))
            result = export(root, root/'out.json', limit=2, client=Client(self.body))
            self.assertEqual(['due','new'], [r['candidate']['id'] for r in result])

    def test_recheck_only_removes_matching_live_evidence_and_keeps_failure(self):
        from crawler.collection import CollectionError
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'data').mkdir()
            changed = dict(self.c, id='changed', source_url='https://example.org/changed')
            failed = dict(self.c, id='failed', source_url='https://example.org/failed')
            fresh = dict(self.c, id='fresh', source_url='https://example.org/fresh')
            p = root/'data/review_backlog.json'
            p.write_text(json.dumps({'candidates':[self.c,changed,failed,fresh]}))
            rows = [dict(self.row, candidate_id=c['id'], source_url=c['source_url'], evidence_url=c['source_url']) for c in [self.c,changed,failed]]
            (root/PATH).write_text(json.dumps({'schema_version':1,'decisions':rows}))
            owner = self
            class Pages:
                def get(self, url):
                    if url == failed['source_url']: raise CollectionError('http_429')
                    return (owner.body.replace('2025','2027') if url == changed['source_url'] else owner.body), {'final_url':url}
            report = recheck_closed(root, root/'out.json', client=Pages())
            self.assertEqual(1, report['confirmed_closed'])
            self.assertEqual(['changed','failed','fresh'],[c['id'] for c in json.loads(p.read_text())['candidates']])
            self.assertEqual(['confirmed_closed','changed_or_identity_mismatch','source_unavailable'],[r['status'] for r in report['checks']])
            self.assertEqual(rows,json.loads((root/PATH).read_text())['decisions'])

    def test_public_registration_form_is_not_a_google_search_page(self):
        from crawler.verified import detail_url
        url = 'https://docs.google.com/forms/d/e/public-form-id/viewform?usp=send_form'
        self.assertEqual(url, detail_url(url))
        for url in ['https://www.google.com/search?q=台語',
                    'https://docs.google.com/forms/d/e/id/formResponse',
                    'https://docs.google.com/forms/d/id/edit',
                    'https://docs.google.com/document/d/id/edit']:
            with self.assertRaises(ValueError):
                detail_url(url)

    def test_incidental_stage_and_programming_language_not_discovered(self):
        self.assertFalse(relevant('以舞台語言呈現舞蹈，Python是跨平台語言'))
        self.assertFalse(relevant('精準的舞臺語彙'))
        self.assertTrue(relevant('以舞台語言呈現台語演唱'))

    def setUp(self):
        self.c = dict(id='one', source_id='test', title='Old event', source_url='https://example.org/event')
        self.body = '<main>Event ended 2025/12/01</main>'
        self.row = dict(candidate_id='one', source_id='test', title='Old event',
                        source_url=self.c['source_url'], evidence_url=self.c['source_url'],
                        reason='expired', rationale='The announced event has ended',
                        reviewed_at='2026-10-01T01:00:00+08:00',
                        content_sha256=digest(document(self.body, self.c['source_url'])),
                        quotes=['2025/12/01'])

    def test_changed_source_or_identity_reopens(self):
        self.assertTrue(matches(self.row, self.c, Client(self.body)))
        self.assertFalse(matches(self.row, self.c, Client(self.body.replace('2025', '2027'))))
        self.assertFalse(matches(self.row, dict(self.c, title='New event'), Client(self.body)))
        self.assertFalse(matches(dict(self.row, quotes=['invented']), self.c, Client(self.body)))

    def test_versioned_counter_change_does_not_reopen_resource_but_content_does(self):
        url = 'https://www.ceramics.ntpc.gov.tw/xmdoc/cont?xsmsid=one'
        c = dict(self.c, source_url=url)
        body = '<main>台語語音導覽 2026/10/03 名額25人 瀏覽人次：1,234</main>'
        row = dict(self.row, source_url=url, evidence_url=url, document_version=2,
                   quotes=['台語語音導覽'], content_sha256=digest(document(body, url, 2)))
        self.assertTrue(matches(row, c, Client(body.replace('1,234', '1,235'))))
        for before, after in [('台語', '華語'), ('2026/10/03', '2026/10/04'), ('25人', '20人')]:
            self.assertFalse(matches(row, c, Client(body.replace(before, after))))
        old = dict(row, document_version=1, content_sha256=digest(document(body, url)))
        self.assertTrue(matches(old, c, Client(body)))
        self.assertFalse(matches(old, c, Client(body.replace('1,234', '1,235'))))
        other = 'https://example.org/event'
        self.assertNotEqual(document(body, other, 2), document(body.replace('1,234', '1,235'), other, 2))
        with self.assertRaises(ValueError):
            document(body, url, 4)

    def test_empty_taigiloo_entry_preserves_visible_index_identity(self):
        url = 'https://taigiloo.tw/articles/'
        body = '<div id="content"><h1>文章列表 – 台語路經驗分享</h1><div class="entry-content"></div></div>'
        before = document(body, url)
        self.assertIn('文章列表', before)
        changed = body.replace('</h1>', '</h1><a href="/new-event">新活動</a>')
        self.assertNotEqual(digest(before), digest(document(changed, url)))
        self.assertEqual('', document('<div class="entry-content"></div>', url))

    def test_failed_batch_does_not_delete_backlog(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'data').mkdir()
            p = root / 'data/review_backlog.json'
            p.write_text(json.dumps({'schema_version': 1, 'candidates': [self.c]}))
            before = p.read_bytes()
            with self.assertRaises(ValueError):
                apply(root, {'decisions': [self.row]}, Client('<main>changed</main>'))
            self.assertEqual(before, p.read_bytes())
            self.assertFalse((root / PATH).exists())
            apply(root, {'decisions': [self.row]}, Client(self.body))
            self.assertEqual([], json.loads(p.read_text())['candidates'])
            self.assertEqual(1, len(load(root)))

    def test_session_changes_invalidate_opentix_exclusion(self):
        p = {'result': {'name': 'event', 'eventVenues': [{'events': [{'id': 1}]}]}}
        before = document(json.dumps(p), 'https://csm.api.opentix.life/programs/1')
        p['result']['eventVenues'][0]['events'].append({'id': 2})
        after = document(json.dumps(p), 'https://csm.api.opentix.life/programs/1')
        self.assertNotEqual(digest(before), digest(after))

    def test_archived_opentix_html_requires_exact_page_and_api_400(self):
        from crawler.collection import CollectionError
        c = dict(self.c, source_id='opentix', source_url='https://www.opentix.life/event/123')
        body = '<main>Old event 本節目已下架 Event ended 2025/12/01</main>'
        row = dict(self.row, source_id='opentix', source_url=c['source_url'],
                   evidence_url=c['source_url'], evidence_kind='opentix_archived_html',
                   content_sha256=digest(document(body, c['source_url'])))
        class Archived:
            error = 'http_400'
            html = body
            def get(self, url):
                if 'csm.api.opentix.life' in url:
                    if self.error:
                        raise CollectionError(self.error)
                    return '{"result":{"eventVenues":[{"events":[{"id":2}]}]}}', {'final_url': url}
                return self.html, {'final_url': url}
        client = Archived()
        self.assertTrue(matches(row, c, client))
        self.assertFalse(matches(dict(row, evidence_url=c['source_url']+'4'), c, client))
        self.assertFalse(matches(dict(row, reason='not_taigi'), c, client))
        client.error = None
        self.assertFalse(matches(row, c, client))
        client.error = 'http_503'
        with self.assertRaises(CollectionError):
            matches(row, c, client)
        client.error = 'http_400'
        client.html = body.replace('2025', '2027')
        self.assertFalse(matches(row, c, client))
        client.html = body.replace('本節目已下架', '')
        self.assertFalse(matches(dict(row, content_sha256=digest(document(client.html, c['source_url']))), c, client))

    def test_reviewed_poster_must_remain_linked_and_unchanged(self):
        from crawler.reviewed_announcements import check
        from crawler.accupass_text_review import digest as normalized_digest
        from crawler.collection import CollectionError
        url = 'https://www.xizhi.ntpc.gov.tw/home.jsp?id=one'
        h = '<div id="home_content">台語演出<img src="/poster.jpg"></div><footer>Visitor 10</footer>'
        poster = {'url': 'https://www.xizhi.ntpc.gov.tw/poster.jpg', 'image_sha256': 'a'*64,
                  'transcription': '11/7 19:00', 'reviewed_at': '2026-10-01'}
        c = {'content_version': 2, 'content_sha256': normalized_digest(document(h, url)),
             'poster_evidence': [poster], 'sessions': []}
        class Images:
            hash = 'a'*64
            def scoped(self, hosts):
                self.hosts = hosts
                return self
            def get(self, image_url):
                return '', {'final_url': image_url, 'sha256': self.hash}
        client = Images()
        check(h.replace('Visitor 10','Visitor 11'), url, c, client)
        self.assertEqual(client.hosts, {'www.xizhi.ntpc.gov.tw'})
        client.hash = 'b'*64
        with self.assertRaises(CollectionError):
            check(h, url, c, client)
        client.hash = 'a'*64
        with self.assertRaises(CollectionError):
            check(h.replace('/poster.jpg','/replacement.jpg'), url, c, client)

    def test_reviewed_language_is_bound_to_venue_and_complete_prose(self):
        p = {'id': 1, 'name': 'Program', 'description': '<p>本場演唱台語歌曲</p>'}
        g = {'id': 2, 'eventNoteContent': ''}
        claim = dict(origin='reviewed_program', program_id='1', group_id='2',
                     quote='本場演唱台語歌曲', rationale='Applies to this program', reviewed_at='2026-10-01',
                     content_sha256=digest(content(p, g)))
        self.assertTrue(validate(claim, p, g))
        self.assertFalse(validate(claim, dict(p, description=p['description']+'改為華語'), g))
        self.assertFalse(validate(claim, p, dict(g, id=3)))

    def test_mixed_series_does_not_authorize_other_sessions(self):
        p = {'id': 1, 'name': 'Mixed series', 'description': 'Friday 台語; Saturday 客語'}
        g = {'id': 2, 'events': [{'id': 10}, {'id': 11}]}
        claim = dict(origin='reviewed_program', program_id='1', group_id='2',
                     quote='Friday 台語', rationale='Friday only', reviewed_at='2026-10-01',
                     content_sha256=digest(content(p, g)), session_ids=['10'])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'data').mkdir()
            (root/'data/reviewed_opentix_language.json').write_text(json.dumps(
                {'schema_version': 1, 'claims': [claim]}))
            self.assertEqual([claim], claims(root, p, g, '10'))
            self.assertEqual([], claims(root, p, g, '11'))
            self.assertFalse(validate(dict(claim, session_ids=['99']), p, g))
        p['changeNotification'] = 'Saturday cancelled'
        claim.update(change_notice_sha256=digest('Saturday cancelled'), change_notice_rationale='Friday unaffected')
        self.assertTrue(notice_valid(claim, p, '10'))
        self.assertFalse(notice_valid(claim, p, '11'))
        self.assertFalse(notice_valid(claim, dict(p, changeNotification='Friday cancelled'), '10'))

    def test_v3_ignores_only_reviewed_navigation_counters_and_clock(self):
        url = 'https://www.jinshan.ntpc.gov.tw/home.jsp?id=event'
        h = '<main>進入內容區塊 Toggle navigation 115 - 10 - 06 星期二 16 : 48 請輸入關鍵字搜尋 活動115年10月9日19:00 票價100元 名額20人 累計人數：2471294人</main>'
        changed = h.replace('16 : 48', '17 : 01').replace('2471294', '2471303')
        self.assertEqual(document(h, url, 3), document(changed, url, 3))
        self.assertNotEqual(document(h, url, 2), document(changed, url, 2))
        for old, new in [('10月9日', '10月10日'), ('票價100', '票價200'), ('名額20', '名額30')]:
            self.assertNotEqual(document(h, url, 3), document(h.replace(old, new), url, 3))
        self.assertNotEqual(document(h, url, 3), document(h.replace('</main>', '活動取消</main>'), url, 3))
        self.assertNotEqual(document(h, 'https://example.com/', 3), document(changed, 'https://example.com/', 3))

    def test_unknown_end_requires_exact_session_conflict_and_live_prose(self):
        from crawler.reviewed_opentix_language import omits_end
        start = datetime(2026, 10, 7, 20, tzinfo=TAIPEI)
        end = datetime(2026, 10, 7, 23, 30, tzinfo=TAIPEI)
        p = {'id': 1, 'name': '歌仔戲', 'description': '台語演出'}
        g = {'id': 2, 'eventNoteContent': '演出全長：1小時',
             'events': [{'id': 10, 'startDateTime': start.timestamp(), 'endDateTime': end.timestamp()}]}
        conflict = dict(session_id='10', start_time=start.isoformat(), api_end_time=end.isoformat(),
                        quote='演出全長：1小時', rationale='Conflicting end; publish start only')
        claim = dict(origin='reviewed_program', program_id='1', group_id='2',
                     quote='台語演出', rationale='Official program', reviewed_at='2026-10-06',
                     content_sha256=digest(content(p, g)), session_ids=['10'], end_time_conflicts=[conflict])
        session = dict(session_id='10', start_time=start.isoformat(), end_time=end.isoformat())
        self.assertTrue(validate(claim, p, g))
        self.assertTrue(omits_end(claim, session))
        self.assertFalse(omits_end(claim, dict(session, session_id='11')))
        self.assertFalse(omits_end(claim, dict(session, end_time=start.isoformat())))
        self.assertFalse(validate(dict(claim, end_time_conflicts=[dict(conflict, rationale='')]), p, g))
        self.assertFalse(validate(dict(claim, end_time_conflicts=[dict(conflict, quote='invented')]), p, g))
        changed = dict(g, events=[dict(g['events'][0], endDateTime=end.timestamp()+60)])
        self.assertFalse(validate(claim, p, changed))
        self.assertFalse(validate(claim, p, dict(g, eventNoteContent='演出全長：2小時')))

    def test_followups_have_due_dates_and_do_not_remove_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'data').mkdir()
            (root/'data/review_backlog.json').write_text(json.dumps({'candidates': [self.c]}))
            now = datetime.now(TAIPEI)
            case = dict(candidate_id='one', source_url=self.c['source_url'], owner='Codex',
                        finding='Two dates disagree', missing_fields=['date'], next_action='Check official booking form',
                        reviewed_at=now.isoformat(), next_review_at=(now+timedelta(days=1)).isoformat())
            followup(root, {'cases': [case]})
            self.assertEqual([], export(root, root/'output.json', client=Client(self.body)))
            self.assertEqual(1, len(json.loads((root/'data/review_backlog.json').read_text())['candidates']))
            with self.assertRaises(ValueError):
                followup(root, {'cases': [dict(case, next_review_at=(now+timedelta(days=30)).isoformat())]})

    def test_supporting_form_changes_reopen_closed_candidate(self):
        url = 'https://official.example/form'
        body = '<main>Conference: 2025/12/14</main>'
        proof = dict(url=url, content_sha256=digest(document(body, url)),
                     quotes=['2025/12/14'], reviewed_at='2026-10-01', rationale='Linked official registration')
        owner = self
        class Pages:
            form = body
            def get(self, requested):
                return (self.form if requested == url else owner.body), {'final_url': requested}
        client = Pages()
        row = dict(self.row, supporting_evidence=[proof])
        self.assertTrue(matches(row, self.c, client))
        client.form = body.replace('2025', '2027')
        self.assertFalse(matches(row, self.c, client))

    def test_external_language_proof_is_live_and_session_scoped(self):
        from crawler.reviewed_supporting_evidence import valid
        url = 'https://official.example/program'
        body = '<main>11/8 本演出為臺灣台語發音</main>'
        proof = dict(url=url, content_sha256=digest(document(body, url)),
                     quotes=['11/8', '本演出為臺灣台語發音'], reviewed_at='2026-10-01', rationale='Same dated performance')
        p = dict(id=1, name='Series', description='11/8 puppet; 11/9 Mandarin')
        g = dict(id=2, events=[{'id': 10}, {'id': 11}])
        claim = dict(origin='reviewed_program', program_id='1', group_id='2',
                     content_sha256=digest(content(p, g)), quote='11/8 puppet',
                     reviewed_at='2026-10-01', rationale='Official venue confirms language',
                     session_ids=['10'], supporting_evidence=[proof])
        self.assertTrue(validate(claim, p, g, Client(body)))
        self.assertFalse(validate(claim, p, g, Client(body.replace('台語', '華語'))))
        unscoped = dict(claim); del unscoped['session_ids']
        self.assertFalse(validate(unscoped, p, g, Client(body)))
        self.assertFalse(valid([], Client(body)))
        self.assertFalse(valid([dict(proof, quotes=['invented'])], Client(body)))
        class Redirect(Client):
            def get(self, url):
                return self.body, {'final_url': url + '/redirect'}
        self.assertFalse(validate(claim, p, g, Redirect(body)))
        class Failure(Client):
            def get(self, url):
                raise OSError('official source unavailable')
        with self.assertRaises(OSError):
            validate(claim, p, g, Failure(body))


if __name__ == '__main__':
    unittest.main()
