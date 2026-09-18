"""
Instagram 標籤與推廣貼文解析模組
"""
import urllib.request
import urllib.parse
import json
import logging
from typing import List, Dict, Any
from datetime import datetime
from ..models import Activity, CityEnum, CategoryEnum, SourcePlatformEnum
from ..processor import ActivityProcessor

logger = logging.getLogger(__name__)


class InstagramCrawler:
    def __init__(self, access_token: str = "", hashtags: List[str] = None):
        self.access_token = access_token
        self.hashtags = hashtags or ["台語活動", "台語繪本", "台語故事", "台語走讀", "台語工作坊"]

    def fetch_activities(self) -> List[Activity]:
        activities: List[Activity] = []
        if self.access_token:
            for tag in self.hashtags:
                try:
                    params = {
                        "user_id": "me",
                        "q": tag,
                        "access_token": self.access_token
                    }
                    url = f"https://graph.facebook.com/v19.0/ig_hashtag_search?{urllib.parse.urlencode(params)}"
                    req = urllib.request.Request(url)
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        if resp.status == 200:
                            tag_id = json.loads(resp.read().decode("utf-8")).get("data", [{}])[0].get("id")
                            if tag_id:
                                media_params = {
                                    "access_token": self.access_token,
                                    "fields": "id,caption,media_url,timestamp,permalink"
                                }
                                media_url = f"https://graph.facebook.com/v19.0/{tag_id}/recent_media?{urllib.parse.urlencode(media_params)}"
                                req2 = urllib.request.Request(media_url)
                                with urllib.request.urlopen(req2, timeout=5) as m_resp:
                                    if m_resp.status == 200:
                                        data = json.loads(m_resp.read().decode("utf-8")).get("data", [])
                                        for post in data:
                                            act = self._parse_post(post, tag)
                                            if act:
                                                activities.append(act)
                except Exception as e:
                    logger.debug(f"Instagram notice for #{tag}: {e}")
        return activities

    def _parse_post(self, post: Dict[str, Any], tag: str) -> Activity:
        caption = post.get("caption", "")
        if not caption:
            return None

        lines = [l.strip() for l in caption.split("\n") if l.strip()]
        title = lines[0] if lines else f"IG 台語活動 #{tag}"

        city = ActivityProcessor.detect_city(caption)
        category = ActivityProcessor.detect_category(title, caption)
        post_id = post.get("id", "")

        return Activity(
            id=f"ig_{post_id}",
            title=title[:60],
            description=caption,
            city=city,
            category=category,
            start_time=post.get("timestamp", datetime.now().isoformat()),
            venue="請見 IG 貼文詳情",
            address=city.value,
            organizer=f"IG: #{tag}",
            source_platform=SourcePlatformEnum.INSTAGRAM,
            source_url=post.get("permalink", "https://www.instagram.com"),
            cover_image=post.get("media_url", ""),
            price_info="請見貼文說明",
            is_free=True,
            tags=["Instagram", f"#{tag}", category.value, city.value]
        )
