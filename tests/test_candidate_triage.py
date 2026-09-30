import copy
import json
import tempfile
import unittest
from pathlib import Path
from crawler.candidate_triage import document, digest, matches, load, PATH
from crawler.collection import relevant
from crawler.reviewed_opentix_language import content, validate, claims, notice_valid
from scripts.review_triage import apply, export, followup
from datetime import datetime, timedelta
from crawler.collection import TAIPEI


class Client:
    def __init__(self, body):
        self.body = body

    def get(self, url):
        return self.body, {'final_url': url}


class TriageTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
