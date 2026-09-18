import json
import unittest
from urllib.error import HTTPError, URLError

from crawler.audit_endpoints import probe


URL = 'https://example.org/search'


class Response:
    status = 200
    headers = {'Content-Type': 'application/json'}

    def __init__(self, body, url=URL):
        self.body = body
        self.url = url

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, size):
        return self.body[:size]


class EndpointAuditTests(unittest.TestCase):
    def run_probe(self, body):
        return probe('test', URL, 'events', opener=lambda *a, **k: Response(body))

    def test_failures_are_not_empty_success(self):
        for error, status in [(HTTPError(URL, 404, '', {}, None), 'http_error'),
                              (URLError('unreachable'), 'network_error')]:
            def fail(*args, **kwargs):
                raise error
            result = probe('test', URL, 'events', opener=fail)
            self.assertEqual(result['status'], status)
            self.assertNotIn('items_received', result)

    def test_wrong_schema_and_html_are_not_empty_results(self):
        for raw in (b'<html>Login</html>', b'{}', b'{"events":null}', b'[]'):
            self.assertEqual(self.run_probe(raw)['status'], 'invalid_response')

    def test_empty_and_nonempty_do_not_certify_crawler(self):
        for events, status in [([], 'empty_response'), ([{'id': '1'}], 'response_received')]:
            result = self.run_probe(json.dumps({'data': {'events': events}}).encode())
            self.assertEqual(result['status'], status)
            self.assertEqual(result['items_received'], len(events))
            self.assertFalse(result['crawler_verified'])

    def test_redirect_to_login_is_not_success(self):
        result = probe('test', URL, 'events', opener=lambda *a, **k: Response(
            b'{"events":[]}', 'https://example.org/login'))
        self.assertEqual(result['status'], 'unexpected_redirect')


if __name__ == '__main__':
    unittest.main()
