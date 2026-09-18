"""Official Blogger feed plus article evidence and a session-oriented review queue."""
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urljoin, urlsplit
from ..web_sources import FeedCrawler
from ..collection import KEYWORDS, TAIPEI, Document, Result, CollectionError, canonical

URL = re.compile(r'https?://[^\s<>"\u3000]+')
DATE = re.compile(r'(?<![\d/])(?:(20\d{2})\s*[/年.-]\s*)?(\d{1,2})\s*[/月]\s*(\d{1,2})(?:日)?(?!\d)')


def content_links(body, base):
    doc = Document(body)
    links = [u for u, _, _ in doc.links(base)]
    for match in URL.finditer(doc.root.text()):
        try:
            links.append(canonical(match.group().rstrip('。，、；;）)')))
        except CollectionError:
            pass
    return list(dict.fromkeys(links))


def review_hints(row):
    """Dates are clues, never certified start times; retain past/ambiguous sessions."""
    body = row['text']
    # A URL path or signup URL is not an event date.
    masked = URL.sub(lambda m: ' ' * len(m.group()), body)
    hints = []
    published_year = (row['fields'].get('published_at') or '')[:4]
    for match in DATE.finditer(masked):
        explicit_year, month, day = match.groups()
        try:
            datetime(int(explicit_year or 2000), int(month), int(day))
        except ValueError:
            continue
        hints.append({'date_text': match.group(), 'year': int(explicit_year) if explicit_year else None,
                      'month': int(month), 'day': int(day),
                      'publication_year_hint': int(published_year) if published_year.isdigit() else None,
                      'context': body[max(0, match.start()-20):match.end()+180],
                      'review_status': 'pending'})
    row['fields']['session_hints'] = hints
    links = row['fields'].get('content_links', [])
    row['fields']['registration_links'] = [u for u in links if urlsplit(u).hostname == 'forms.gle' or
                                           (urlsplit(u).hostname == 'docs.google.com' and '/forms/' in urlsplit(u).path)]
    # Preserve all other links too: registration is not restricted to Google Forms.
    if hints and any(h['year'] is None for h in hints):
        if 'event_year_requires_review' not in row['issues']:
            row['issues'].append('event_year_requires_review')


class FoundationResult(Result):
    def to_dict(self):
        data = super().to_dict()
        data['review_queue'] = [
            {'candidate_id': row['id'], 'source_url': row['source_url'], 'title': row['title'],
             'session_hints': row['fields']['session_hints'],
             'content_links': row['fields'].get('content_links', []),
             'registration_links': row['fields']['registration_links'],
             'issues': row['issues'], 'review_status': 'pending'}
            for row in self.candidates if row['fields']['session_hints'] or row['fields']['registration_links']]
        return data


class LiKangKhiokCrawler(FeedCrawler):
    def __init__(self, keywords=None, max_pages=20, max_details=30, now=None):
        super().__init__('li_kang_khiok', 'https://www.tgb.org.tw/feeds/posts/default?max-results=50',
                         keywords or KEYWORDS, max_pages,
                         feed_mirrors=('https://www.blogger.com/feeds/8088173083479680563/posts/default',))
        self.max_details = max_details
        self.now = now or datetime.now(TAIPEI)

    def parse_page(self, text, evidence):
        rows, more = super().parse_page(text, evidence)  # validates XML before parsing below
        links_by_url = {}
        for entry in ET.fromstring(text).findall('{http://www.w3.org/2005/Atom}entry'):
            body = entry.find('{http://www.w3.org/2005/Atom}content')
            for link in entry.findall('{http://www.w3.org/2005/Atom}link'):
                if link.get('rel', 'alternate') == 'alternate' and link.get('href'):
                    url = canonical(link.get('href'))
                    links_by_url[url] = content_links(body.text if body is not None else '', url)
        for row in rows:
            row['fields']['content_links'] = links_by_url.get(row['source_url'], [])
            review_hints(row)
        return rows, more

    def priority(self, row):
        hints = row['fields']['session_hints']
        upcoming = False
        for hint in hints:
            year = hint['year'] or hint['publication_year_hint']
            try:
                upcoming |= datetime(year, hint['month'], hint['day']).date() >= self.now.date()
            except (TypeError, ValueError):
                pass
        return (upcoming, bool(hints), row['fields'].get('published_at') or '')

    def collect(self, client):
        result = FoundationResult(**super().collect(client).to_dict())
        result.method = 'official_feed_and_article_review'
        result.candidates = list({r['id']: r for r in result.candidates}.values())
        result.candidates.sort(key=self.priority, reverse=True)
        for index, row in enumerate(result.candidates):
            if index >= self.max_details:
                row['issues'].append('article_detail_budget_exhausted')
                continue
            url = row['source_url']
            try:
                if urlsplit(url).hostname != 'www.tgb.org.tw' or not re.fullmatch(r'/\d{4}/\d{2}/[^/]+\.html', urlsplit(url).path):
                    raise CollectionError('unapproved_foundation_article')
                html, evidence = client.get(url)
                if urlsplit(evidence['final_url']).hostname != 'www.tgb.org.tw':
                    raise CollectionError('unapproved_foundation_redirect')
                doc = Document(html)
                bodies = [n for n in doc.root.all() if n.has_class('post-body')]
                titles = [n for n in doc.root.all() if n.has_class('post-title') and n.has_class('entry-title')]
                if len(bodies) != 1 or not titles or not bodies[0].text().strip():
                    raise CollectionError('invalid_foundation_article')
                body = bodies[0]
                row['title'], row['text'] = titles[0].text().strip(), body.text().strip()
                # Re-parse only article anchors, not related posts or the site footer.
                links = []
                for a in body.all('a'):
                    if not a.attrs.get('href') or a.attrs['href'].startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                        continue
                    try:
                        links.append(canonical(urljoin(url, a.attrs.get('href', ''))))
                    except CollectionError:
                        pass
                links.extend(content_links(row['text'], url))
                row['fields']['content_links'] = list(dict.fromkeys(links))
                row['feed_evidence'], row['evidence'] = row['evidence'], evidence
                row['language_hits'] = [k for k in KEYWORDS if k in row['title'] + ' ' + row['text']]
                review_hints(row)
            except CollectionError as error:
                result.error(url, error)
                row['issues'].append('article_detail_unavailable')
        if len(result.candidates) > self.max_details:
            result.status = 'partial'
            result.notes.append('foundation_article_detail_limit_reached')
        result.candidates.sort(key=self.priority, reverse=True)
        result.notes.append('Review queue retains each date clue and signup link, including old posts with future sessions. '
                            'Publication year only affects priority; event years, shared times, venues and cancellation need manual review. '
                            'Images and date formats without recognized numeric month/day still need manual review. No automatic publication.')
        return result
