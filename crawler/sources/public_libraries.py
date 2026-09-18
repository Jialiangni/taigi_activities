"""Official activity/news discovery for all three city libraries."""
from ..institutions import InstitutionCrawler


class PublicLibrariesCrawler(InstitutionCrawler):
    group = 'public_libraries'
