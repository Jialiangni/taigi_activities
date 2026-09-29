"""Bounded diagnostic metadata; never serialize response bodies or exception messages."""
import socket
import ssl
import traceback
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit, urlunsplit


def safe_url(url):
    try:
        p = urlsplit(url)
        if p.scheme not in ('http', 'https') or not p.hostname:
            return '[unavailable]'
        # Query strings, fragments and userinfo may contain credentials.
        return urlunsplit((p.scheme, p.hostname, p.path, '', ''))[:500]
    except ValueError:
        return '[invalid URL]'


def exception_info(error):
    cause = error.reason if isinstance(error, URLError) else error
    category = ('tls_certificate' if isinstance(cause, ssl.SSLCertVerificationError) else
                'tls' if isinstance(cause, ssl.SSLError) else
                'dns' if isinstance(cause, socket.gaierror) else
                'timeout' if isinstance(cause, TimeoutError) else
                'connection' if isinstance(cause, ConnectionError) else 'network')
    info = {'category': category, 'exception_type': type(error).__name__,
            'cause_type': type(cause).__name__}
    for attr in ('errno', 'verify_code'):
        value = getattr(cause, attr, None)
        if isinstance(value, int):
            info[attr] = value
    return info


def error_location(error):
    # No local values, exception messages, source lines or absolute home paths.
    return [{'file': Path(frame.filename).name, 'line': frame.lineno, 'function': frame.name}
            for frame in traceback.extract_tb(error.__traceback__)[-8:]]
