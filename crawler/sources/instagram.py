"""Facebook Login Instagram hashtag discovery using a real professional-account ID."""
import re
from urllib.parse import urlencode
from ..social import SocialCrawler, read_pages
from ..collection import CollectionError


class InstagramCrawler(SocialCrawler):
    source_id = 'instagram'
    required_env = ('INSTAGRAM_ACCESS_TOKEN', 'INSTAGRAM_USER_ID')

    def __init__(self, hashtags=None, **kwargs):
        super().__init__(**kwargs)
        self.hashtags = hashtags or ['台語活動', '台語繪本', '台語故事', '台語走讀', '台語工作坊']

    def read(self, client, result):
        base, token, user_id = self.graph_base(), self.env['INSTAGRAM_ACCESS_TOKEN'], self.env['INSTAGRAM_USER_ID']
        if not re.fullmatch(r'\d+', user_id):
            raise CollectionError('numeric_instagram_user_id_required')
        if len(set(self.hashtags)) > 30:
            raise CollectionError('hashtag_limit_exceeded')
        for tag in self.hashtags:
            try:
                url = base + '/ig_hashtag_search?' + urlencode({'user_id': user_id, 'q': tag})
                data, _ = client.json(url, token=token)
                if not isinstance(data, dict) or data.get('error') or not isinstance(data.get('data'), list):
                    raise CollectionError('hashtag_schema_changed')
                for item in data['data']:
                    hashtag_id = str(item.get('id', ''))
                    if not hashtag_id.isdigit():
                        raise CollectionError('invalid_hashtag_id')
                    params = {'user_id': user_id, 'fields': 'id,caption,permalink,timestamp', 'limit': 50}
                    # Official IG docs allow the same after cursor across different pages.
                    for posts, ev in read_pages(client, base + '/' + hashtag_id + '/recent_media', params, token, self.max_pages, allow_same_cursor=True):
                        self.add_posts(result, posts, ev, 'caption', 'permalink', 'timestamp')
            except CollectionError as e:
                result.error('instagram_hashtag:' + tag, e)
        result.notes.append('recent_media covers the platform-defined recent window; 30 unique hashtags per rolling 7 days across this account. Keep configured tags stable.')
