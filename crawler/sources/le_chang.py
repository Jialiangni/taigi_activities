"""
樂暢親子共學 / 樂暢台語 活動抓取模組
"""
import logging
from typing import List, Dict, Any
from datetime import datetime
from ..models import Activity, CityEnum, CategoryEnum, SourcePlatformEnum
from ..processor import ActivityProcessor

logger = logging.getLogger(__name__)


class LeChangCrawler:
    """
    樂暢親子共學 (Le-tshiòng Taigi Kids Learning)
    專注於幼兒台語繪本、全台語故事、戶外生態台語體驗、親子共學共玩
    """
    def __init__(self):
        pass

    def fetch_activities(self) -> List[Activity]:
        activities: List[Activity] = []
        return activities
