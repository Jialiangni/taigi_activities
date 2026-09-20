import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, Mock
from urllib.error import HTTPError

from crawler import ai_editorial as ai
from crawler.collection import TAIPEI, CollectionError
from crawler.models import Activity
from crawler.taiwanese_dictionary import lookup_taiwanese, parse_entry


SUMMARY = '王老師講故事，介紹故事內底的人物佮生活。'
DESCRIPTION = '王老師講故事，介紹故事內底的人物佮生活。\n\n這場活動愛事先報名。'


class FakeAI:
    model = 'fixture-model'

    def __init__(self, fail=None, terms=None):
        self.total_calls = 0
        self.calls = []
        self.fail = fail
        self.terms = terms or []

    def generate(self, instructions, payload, schema, stage):
        self.total_calls += 1
        self.calls.append({'stage': stage})
        if self.fail:
            raise ai.EditorialError(self.fail)
        if stage == 'review':
            return {'facts_match': True, 'natural_taiwanese': True,
                    'people_and_content_complete': True, 'issues': [],
                    'evidence': [{'claim': '王老師講故事', 'quote': '王老師講故事'},
                                 {'claim': '愛事先報名', 'quote': '需要事先報名'}]}
        return {'summary_taigi': SUMMARY, 'description_taigi': DESCRIPTION,
                'uncertain_terms': self.terms if stage == 'draft' else []}


class AIEditorialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'data').mkdir()
        self.path = self.root / 'data/ai_taigi.json'
        self.state = {'schema_version': 1, 'protected_activity_ids': ['old'],
                      'editions': {}, 'attempts': {}, 'daily_usage': {}}
        ai.save_json(self.path, self.state)
        for name, data in [('ui_taigi.json', {}), ('accupass_editorial.json', []), ('opentix_editorial.json', [])]:
            ai.save_json(self.root / 'data' / name, data)
        (self.root / 'TAIGI_EDITORIAL.md').write_text('保留活動事實，使用自然台語。')
        self.activity = Activity(id='new', title='台語故事',
                                 description='王老師講故事，介紹故事裡的人物與生活。需要事先報名。',
                                 start_time='2027-01-01T10:00:00+08:00', source_url='https://example.org/event')
        self.now = datetime(2026, 9, 20, 12, tzinfo=TAIPEI)

    def run_edit(self, client, activities=None, **kwargs):
        return ai.enrich(activities or [self.activity], self.root, client, now=kwargs.pop('now', self.now), **kwargs)

    def test_old_records_are_protected_even_after_guide_or_source_change(self):
        old = copy.deepcopy(self.activity)
        old.id = 'old'
        client = FakeAI()
        result = self.run_edit(client, [old])
        self.assertEqual(result['decisions'][0]['status'], 'existing_copy_preserved')
        old.description = '原文改過也不自動重寫已存在的活動。'
        (self.root / 'TAIGI_EDITORIAL.md').write_text('新的編輯規範')
        self.run_edit(client, [old])
        self.assertEqual(client.total_calls, 0)

    def test_new_copy_is_cached_without_overwriting_manual_or_original_data(self):
        before = self.activity.to_dict()
        client = FakeAI()
        self.run_edit(client)
        self.assertEqual(client.total_calls, 3)
        saved = ai.load_state(self.path)
        self.assertEqual(ai.approved_edition(before, saved)['summary_taigi'], SUMMARY)
        (self.root / 'TAIGI_EDITORIAL.md').write_text('改規範不能造成舊稿重寫')
        self.run_edit(client)
        self.assertEqual(client.total_calls, 3)
        self.assertEqual(self.activity.to_dict(), before)
        self.assertEqual(json.loads((self.root / 'data/ui_taigi.json').read_text()), {})

    def test_existing_translations_and_editorial_ids_never_generate(self):
        client = FakeAI()
        ai.save_json(self.root / 'data/ui_taigi.json', {self.activity.description: '已校訂台文'})
        self.run_edit(client)
        ai.save_json(self.root / 'data/ui_taigi.json', {})
        ai.save_json(self.root / 'data/opentix_editorial.json', [{'activity_id': 'new'}])
        self.run_edit(client)
        self.assertEqual(client.total_calls, 0)

    def test_only_changed_new_session_is_invalidated(self):
        client = FakeAI()
        self.run_edit(client)
        self.activity.venue = '改場地'
        self.assertIsNone(ai.approved_edition(self.activity.to_dict(), ai.load_state(self.path)))
        self.run_edit(client)
        self.assertEqual(client.total_calls, 6)
        self.assertEqual(ai.approved_edition(self.activity.to_dict(), ai.load_state(self.path))['binding']['venue'], '改場地')

    def test_missing_api_key_preserves_original_and_does_not_consume_attempts(self):
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}):
            result = self.run_edit(None)
        self.assertEqual(result['decisions'][0]['status'], 'missing_api_key')
        self.assertEqual(ai.load_state(self.path)['attempts'], {})

    def test_failed_review_is_not_published_and_retries_are_bounded(self):
        client = FakeAI(fail='review_failed')
        self.run_edit(client)
        self.run_edit(client)
        self.assertEqual(client.total_calls, 1)
        self.run_edit(client, now=self.now + timedelta(days=1))
        result = self.run_edit(client, now=self.now + timedelta(days=2))
        self.assertEqual(client.total_calls, 2)
        self.assertEqual(result['decisions'][0]['status'], 'needs_attention')
        self.assertEqual(ai.load_state(self.path)['editions'], {})

    def test_daily_limit_and_service_circuit_breaker(self):
        activities = [Activity(**dict(self.activity.to_dict(), id='new-' + str(i))) for i in range(7)]
        client = FakeAI()
        report = self.run_edit(client, activities)
        self.assertEqual(client.total_calls, ai.MAX_DAILY * 3)
        self.assertEqual(sum(d['status'] == 'daily_limit' for d in report['decisions']), 2)
        self.run_edit(client, activities)
        self.assertEqual(client.total_calls, ai.MAX_DAILY * 3)
        ai.save_json(self.path, self.state)
        client = FakeAI(fail='api_http_401')
        report = self.run_edit(client, activities)
        self.assertEqual(client.total_calls, 1)
        self.assertEqual(report['decisions'][1]['status'], 'service_unavailable')

    def test_dictionary_must_be_real_success_and_is_saved(self):
        lookup = Mock(return_value={'query': '人物', 'status': 'ok', 'readings': []})
        client = FakeAI(terms=['人物'])
        self.run_edit(client, lookup=lookup)
        lookup.assert_called_once_with('人物')
        self.assertEqual(ai.load_state(self.path)['editions']['new']['dictionary_evidence'][0]['query'], '人物')
        ai.save_json(self.path, self.state)
        lookup.return_value = {'status': 'not_found'}
        client = FakeAI(terms=['人物'])
        result = self.run_edit(client, lookup=lookup)
        self.assertEqual(client.total_calls, 1)
        self.assertEqual(result['decisions'][0]['reason'], 'dictionary_unresolved')
        self.assertEqual(ai.load_state(self.path)['editions'], {})

    def test_review_flags_quotes_and_numbers_are_enforced(self):
        for mutation in ('flag', 'quote', 'claim', 'number', 'uncertain'):
            client = FakeAI()
            original = client.generate
            def generate(instructions, payload, schema, stage):
                data = original(instructions, payload, schema, stage)
                if stage == 'review':
                    if mutation == 'flag': data['facts_match'] = False
                    if mutation == 'quote': data['evidence'][0]['quote'] = '來源沒有的話'
                    if mutation == 'claim': data['evidence'][0]['claim'] = '成稿沒有的話'
                if stage == 'edit':
                    if mutation == 'number': data['description_taigi'] += '費用999元'
                    if mutation == 'uncertain': data['uncertain_terms'] = ['疑詞']
                return data
            client.generate = generate
            with self.subTest(mutation=mutation), self.assertRaises(ai.EditorialError):
                ai.write_edition(self.activity.to_dict(), client, '規範')

    def test_no_paid_generation_before_source_gates(self):
        import main
        with patch('main.load_verified', side_effect=ValueError('source failed')), patch.object(ai, 'enrich') as enrich:
            with self.assertRaises(ValueError): main.build(self.root, True, True)
            enrich.assert_not_called()
        with self.assertRaises(ValueError): main.build(self.root, False, True)

    def test_display_uses_ai_only_when_matching_and_keeps_manual_precedence(self):
        from build_html import generate_single_html
        client = FakeAI()
        self.run_edit(client)
        state = ai.load_state(self.path)
        # Use a known-good model object but with our isolated AI fixture content.
        self.activity.raw_metadata = {'verified_at': self.now.isoformat()}
        with patch('build_html.load_state', return_value=state), patch('build_html.session_editions', return_value=[]):
            html = Path(generate_single_html([self.activity], str(self.root / 'index.html'))).read_text()
        self.assertIn(SUMMARY, html)
        self.activity.description += '來源修訂'
        with patch('build_html.load_state', return_value=state), patch('build_html.session_editions', return_value=[]):
            html = Path(generate_single_html([self.activity], str(self.root / 'index.html'))).read_text()
        self.assertNotIn(SUMMARY, html)
        self.activity.description = state['editions']['new']['binding']['description']
        manual = {'activity_id': 'new', 'binding': {}, 'summary_taigi': '編輯定稿摘要', 'description_taigi': '編輯定稿完整介紹'}
        with patch('build_html.load_state', return_value=state), patch('build_html.session_editions', return_value=[manual]):
            html = Path(generate_single_html([self.activity], str(self.root / 'index.html'))).read_text()
        self.assertIn('編輯定稿摘要', html)
        self.assertNotIn(SUMMARY, html)

    def test_responses_transport_uses_strict_schema_and_no_secret_in_errors(self):
        client = ai.ResponsesClient('private-key')
        payload = {'status': 'completed', 'id': 'test-response', 'output': [{'type': 'message', 'content': [
            {'type': 'output_text', 'text': json.dumps({'summary_taigi': SUMMARY, 'description_taigi': DESCRIPTION, 'uncertain_terms': []})}]}]}
        response = Mock()
        response.read.return_value = json.dumps(payload).encode()
        cm = Mock()
        cm.__enter__ = Mock(return_value=response)
        cm.__exit__ = Mock(return_value=False)
        client.opener = Mock()
        client.opener.open.return_value = cm
        client.generate('規範', {'activity': 'source'}, ai.COPY_SCHEMA, 'draft')
        request = client.opener.open.call_args[0][0]
        request_body = json.loads(request.data)
        self.assertEqual(request.full_url, 'https://api.openai.com/v1/responses')
        self.assertFalse(request_body['store'])
        self.assertTrue(request_body['text']['format']['strict'])
        self.assertNotIn('private-key', json.dumps(client.calls))
        payload['status'] = 'incomplete'
        response.read.return_value = json.dumps(payload).encode()
        with self.assertRaisesRegex(ai.EditorialError, 'api_incomplete'):
            client.generate('規範', {}, ai.COPY_SCHEMA, 'draft')
        client.opener.open.side_effect = HTTPError(request.full_url, 401, 'private-key', {}, None)
        with self.assertRaises(ai.EditorialError) as caught:
            client.generate('規範', {}, ai.COPY_SCHEMA, 'draft')
        self.assertEqual(str(caught.exception), 'api_http_401')
        with self.assertRaisesRegex(ai.EditorialError, 'api_redirect_rejected'):
            ai.NoRedirect().redirect_request(None)
        with self.assertRaisesRegex(ai.EditorialError, 'input_too_large'):
            client.generate('x' * 50001, {}, ai.COPY_SCHEMA, 'draft')

    def test_refusal_and_malformed_model_output_never_become_copy(self):
        for output in (None, [{'type': 'message', 'content': [{'type': 'refusal', 'refusal': 'no'}]}],
                       [{'type': 'message', 'content': [{'type': 'output_text', 'text': '{}'}]}]):
            client = ai.ResponsesClient('unused')
            response = Mock()
            response.read.return_value = json.dumps({'status': 'completed', 'output': output}).encode()
            cm = Mock()
            cm.__enter__ = Mock(return_value=response)
            cm.__exit__ = Mock(return_value=False)
            client.opener = Mock()
            client.opener.open.return_value = cm
            with self.subTest(output=output), self.assertRaises(ai.EditorialError):
                client.generate('規範', {}, ai.COPY_SCHEMA, 'draft')

    def test_dictionary_error_is_distinct_from_missing_word(self):
        with patch('crawler.taiwanese_dictionary.Client') as cls:
            cls.return_value.json.side_effect = CollectionError('http_404')
            self.assertEqual(lookup_taiwanese('人物')['status'], 'not_found')
            cls.return_value.json.side_effect = CollectionError('network_or_tls_error')
            self.assertEqual(lookup_taiwanese('人物')['status'], 'service_error')
        with self.assertRaises(ValueError):
            parse_entry({'t': '別詞', 'h': []}, '人物')
