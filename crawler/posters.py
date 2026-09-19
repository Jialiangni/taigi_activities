"""Official event artwork only: structured event image or scoped article media."""
import re
from urllib.parse import urljoin, urlsplit, urlunsplit, quote

from .collection import Document

IMAGE_EXT = re.compile(r'\.(?:jpe?g|png|webp|gif)(?:$|[?])', re.I)
DECORATION = re.compile(r'(?:logo|favicon|placeholder|no[-_]?image|emoji|icon[_/.-]|'
                        r'/icons?/|/share/|accessibility|captcha|qrcode|qr_code|fbshare)', re.I)
CONTENT_CLASSES = {'post-body', 'article_content', 'article-content', 'entry-content',
                   'cp', 'userEdit', 'editor', 'edit-content', 'html', 'detail_pic',
                   'articleContent', 'news-detail-content', 'event-content'}


def excluded_context(node):
    while node:
        if node.tag in ('nav', 'footer', 'aside') or re.search(
                r'related|recommend|newslist|share|social|avatar|item-thumbnail',
                node.attrs.get('class', ''), re.I):
            return True
        node = node.parent
    return False


def image_url(value, base):
    if not isinstance(value, str) or not value.strip():
        return ''
    try:
        # Some culture portals publish Windows separators in image attributes.
        value = value.strip().replace('\\', '/')
        if value.startswith('//') and not value.startswith('///'):
            value = 'https:' + value
        p = urlsplit(urljoin(base, value))
        if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
            return ''
        if DECORATION.search(p.path):
            return ''
        if p.hostname == 'atpass.ntpclib.gov.tw' and p.path.startswith(('/img/', '/images/', '/template/')):
            return ''
        return urlunsplit((p.scheme, p.netloc, quote(p.path, safe='/%:@='),
                           quote(p.query, safe='=&%/:@,+;?'), ''))
    except (ValueError, UnicodeError):
        return ''


def images_in(node, base):
    for img in node.all('img'):
        if excluded_context(img):
            continue
        if any(str(img.attrs.get(k, '')).isdigit() and int(img.attrs[k]) < 100 for k in ('width', 'height')):
            continue
        raw = img.attrs.get('data-src') or img.attrs.get('src')
        url = image_url(raw, base)
        if not url:
            continue
        # Use the full-size file only when the publisher explicitly links it.
        if img.parent and img.parent.tag == 'a':
            full = image_url(img.parent.attrs.get('href'), base)
            if full and IMAGE_EXT.search(full):
                url = full
        yield url
    for anchor in node.all('a'):
        href = image_url(anchor.attrs.get('href'), base)
        if (not excluded_context(anchor) and href and IMAGE_EXT.search(href)
                and re.search(r'海報|活動圖片|宣傳|poster', anchor.text(), re.I)):
            yield href


def poster_url(html, base):
    doc = Document(html)
    host = urlsplit(base).hostname
    if host == 'www.accupass.com':
        # Never select organization avatars or recommended-event banners.
        from .sources.accupass import event_jsonld
        events = list(event_jsonld(doc))
        for event in events:
            if event.get('url') and event['url'].split('?')[0].rstrip('/') != base.split('?')[0].rstrip('/'):
                continue
            if not event.get('url') and len(events) != 1:
                continue
            values = event.get('image') or []
            for value in values if isinstance(values, list) else [values]:
                if isinstance(value, dict):
                    value = value.get('url') or value.get('contentUrl')
                image = image_url(value, base)
                if image:
                    return image
        return ''
    if host == 'www.gameislearning.url.tw':
        from .sources.gameislearning import poster_url as taigi_poster
        return taigi_poster(html, base)
    if host == 'www.typl.gov.tw':
        event_id = urlsplit(base).path.rstrip('/').rsplit('/', 1)[-1]
        for img in doc.root.all('img'):
            value = image_url(img.attrs.get('src'), base)
            if re.search(r'/FileUploads/Activity/' + re.escape(event_id) + r'\.(?:jpg|png|webp)$', value, re.I):
                return value
    if host == 'event.culture.tw':
        for node in doc.root.all():
            if node.attrs.get('id') == 'carouselExampleIndicators':
                return next(images_in(node, base), '')
    if host == 'www.tfam.museum':
        for node in doc.root.all():
            if node.attrs.get('id') == 'divImgs':
                return next(images_in(node, base), '')
    # Foundation post-body excludes Blogger headers and recommended posts.
    scopes = [n for n in doc.root.all() if n.has_class('post-body')]
    if not scopes:
        scopes = [n for n in doc.root.all() if n.tag == 'article' or
                  CONTENT_CLASSES.intersection(n.attrs.get('class', '').split())]
    for node in scopes:
        image = next(images_in(node, base), '')
        if image:
            return image
    return ''


def poster_fields(html, url):
    return {'cover_image': poster_url(html, url)}
