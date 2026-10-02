import copy
import json
import unittest

from crawler.accupass_text_review import digest
from crawler.collection import CollectionError
from crawler.reviewed_announcements import check, public_form_content


class ReviewedFormTests(unittest.TestCase):
    url = 'https://docs.google.com/forms/d/e/public-form/viewform?usp=send_form'

    def setUp(self):
        self.payload = [None] * 15
        self.payload[14] = 'e/public-form'
        self.payload[1] = ['台語活動 10/3 14:00 免費', [['報名須知', '限30名']], None,
                           None, None, None, None, ['報名已額滿'], '台語親子活動']

    def page(self, payload=None, chrome='登入 下一步', action=None):
        action = action or self.url.replace('viewform', 'formResponse')
        return ('<title>台語親子活動</title><form action="' + action + '">台語活動 10/3 14:00 免費</form>'
                + '<div>' + chrome + '</div><script>var FB_PUBLIC_LOAD_DATA_ = '
                + json.dumps(payload or self.payload, ensure_ascii=False) + ';</script>')

    def test_chrome_locale_is_ignored_but_author_changes_are_blocked(self):
        contract = {'content_version': 3, 'content_sha256': digest(public_form_content(self.page(), self.url)),
                    'sessions': []}
        check(self.page(chrome='Sign in Next'), self.url, contract)
        for index, value in ((0, '台語活動改期 10/4'), (1, [['報名須知', '限20名']]),
                             (7, ['活動取消']), (8, '另一場活動')):
            changed = copy.deepcopy(self.payload)
            changed[1][index] = value
            with self.subTest(index=index), self.assertRaisesRegex(CollectionError, 'content_changed'):
                check(self.page(changed), self.url, contract)

    def test_closed_malformed_wrong_identity_and_redirect_forms_fail(self):
        wrong = copy.deepcopy(self.payload)
        wrong[14] = 'e/other-form'
        for html in ('<p>報名已額滿</p>', self.page().replace('<form ', '<div ').replace('</form>', '</div>'),
                     self.page(wrong), self.page(action='https://evil.org/forms/d/e/public-form/formResponse'),
                     '<script>FB_PUBLIC_LOAD_DATA_ = broken;</script>'):
            with self.subTest(html=html), self.assertRaises(CollectionError):
                public_form_content(html, self.url)

    def test_old_full_page_contracts_are_not_silently_migrated(self):
        from crawler.candidate_triage import document
        contract = {'content_version': 2, 'content_sha256': digest(document(self.page(), self.url)), 'sessions': []}
        check(self.page(), self.url, contract)
        with self.assertRaisesRegex(CollectionError, 'content_changed'):
            check(self.page(chrome='Sign in Next'), self.url, contract)
