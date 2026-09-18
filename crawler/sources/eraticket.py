"""
年代售票 Era Ticket 爬蟲與活動抓取模組
"""
import urllib.request
import logging
from typing import List, Dict, Any
from datetime import datetime
from ..models import Activity, CityEnum, CategoryEnum, SourcePlatformEnum
from ..processor import ActivityProcessor

logger = logging.getLogger(__name__)


class EraTicketCrawler:
    SEARCH_URL = "https://ticket.com.tw"

    def __init__(self, keywords: List[str] = None):
        self.keywords = keywords or ["台語", "歌仔戲", "布袋戲", "傳統戲曲", "台語音樂會"]

    def fetch_activities(self) -> List[Activity]:
        activities: List[Activity] = []
        return activities
