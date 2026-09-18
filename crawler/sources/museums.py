"""Official museum announcement discovery; no static or sample events."""
from ..institutions import InstitutionCrawler


class MuseumsCrawler(InstitutionCrawler):
    group = 'museums'
