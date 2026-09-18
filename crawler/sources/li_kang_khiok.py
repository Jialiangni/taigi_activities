"""
李江却台語文教基金會 串接與活動抓取模組
"""
import logging
from typing import List, Dict, Any
from datetime import datetime
from ..models import Activity, CityEnum, CategoryEnum, SourcePlatformEnum
from ..processor import ActivityProcessor

logger = logging.getLogger(__name__)


class LiKangKhiokCrawler:
    """
    李江却台語文教基金會 (Lí Kang-khiok Taiwanese Cultural & Educational Foundation)
    涵蓋：阿却賞台語文學獎、台語文研習、台語讀書會、台語文化講堂
    """
    OFFICIAL_URL = "https://www.tgb.org.tw"

    def __init__(self):
        pass

    def fetch_activities(self) -> List[Activity]:
        activities: List[Activity] = []
        # Support fetching from official RSS / website feeds
        return activities
