import unittest

from scripts.update_manual_review_issue import build_body, pending_rows


class ManualReviewIssueTests(unittest.TestCase):
    def test_only_pending_facebook_rows_are_listed_without_commenter_identity(self):
        context = {'page_handle': 'example', 'post_excerpt': '台語故事，請看圖片',
                   'discovered_links': [{'url': 'https://example.org/event', 'is_page_author': None}],
                   'draft': {'unverified_fields': ['start_time', 'venue']}}
        audit = {'reviewed_at': '2026-09-19T12:00:00+08:00', 'decisions': [
            {'candidate_id': 'abc', 'source_id': 'facebook_review', 'source_url': 'https://facebook.com/post/1',
             'title': '故事活動', 'decision': 'pending', 'reason': 'comment_link_authorship_needs_review',
             'review_context': context},
            {'candidate_id': 'def', 'source_id': 'facebook_review', 'decision': 'duplicate'},
            {'candidate_id': 'ghi', 'source_id': 'opentix', 'decision': 'pending'}]}
        self.assertEqual(len(pending_rows(audit)), 1)
        body = build_body(audit, 'https://github.com/owner/repo/actions/runs/1')
        self.assertIn('故事活動', body)
        self.assertIn('comment_link_authorship_needs_review', body)
        self.assertIn('start_time、venue', body)
        self.assertIn('作者未確認', body)
        self.assertNotIn('def', body)
        self.assertNotIn('ghi', body)


if __name__ == '__main__':
    unittest.main()
