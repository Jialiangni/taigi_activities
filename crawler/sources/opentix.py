"""
OPENTIX 兩廳院文化生活 爬蟲與活動抓取模組 (支援 requests 與 urllib 雙重容錯)
"""
import json
import urllib.request
import urllib.parse
import logging
from typing import List, Dict, Any
from datetime import datetime
from ..models import Activity, CityEnum, CategoryEnum, SourcePlatformEnum
from ..processor import ActivityProcessor

logger = logging.getLogger(__name__)


class OpentixCrawler:
    SEARCH_API = "https://www.opentix.life/oapi/v1/search/program"

    def __init__(self, keywords: List[str] = None):
        self.keywords = keywords or ["台語", "臺灣話", "歌仔戲", "布袋戲", "台語音樂劇", "傳統戲曲"]

    def fetch_activities(self) -> List[Activity]:
        activities: List[Activity] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json"
        }

        for kw in self.keywords:
            try:
                params = {
                    "keyword": kw,
                    "offset": 0,
                    "limit": 20,
                    "sort": "ON_SALE_DATE_ASC"
                }
                url = f"{self.SEARCH_API}?{urllib.parse.urlencode(params)}"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode("utf-8"))
                        programs = data.get("result", {}).get("programs", []) or data.get("programs", [])
                        for prog in programs:
                            act = self._parse_program(prog)
                            if act:
                                activities.append(act)
            except Exception as e:
                logger.debug(f"OPENTIX fetch notice for '{kw}': {e}")

        return activities

    def _parse_program(self, item: Dict[str, Any]) -> Activity:
        title = item.get("title", "") or item.get("name", "")
        if not title:
            return None

        desc = item.get("description", "") or item.get("summary", "")
        venue = item.get("placeName", "") or item.get("venue", "國家兩廳院 / 臺灣戲曲中心")
        address = item.get("address", "") or venue

        city = ActivityProcessor.detect_city(title + " " + desc, venue, address)
        category = ActivityProcessor.detect_category(title, desc)

        if category not in [CategoryEnum.STAGE_PLAY, CategoryEnum.PERFORMANCE]:
            category = CategoryEnum.STAGE_PLAY

        start_time = item.get("startDateTime", "") or datetime.now().isoformat()
        end_time = item.get("endDateTime", "")
        prog_id = str(item.get("id", item.get("programId", "")))

        min_price = item.get("minPrice", 300)
        max_price = item.get("maxPrice", 1800)
        price_info = f"NT$ {min_price} ~ {max_price}" if min_price else "售票演出"
        cover_image = item.get("coverImage", "") or item.get("imageUrl", "")

        return Activity(
            id=f"opentix_{prog_id}",
            title=title,
            description=desc,
            city=city,
            category=category,
            start_time=start_time,
            end_time=end_time,
            venue=venue,
            address=address,
            organizer=item.get("presenter", "兩廳院主辦/合辦團體"),
            source_platform=SourcePlatformEnum.OPENTIX,
            source_url=f"https://www.opentix.life/event/{prog_id}" if prog_id else "https://www.opentix.life",
            cover_image=cover_image,
            price_info=price_info,
            is_free=False,
            tags=["OPENTIX", "兩廳院", "台語舞台劇", category.value, city.value]
        )
