import json
import unittest
from urllib.parse import parse_qs, urlsplit
from crawler.collection import CollectionError
from crawler.sources.facebook import FacebookCrawler, watched_pages, link_urls
from crawler.social import read_pages
from test_collection import MockClient

PAGES = [{'handle': 'example', 'url': 'https://www.facebook.com/example'}]
ENV = {'FACEBOOK_ACCESS_TOKEN': 'SECRET', 'FACEBOOK_PAGE_ID_MAP': '{"example":"123"}'}

def post(id='123_1', message='親子活動，詳情請看留言'):
    return {'id': id, 'message': message, 'permalink_url': 'https://www.facebook.com/' + id, 'created_time': '2026-09-18T00:00:00Z'}

def page(items, after=None):
    row = {'data': items}
    if after:
        row['paging'] = {'next': 'https://graph.facebook.com/next?access_token=SECRET&after=' + after,
                         'cursors': {'after': after}}
    return row


class FacebookCommentTests(unittest.TestCase):
    def collect(self, replies, **kwargs):
        client = MockClient(jsons=replies)
        result = FacebookCrawler(['台語'], pages=PAGES, env=ENV, **kwargs).collect(client)
        return result, client

    def test_watched_handles_are_distinct_and_reported_without_auth(self):
        self.assertEqual({p['handle'] for p in watched_pages()}, {'taigilok', 'ChhutGoaKongTaiGi', 'Guaayingla', 'taigiloo'})
        client = MockClient()
        result = FacebookCrawler(env={}).collect(client)
        self.assertEqual(result.status, 'needs_configuration')
        self.assertEqual(len(result.page_status), 4)
        self.assertTrue(all(s['status'] == 'needs_configuration' for s in result.page_status))
        self.assertEqual(client.calls, [])

    def test_keyword_and_registration_only_in_later_reply_are_kept(self):
        rows = [page([post()]), page([{'id': 'c1', 'message': '期待！'}], 'A'),
                page([{'id': 'c2', 'parent': {'id': 'c1'}, 'message': '台語故事報名 https://forms.gle/abc',
                       'from': {'id': '123'}, 'permalink_url': 'https://www.facebook.com/123_1?comment_id=c2'}])]
        r, c = self.collect(rows)
        self.assertEqual(r.status, 'ok')
        a = r.candidates[0]
        self.assertEqual(a['comments_read'], 2)
        self.assertEqual(a['comments'][0]['parent_id'], 'c1')
        self.assertTrue(a['discovered_links'][0]['is_page_author'])
        self.assertEqual(a['discovered_links'][0]['url'], 'https://forms.gle/abc')
        self.assertIsNone(a['fields']['start_time'])
        self.assertEqual(parse_qs(urlsplit(c.calls[1][0]).query)['filter'], ['stream'])
        self.assertEqual(parse_qs(urlsplit(c.calls[2][0]).query)['after'], ['A'])
        self.assertNotIn('SECRET', json.dumps(r.to_dict()))
        self.assertTrue(all('SECRET' not in x[0] for x in c.calls))

    def test_watched_image_posts_without_keywords_are_retained(self):
        r, _ = self.collect([page([post(message='')]), page([])])
        self.assertEqual(len(r.candidates), 1)
        self.assertIn('image_or_attachment_requires_manual_review', r.candidates[0]['issues'])
        self.assertEqual(r.candidates[0]['comment_status'], 'no_visible_comments_not_proof_of_absence')
        self.assertFalse(r.coverage_complete)

    def test_comment_permission_error_does_not_drop_post_or_next_post(self):
        r, c = self.collect([page([post(), post('123_2')]), CollectionError('http_403'),
                            page([{'id': 'c2', 'message': '報名 https://www.accupass.com/event/2'}])])
        self.assertEqual(len(r.candidates), 2)
        self.assertEqual(r.status, 'partial')
        self.assertEqual(r.candidates[0]['comment_status'], 'partial')
        self.assertIn('comments_incomplete', r.candidates[0]['issues'])
        self.assertEqual(r.page_status[0]['status'], 'partial')
        self.assertEqual(r.candidates[1]['discovered_links'][0]['is_page_author'], None)

    def test_comment_page_limit_keeps_links_and_marks_incomplete(self):
        r, _ = self.collect([page([post()]), page([{'id': 'c1', 'message': '報名 https://forms.gle/one'}], 'A')], max_comment_pages=1)
        self.assertEqual(r.status, 'partial')
        self.assertEqual(r.candidates[0]['discovered_links'][0]['url'], 'https://forms.gle/one')
        self.assertIn('comments_incomplete', r.candidates[0]['issues'])

    def test_stream_comments_without_ids_do_not_collide_between_pages(self):
        r, _ = self.collect([page([post()]), page([{'message': '報名 https://forms.gle/one'}], 'A'),
                            page([{'message': '報名 https://forms.gle/two'}])])
        self.assertEqual(r.status, 'ok')
        self.assertEqual(len(r.candidates[0]['discovered_links']), 2)
        self.assertIsNone(r.candidates[0]['comments'][0]['id'])
        client = MockClient(jsons=[page([{'message': 'same'}], 'A'), page([{'message': 'same'}], 'B')])
        with self.assertRaises(CollectionError):
            list(read_pages(client, 'https://graph.facebook.com/comments', {}, 'SECRET', 3))

    def test_attachment_redirect_and_untrusted_comment_authorship(self):
        r, _ = self.collect([page([post()]), page([{'id': 'c1', 'from': {'id': '999', 'name': 'private name'},
            'attachment': {'target': {'url': 'https://l.facebook.com/l.php?u=https%3A%2F%2Fforms.gle%2Fexample&h=tracking'}}}])])
        link = r.candidates[0]['discovered_links'][0]
        self.assertEqual(link['url'], 'https://forms.gle/example')
        self.assertFalse(link['is_page_author'])
        self.assertNotIn('private name', json.dumps(r.to_dict()))
        self.assertEqual(link_urls({'message': 'https://user:pass@example.com/ x javascript:bad'}), [])

    def test_missing_mapping_is_visible_even_when_legacy_feed_succeeds(self):
        r = FacebookCrawler(['台語'], pages=PAGES, env={'FACEBOOK_ACCESS_TOKEN': 'SECRET','FACEBOOK_PAGE_IDS':'456'}).collect(MockClient(jsons=[page([])]))
        self.assertEqual(r.status, 'partial')
        self.assertEqual(r.page_status[0]['status'], 'needs_configuration')
        self.assertEqual(r.page_status[1]['status'], 'ok')

    def test_aliases_with_same_verified_id_are_fetched_once(self):
        pages = PAGES + [{'handle': 'other', 'url':'https://www.facebook.com/other'}]
        env = dict(ENV, FACEBOOK_PAGE_ID_MAP='{"example":"123","other":"123"}')
        c = MockClient(jsons=[page([])])
        r = FacebookCrawler(pages=pages, env=env).collect(c)
        self.assertEqual(len(c.calls), 1)
        self.assertTrue(all(x['status'] == 'ok' for x in r.page_status))

    def test_post_budget_and_invalid_configuration_are_explicit(self):
        r, c = self.collect([page([post(),post('123_2')]), page([])],max_posts=1)
        self.assertEqual(r.status, 'partial')
        self.assertEqual(len(r.candidates), 1)
        self.assertTrue(any(e['code']=='facebook_post_limit_reached' for e in r.errors))
        for mapping in ['invalid SECRET', '[]', '{"example":"https://evil.example/"}']:
            c=MockClient();r=FacebookCrawler(pages=PAGES,env=dict(ENV,FACEBOOK_PAGE_ID_MAP=mapping)).collect(c)
            self.assertEqual(r.status, 'failed')
            self.assertEqual(c.calls, [])
            self.assertNotIn('SECRET',json.dumps(r.to_dict()))

    def test_comment_paging_cannot_send_token_to_another_host(self):
        bad=page([]);bad['paging']={'next':'https://evil.example/?after=x'}
        r,c=self.collect([page([post()]),bad])
        self.assertEqual(r.status,'partial')
        self.assertEqual(len(c.calls),2)
        self.assertIn('comments_incomplete',r.candidates[0]['issues'])
