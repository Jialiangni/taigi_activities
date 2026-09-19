import json
import unittest

from crawler.facebook_review import build_facebook_review


class FacebookReviewSnapshotTests(unittest.TestCase):
    def test_snapshot_keeps_links_and_drops_commenter_content_and_api_request(self):
        raw = {
            'source_id': 'facebook', 'status': 'ok',
            'errors': [{'url': 'facebook_page:123', 'code': 'http_403'}],
            'started_at': '2026-09-19T03:15:00+08:00', 'completed_at': '2026-09-19T03:16:00+08:00',
            'page_status': [{'page_id': '123', 'handle': 'example'}],
            'candidates': [{
                'id': 'raw-id', 'source_url': 'https://www.facebook.com/example/posts/1?fbclid=tracking',
                'title': '台語活動', 'post_text': '台語活動，日期請看活動頁。', 'page_id': '123',
                'language_hits': ['台語'], 'comment_status': 'checked_visible_comments', 'comments_read': 2,
                'comments': [{'id': 'private-id', 'message': '我的私人留言', 'from': {'name': '某人'}}],
                'discovered_links': [
                    {'url': 'https://events.example/one?utm_source=fb', 'origin': 'post'},
                    {'url': 'https://forms.gle/two', 'origin': 'comment', 'is_page_author': True},
                    {'url': 'https://other.example/clue', 'origin': 'comment', 'is_page_author': False}],
                'evidence': {'url': 'https://graph.facebook.com/123/feed?access_token=SECRET',
                             'fetched_at': '2026-09-19T03:15:01+08:00', 'http_status': 200, 'sha256': 'a' * 64},
                'comment_requests': [{'url': 'https://graph.facebook.com/comments?access_token=SECRET',
                                      'fetched_at': '2026-09-19T03:15:02+08:00', 'http_status': 200, 'sha256': 'b' * 64}]
            }]
        }
        result = build_facebook_review(raw)
        encoded = json.dumps(result, ensure_ascii=False)
        self.assertEqual(result['source_id'], 'facebook_review')
        self.assertEqual(len(result['candidates']), 1)
        self.assertNotIn('SECRET', encoded)
        self.assertNotIn('我的私人留言', encoded)
        self.assertNotIn('private-id', encoded)
        self.assertNotIn('某人', encoded)
        self.assertNotIn('graph.facebook.com', encoded)
        self.assertNotIn('facebook_page:123', encoded)
        self.assertEqual(result['errors'], [{'code': 'http_403'}])
        context = result['candidates'][0]['review_context']
        self.assertEqual(context['page_handle'], 'example')
        self.assertEqual(context['official_link_count'], 2)
        self.assertEqual(context['discovered_links'][0]['url'], 'https://events.example/one')
        self.assertIn('unverified_fields', context['draft'])

    def test_image_only_post_gets_honest_draft(self):
        raw = {'status': 'partial', 'errors': [], 'page_status': [], 'candidates': [{
            'id': 'x', 'source_url': 'https://www.facebook.com/posts/2', 'title': '', 'post_text': '',
            'language_hits': [], 'comment_status': 'partial', 'comments_read': 0,
            'discovered_links': [], 'evidence': {}, 'comment_requests': []}]}
        row = build_facebook_review(raw)['candidates'][0]
        self.assertIn('圖片或附件', row['text'])
        self.assertEqual(row['review_status'], 'pending')


if __name__ == '__main__':
    unittest.main()
