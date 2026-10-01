import copy
import json
from pathlib import Path
import tempfile
import unittest
from scripts.meta_translate import MODEL, extract, translate


def response(text='Example 200'):
    return {'id': 'resp_test', 'model': MODEL, 'status': 'completed',
            'output': [{'type': 'reasoning', 'summary': []},
                       {'type': 'message', 'role': 'assistant', 'status': 'completed',
                        'content': [{'type': 'output_text', 'text': text}]}]}


class MetaTranslationTests(unittest.TestCase):
    def test_incomplete_refusal_and_wrong_model_fail(self):
        base = response()
        variants = []
        for key, val in [('status', 'incomplete'), ('model', 'another-model'), ('id', '')]:
            bad = copy.deepcopy(base); bad[key] = val; variants.append(bad)
        bad = copy.deepcopy(base)
        bad['output'][1]['content'] = [{'type': 'refusal', 'refusal': 'No'}]
        variants.append(bad)
        for bad in variants:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                extract(bad)

    def test_save_raw_text_no_quality_claim_and_no_resend(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'run'
            calls = []
            def send(body, key):
                calls.append(body)
                return response('Example 200\n')
            result = translate('Example 200', ['Example'], target, 'test-key', send)
            self.assertEqual((target / 'translation.txt').read_text(), 'Example 200\n')
            self.assertEqual(result['status'], 'needs_fact_review')
            self.assertFalse(result['facts_reviewed'])
            self.assertFalse(result['independent_naturalness_review'])
            with self.assertRaises(FileExistsError):
                translate('Example 200', ['Example'], target, 'test-key', send)
            self.assertEqual(len(calls), 1)
            self.assertNotIn('test-key', ''.join(p.read_text() for p in target.iterdir()))

    def test_missing_facts_preserve_draft(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'run'
            result = translate('Example 200', ['Example'], target, 'key', lambda *_: response('Example'))
            self.assertEqual(result['status'], 'missing_facts')
            self.assertEqual((target / 'translation.txt').read_text(), 'Example')

    def test_error_retained_and_no_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'run'
            def fail(*_):
                raise ValueError('Meta API HTTP 401; not retried')
            with self.assertRaises(ValueError):
                translate('Example 200', [], target, 'key', fail)
            self.assertEqual(json.loads((target / 'status.json').read_text())['status'], 'failed')
            with self.assertRaises(FileExistsError):
                translate('Example 200', [], target, 'key', fail)

    def test_missing_credentials_do_not_submit(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'run'
            with self.assertRaises(ValueError):
                translate('Example', [], target, '', lambda *_: self.fail('Unexpected API call'))
            self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
