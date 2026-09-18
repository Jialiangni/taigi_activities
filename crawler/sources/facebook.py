"""Read authorized Page feeds, then filter their public posts locally by keyword."""
import re
from ..social import SocialCrawler, read_pages
from ..collection import CollectionError


class FacebookCrawler(SocialCrawler):
    source_id = 'facebook'
    required_env = ('FACEBOOK_ACCESS_TOKEN', 'FACEBOOK_PAGE_IDS')

    def read(self, client, result):
        base, token = self.graph_base(), self.env['FACEBOOK_ACCESS_TOKEN']
        for page in self.env['FACEBOOK_PAGE_IDS'].split(','):
            page = page.strip()
            if not re.fullmatch(r'\d+', page):
                raise CollectionError('numeric_facebook_page_ids_required')
            params = {'fields': 'id,message,permalink_url,created_time', 'limit': 100}
            try:
                for posts, ev in read_pages(client, base + '/' + page + '/feed', params, token, self.max_pages):
                    self.add_posts(result, posts, ev, 'message', 'permalink_url', 'created_time')
            except CollectionError as e:
                result.error('facebook_page:' + page, e)
