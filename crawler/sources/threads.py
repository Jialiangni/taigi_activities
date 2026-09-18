"""Official Threads keyword search with cursor pagination."""
from ..social import SocialCrawler, read_pages
from ..collection import CollectionError


class ThreadsCrawler(SocialCrawler):
    source_id = 'threads'
    required_env = ('THREADS_ACCESS_TOKEN',)

    def read(self, client, result):
        token = self.env['THREADS_ACCESS_TOKEN']
        for keyword in self.keywords:
            params = {'q': keyword, 'search_type': 'RECENT', 'search_mode': 'KEYWORD',
                      'fields': 'id,text,permalink,timestamp,username', 'limit': 50}
            try:
                for posts, ev in read_pages(client, 'https://graph.threads.com/v1.0/keyword_search', params, token, self.max_pages):
                    self.add_posts(result, posts, ev, 'text', 'permalink', 'timestamp')
            except CollectionError as e:
                result.error('threads_keyword:' + keyword, e)
