"""
Threads 貼文與即時台語活動抓取模組
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


class ThreadsCrawler:
    def __init__(self, keywords: List[str] = None):
        self.keywords = keywords or ["台語活動", "台語走讀", "台語舞台劇", "台語故事屋", "台語聚會"]

    def fetch_activities(self) -> List[Activity]:
        activities: List[Activity] = []
        return activities

    def parse_threads_post(self, post_text: str, author: str, post_url: str, post_time: str = None) -> Activity:
        lines = [l.strip() for l in post_text.split("\n") if l.strip()]
        title = lines[0] if lines else "Threads 台語活動分享"

        city = ActivityProcessor.detect_city(post_text)
        category = ActivityProcessor.detect_category(title, post_text)

        return Activity(
            id=f"threads_{abs(hash(post_url or post_text))}",
            title=title[:60],
            description=post_text,
            city=city,
            category=category,
            start_time=post_time or datetime.now().isoformat(),
            venue="詳見 Threads 貼文",
            address=city.value,
            organizer=f"@{author}",
            source_platform=SourcePlatformEnum.THREADS,
            source_url=post_url or "https://www.threads.net",
            cover_image="",
            price_info="免費 / 詳見貼文",
            is_free=True,
            tags=["Threads", "社群活動", category.value, city.value]
        )
