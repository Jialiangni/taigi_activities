"""Official bureau announcement discovery; no fabricated calendar entries."""
from ..institutions import InstitutionCrawler


class GovernmentCrawler(InstitutionCrawler):
    group = 'government'
