"""Institution registry and grouped official-site collectors."""
import json
from pathlib import Path
from .collection import Collector, KEYWORDS
from .web_sources import WebsiteCrawler

REGISTRY = Path(__file__).resolve().parents[1] / 'data/source_registry.json'


def registry():
    return json.loads(REGISTRY.read_text(encoding='utf-8'))['sources']


class InstitutionCrawler(Collector):
    group = ''

    def __init__(self, keywords=None, max_pages=30):
        self.keywords, self.max_pages = keywords or KEYWORDS, max_pages

    def collect(self, client):
        from .library_sources import LibraryListingCrawler
        from .sources.tmofa import TmofaCrawler
        from .sources.tfam import TfamCrawler
        return [(TfamCrawler(self.keywords) if spec['id'] == 'tfam' else TmofaCrawler(self.keywords) if spec['id'] == 'tmofa' else (LibraryListingCrawler if spec.get('collector') == 'library_listing' else WebsiteCrawler)(spec, self.keywords, self.max_pages)).collect(client)
                for spec in registry() if spec['group'] == self.group]
