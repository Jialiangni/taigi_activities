import json
import socket
import ssl
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from crawler.collection import Client, CollectionError, Result
from crawler.collect import run


class DiagnosticTests(unittest.TestCase):
    def test_network_causes_and_credentials_are_not_serialized(self):
        cases = [(URLError(socket.gaierror(-2, 'secret')), 'dns'),
                 (URLError(TimeoutError('secret')), 'timeout'),
                 (URLError(ssl.SSLCertVerificationError(1, 'secret')), 'tls_certificate'),
                 (ConnectionResetError(54, 'secret'), 'connection')]
        for error, category in cases:
            with self.subTest(category=category):
                client = Client(delay=0)
                client.opener = Mock()
                client.opener.open.side_effect = error
                with self.assertRaises(CollectionError) as caught:
                    client.get('https://example.org/events?token=secret#secret', token='secret')
                result = Result('test', 'test')
                result.error('https://example.org/events?token=secret', caught.exception)
                record = result.errors[0]['diagnostics']
                self.assertEqual(record['category'], category)
                self.assertEqual(record['attempt'], 1)
                self.assertGreaterEqual(record['elapsed_ms'], 0)
                self.assertNotIn('secret', json.dumps(result.to_dict()))

    def test_retry_attempts_remain_visible_after_success(self):
        client = Client(delay=0)
        headers = Message(); headers['Retry-After'] = '2'
        failure = HTTPError('https://example.org', 429, 'secret', headers, None)
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'OK'
        response.headers = Message(); response.status = 200; response.url = 'https://example.org'
        client.opener = Mock(); client.opener.open.side_effect = [failure, response]
        with patch('crawler.collection.time.sleep'):
            text, evidence = client.get('https://example.org')
        self.assertEqual(text, 'OK')
        self.assertEqual(evidence['attempt'], 2)
        self.assertEqual(client.request_failures[0]['http_status'], 429)
        self.assertTrue(client.request_failures[0]['will_retry'])
        self.assertEqual(client.request_failures[0]['retry_after_seconds'], 2)
        self.assertEqual(len(client.requests), 1)

    def test_scoped_client_shares_diagnostics(self):
        client = Client(delay=0); client.diagnostic = Mock()
        scoped = client.scoped({'example.org'})
        scoped.opener = Mock(); scoped.opener.open.side_effect = TimeoutError()
        with self.assertRaises(CollectionError): scoped.get('https://example.org')
        self.assertEqual(len(client.request_failures), 1)
        client.diagnostic.assert_called_once()

    def test_unexpected_parser_error_has_location_without_exception_values(self):
        class Broken:
            def collect(self, client):
                raise ValueError('secret response with token=abc')
        with tempfile.TemporaryDirectory() as directory, patch('crawler.collect.collectors', return_value={'broken': Broken()}):
            report = run({}, directory)
            error = report['sources'][0]['errors'][0]
            self.assertEqual(error['code'], 'unexpected_ValueError')
            self.assertEqual(error['location'][-1]['function'], 'collect')
            self.assertTrue(error['location'][-1]['line'] > 0)
            self.assertNotIn('secret', json.dumps(report))
            self.assertNotIn('token=abc', json.dumps(report))
            data = json.loads((Path(directory) / 'broken.json').read_text())
            self.assertIn('request_failures', data)

    def test_http_failure_retains_both_attempts_and_final_status(self):
        client = Client(delay=0); client.opener = Mock()
        client.opener.open.side_effect = HTTPError('https://example.org', 503, 'secret', Message(), None)
        with patch('crawler.collection.time.sleep'), self.assertRaises(CollectionError) as caught:
            client.get('https://example.org')
        self.assertEqual([r['attempt'] for r in client.request_failures], [1, 2])
        self.assertFalse(client.request_failures[-1]['will_retry'])
        self.assertEqual(caught.exception.diagnostics['http_status'], 503)

    def test_actual_cli_summary_and_failure_exit_code(self):
        from crawler.collect import main
        report = {'sources': [{'source_id': 'example', 'status': 'failed', 'candidate_count': 0,
                              'failed_attempt_count': 2, 'duration_seconds': 1.2,
                              'errors': [{'code': 'http_503'}]}]}
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.json'; config.write_text('{}')
            summary = Path(directory) / 'summary.md'
            with patch('sys.argv', ['collect', '--config', str(config)]), \
                 patch.dict('os.environ', {'GITHUB_STEP_SUMMARY': str(summary)}), \
                 patch('crawler.collect.run', return_value=report):
                self.assertEqual(main(), 1)
            self.assertIn('| example | failed | 0 | 2 | 1.2 | http_503 |', summary.read_text())
            self.assertNotIn('API 設定', summary.read_text())
