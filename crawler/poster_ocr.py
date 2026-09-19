"""Last-resort public poster OCR; separate recognition from date verification."""
import csv
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

from .collection import CollectionError, TAIPEI

MAX_BYTES = 8_000_000
MAX_POSTERS_PER_CLIENT = 30


def allowed_poster(url):
    from .sources.gameislearning import poster_url
    return poster_url('<img id="myPic" src="'+url+'">', 'https://www.gameislearning.url.tw/') == url


class PosterRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_poster(newurl): raise CollectionError('poster_redirect_not_allowed')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_poster(url):
    if not allowed_poster(url): raise CollectionError('poster_url_not_allowed')
    # Reuse the client's CA configuration, but restrict redirects before following.
    import ssl
    ctx = ssl.create_default_context()
    if Path('/etc/ssl/cert.pem').exists(): ctx.load_verify_locations('/etc/ssl/cert.pem')
    opener = build_opener(HTTPSHandler(context=ctx), PosterRedirect())
    try:
        with opener.open(Request(url, headers={'User-Agent':'TaigiActivities/1.0 (poster OCR)'}), timeout=25) as response:
            if response.headers.get_content_type() not in ('image/jpeg','image/png','image/webp','image/gif'):
                raise CollectionError('poster_not_image')
            raw = response.read(MAX_BYTES+1)
            if not raw or len(raw)>MAX_BYTES: raise CollectionError('poster_size_invalid')
            signature = (raw.startswith((b'\xff\xd8\xff', b'\x89PNG\r\n\x1a\n', b'GIF87a',b'GIF89a'))
                         or raw[:4]==b'RIFF' and raw[8:12]==b'WEBP')
            if not signature: raise CollectionError('poster_not_image')
            return raw, {'url':url,'final_url':response.url,'checked_at':datetime.now(TAIPEI).isoformat(timespec='seconds'),
                         'image_sha256':hashlib.sha256(raw).hexdigest()}
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise CollectionError('poster_fetch_failed') from error


def tsv_lines(value):
    lines = {}
    for row in csv.DictReader(io.StringIO(value), delimiter='\t'):
        if row.get('level') != '5' or not row.get('text','').strip(): continue
        key = tuple(row[k] for k in ('page_num','block_num','par_num','line_num'))
        line = lines.setdefault(key, {'text':[], 'confidence':100.0})
        confidence = float(row['conf'])
        if not math.isfinite(confidence) or not 0 <= confidence <= 100:
            raise CollectionError('poster_ocr_invalid_confidence')
        line['text'].append(row['text']); line['confidence'] = min(line['confidence'], confidence)
    return [{'text':' '.join(r['text']), 'confidence':r['confidence']} for r in lines.values()]


def recognize(raw):
    """No cloud keys or third-party uploads: run the configured local OCR engine."""
    with tempfile.TemporaryDirectory(prefix='taigi-ocr-') as temp:
        image = Path(temp)/'poster.img'; image.write_bytes(raw)
        binary = shutil.which('tesseract')
        try:
            if binary:
                result = subprocess.run([binary,str(image),'stdout','-l','chi_tra+eng','--psm','11','tsv'],
                                        capture_output=True, timeout=45, check=True)
                lines = tsv_lines(result.stdout.decode('utf-8'))
                engine = 'tesseract-chi_tra+eng-psm11'
            elif sys.platform == 'darwin' and shutil.which('swift'):
                cache = Path(tempfile.gettempdir()) / ('taigi-ocr-modules-' + str(os.getuid()))
                cache.mkdir(mode=0o700, exist_ok=True)
                if cache.is_symlink() or cache.stat().st_uid != os.getuid():
                    raise CollectionError('poster_ocr_cache_unsafe')
                env = dict(os.environ)
                env.setdefault('CLANG_MODULE_CACHE_PATH', str(cache))
                env.setdefault('SWIFT_MODULECACHE_PATH', str(cache))
                script = Path(__file__).resolve().parents[1]/'scripts/poster_ocr.swift'
                result = subprocess.run(['swift',str(script),str(image)], env=env,
                                        capture_output=True, timeout=240, check=True)
                payload = json.loads(result.stdout); lines, engine = payload['lines'], payload['engine']
            else: raise CollectionError('poster_ocr_engine_missing')
        except (subprocess.SubprocessError, ValueError, KeyError, UnicodeError, OSError) as error:
            raise CollectionError('poster_ocr_failed') from error
    if not lines or len(lines)>1500: raise CollectionError('poster_ocr_empty_or_oversized')
    for line in lines:
        if (not isinstance(line.get('text'),str) or not math.isfinite(line.get('confidence',float('nan')))
                or not 0 <= line['confidence'] <= 100): raise CollectionError('poster_ocr_invalid_output')
    return {'engine':engine,'lines':lines}


