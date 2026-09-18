"""Le Second Floor's publisher-provided Wix RSS feed."""
from ..web_sources import FeedCrawler
from ..collection import KEYWORDS


class LeChangCrawler(FeedCrawler):
    def __init__(self, keywords=None, max_pages=20):
        super().__init__('le_chang', 'https://www.lesecondfloor.com/blog-feed.xml', keywords or KEYWORDS, max_pages)
