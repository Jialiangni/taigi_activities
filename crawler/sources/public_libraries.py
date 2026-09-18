"""
臺北市立圖書館、新北市立圖書館、桃園市立圖書館 台語活動抓取模組
"""
import logging
from typing import List, Dict, Any
from datetime import datetime
from ..models import Activity, CityEnum, CategoryEnum, SourcePlatformEnum
from ..processor import ActivityProcessor

logger = logging.getLogger(__name__)


class PublicLibrariesCrawler:
    """
    彙整北北桃公立圖書館台語推廣活動：
    - 臺北市立圖書館總館及各區分館（台灣母語故事坊、台語讀書會）
    - 新北市立圖書館總館及各區分館（新北愛閱讀、台語囡仔古巡迴）
    - 桃園市立圖書館總館及各區分館（故事志工台語說演、繪本工作坊）
    """
    def __init__(self):
        self.tpml_url = "https://tpml.gov.taipei"
        self.tphcc_url = "https://www.library.ntpc.gov.tw"
        self.typl_url = "https://www.typl.gov.tw"

    def fetch_activities(self) -> List[Activity]:
        activities: List[Activity] = []
        return activities
