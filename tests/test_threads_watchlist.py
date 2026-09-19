import json
import unittest

from crawler.sources.threads import ThreadsCrawler, watched_accounts
from crawler.threads_review import build_threads_review

ACCOUNT = [{'username': 'example', 'name': 'Example', 'url': 'https://www.threads.com/@example'}]
EVIDENCE = {'url': 'https://graph.threads.com/v1.0/test', 'http_status': 200,
            'fetched_at': '2026-09-19T12:00:00+08:00', 'sha256': 'a' * 64}


class MockClient:
    def __init__(self, jsons=None):
        self.jsons, self.calls, self.requests = list(jsons or []), [], []

    def json(self, url, payload=None, token=None):
        self.calls.append((url, payload, token))
        return self.jsons.pop(0), dict(EVIDENCE, url=url)


class ThreadsWatchlistTests(unittest.TestCase):
    def test_requested_accounts_are_the_active_watchlist(self):
        self.assertEqual([row['username'] for row in watched_accounts()],
                         ['chhut_goa_kong_tai_gi', 'taigiloo', 'lesecondfloor', 'lekhiantang'])

    def test_exact_account_post_and_visible_reply_links_are_collected(self):
        post = {'id': '11', 'text': '台語活動 https://forms.gle/official',
                'permalink': 'https://www.threads.com/@example/post/ABC',
                'timestamp': '2026-09-19T01:00:00+0000', 'username': 'example',
                'has_replies': True, 'is_reply': False}
        replies = [{'id': '12', 'text': '補充 https://linktr.ee/example', 'username': 'example'},
                   {'id': '13', 'text': '路人 https://evil.example/clue', 'username': 'someone'}]
        client = MockClient(jsons=[{'data': [post]}, {'data': replies}])
        result = ThreadsCrawler(['台語'], env={'THREADS_ACCESS_TOKEN': 'SECRET'},
                                accounts=ACCOUNT).collect(client)
        self.assertEqual(result.status, 'ok')
        self.assertEqual(len(result.candidates), 1)
        row = result.candidates[0]
        self.assertEqual(row['account_username'], 'example')
        self.assertEqual(row['replies_read'], 2)
        self.assertEqual([link['is_page_author'] for link in row['discovered_links']], [True, True, False])
        self.assertIn('/11/conversation?', client.calls[1][0])
        self.assertNotIn('SECRET', json.dumps(result.to_dict()))

        safe = build_threads_review(result.to_dict())
        encoded = json.dumps(safe, ensure_ascii=False)
        self.assertEqual(safe['source_id'], 'threads_review')
        self.assertNotIn('路人', encoded)
        self.assertNotIn('someone', encoded)
        self.assertEqual(safe['candidates'][0]['review_context']['official_link_count'], 2)

    def test_missing_token_reports_each_account_without_requests(self):
        client = MockClient()
        result = ThreadsCrawler(env={}).collect(client)
        self.assertEqual(result.status, 'needs_configuration')
        self.assertEqual(len(result.account_status), 4)
        self.assertTrue(all(row['status'] == 'needs_configuration' for row in result.account_status))
        self.assertEqual(client.calls, [])


if __name__ == '__main__':
    unittest.main()