def read_poster(url, client):
    cache = getattr(client, '_poster_ocr_cache', None)
    if cache is None:
        cache = {}; setattr(client,'_poster_ocr_cache',cache)
    if url not in cache:
        attempts = getattr(client, '_poster_ocr_attempts', 0)
        if attempts >= MAX_POSTERS_PER_CLIENT:
            raise CollectionError('poster_ocr_run_limit')
        setattr(client, '_poster_ocr_attempts', attempts + 1)
        raw, evidence = download_poster(url)
        cache[url] = dict(recognize(raw), **evidence)
    return cache[url]


def poster_sessions(parsed, recognition):
    from .registration import same_identity, text_sessions, merge_sessions
    from .sources.gameislearning import DATE_RE, START_TIME_RE, _year
    # OCR spacing is not a semantic separator within Chinese/date notation.
    lines = [dict(r, text=re.sub(r'\s+','',r['text'])) for r in recognition['lines']]
    full_text = '\n'.join(r['text'] for r in lines)
    confident_text = '\n'.join(r['text'] for r in lines if r['confidence'] >= 85)
    if not same_identity(parsed, confident_text): raise CollectionError('poster_identity_uncertain')
    relevant = [r for r in lines if DATE_RE.search(r['text']) or START_TIME_RE.search(r['text'])
                or re.search(r'20\d{2}年|^20\d{2}$', r['text'])]
    if not relevant or any(r['confidence'] < 85 for r in relevant):
        raise CollectionError('poster_date_time_low_confidence')
    for line in lines:
        if re.search(r'[0-9OoIl][:：][0-9OoIl]', line['text']) and not START_TIME_RE.search(line['text']):
            raise CollectionError('poster_numeric_ambiguous')
    # A year explicitly written in the announcement may supplement a month/day
    # poster. Never use the crawl year or listing publication timestamp.
    text = confident_text
    year_evidence = None
    if not any(d[1] for d in DATE_RE.finditer(text)) and not re.search(r'20\d{2}年|(?m:^20\d{2}$)', text):
        notice = parsed['title'] + '\n' + parsed['text']
        declarations = [(int(m[1]), m[0]) for m in re.finditer(r'(20\d{2})年', notice)]
        declarations += [(_year(d[1], 0), d[0]) for d in DATE_RE.finditer(notice) if d[1]]
        years = {year for year,_ in declarations}
        if len(years) != 1:
            raise CollectionError('poster_year_not_explicit')
        year, quote = declarations[0]
        text = str(year) + '年\n' + text
        year_evidence = {'origin':'announcement','quote':quote,'year':year}
    if re.search(r'取消|延期|改期', full_text): raise CollectionError('poster_status_needs_review')
    rows = text_sessions(parsed, text)
    if any(len(r.get('end_time_variants', [])) > 1 for r in rows):
        raise CollectionError('poster_session_conflict')
    evidence = {k:recognition[k] for k in ('url','final_url','checked_at','image_sha256','engine')}
    if year_evidence: evidence['year_evidence'] = year_evidence
    evidence.update(text_sha256=hashlib.sha256(full_text.encode()).hexdigest(),
                    date_time_lines=relevant, sessions=rows)
    return merge_sessions(parsed, dict(parsed, sessions=rows, poster_ocr_evidence=evidence))


def supplement_activity(parsed, client):
    """Announcement -> linked registration text -> poster, without conflict overrides."""
    from .registration import resolve_registration
    if parsed['sessions'] and all(r.get('end_time') for r in parsed['sessions']): return parsed
    error = None
    try:
        resolved = resolve_registration(parsed, client)
        if resolved.get('registration_evidence'): return resolved
    except CollectionError as caught:
        error = caught
        if any(word in caught.code for word in ('conflict','mismatch','invalid','ambiguous','status','limit')):
            raise
    if not parsed.get('cover_image'):
        if error: raise error
        return parsed
    try:
        recognition = read_poster(parsed['cover_image'], client)
        parsed['poster_ocr_attempt'] = recognition
        return poster_sessions(parsed, recognition)
    except CollectionError as caught:
        # Preserve already explicit announcement start times; never add OCR guesses.
        if parsed['sessions']:
            return dict(parsed, enrichment_issue=caught.code)
        raise error or caught
