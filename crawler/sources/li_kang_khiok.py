"""Foundation's official Blogger Atom feed, including rel=next pagination."""
from ..web_sources import FeedCrawler
from ..collection import KEYWORDS


class LiKangKhiokCrawler(FeedCrawler):
    def __init__(self, keywords=None, max_pages=20):
        super().__init__('li_kang_khiok', 'https://www.tgb.org.tw/feeds/posts/default?max-results=50',
                         keywords or KEYWORDS, max_pages,
                         feed_mirrors=('https://www.blogger.com/feeds/8088173083479680563/posts/default',))
