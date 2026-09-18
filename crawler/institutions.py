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

    def __init__(self, keywords=None, max_pages=8):
        self.keywords, self.max_pages = keywords or KEYWORDS, max_pages

    def collect(self, client):
        from .sources.tmofa import TmofaCrawler
        return [(TmofaCrawler(self.keywords) if spec['id'] == 'tmofa' else WebsiteCrawler(spec, self.keywords, self.max_pages)).collect(client)
                for spec in registry() if spec['group'] == self.group]
