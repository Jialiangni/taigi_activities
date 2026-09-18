"""
Accupass 活動通 爬蟲與資料抓取模組 (支援 requests 與 urllib 雙重容錯)
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


class AccupassCrawler:
    SEARCH_API = "https://api.accupass.com/v3/search"

    def __init__(self, keywords: List[str] = None):
        self.keywords = keywords or ["台語", "台灣話", "閩南語", "囡仔古", "台語故事", "台語繪本", "台語導覽", "台語體驗"]

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
                    "page": 1,
                    "size": 20,
                    "city": "all",
                    "sort": "start_time"
                }
                url = f"{self.SEARCH_API}?{urllib.parse.urlencode(params)}"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode("utf-8"))
                        events = data.get("data", {}).get("events", []) or data.get("events", [])
                        for ev in events:
                            act = self._parse_event(ev)
                            if act:
                                activities.append(act)
            except Exception as e:
                logger.debug(f"Accupass fetch notice for '{kw}': {e}")

        return activities

    def _parse_event(self, item: Dict[str, Any]) -> Activity:
        title = item.get("name", "") or item.get("title", "")
        if not title:
            return None

        desc = item.get("summary", "") or item.get("description", "")
        venue = item.get("address", "") or item.get("venue", "") or ""
        address = item.get("fullAddress", "") or venue

        city = ActivityProcessor.detect_city(title + " " + desc, venue, address)
        category = ActivityProcessor.detect_category(title, desc)

        start_time = item.get("startDateTime", "") or datetime.now().isoformat()
        end_time = item.get("endDateTime", "")
        event_id = str(item.get("id", item.get("eventId", "")))

        price_info = "免費" if item.get("isFree", True) else f"NT$ {item.get('minPrice', '300')} 起"
        cover_image = item.get("coverUrl", "") or item.get("photoUrl", "")

        return Activity(
            id=f"accupass_{event_id}",
            title=title,
            description=desc,
            city=city,
            category=category,
            start_time=start_time,
            end_time=end_time,
            venue=venue,
            address=address,
            organizer=item.get("orgName", "Accupass 主辦單位"),
            source_platform=SourcePlatformEnum.ACCUPASS,
            source_url=f"https://www.accupass.com/event/{event_id}" if event_id else "https://www.accupass.com",
            cover_image=cover_image,
            price_info=price_info,
            is_free=item.get("isFree", True),
            tags=["Accupass", "台語活動", category.value, city.value]
        )
