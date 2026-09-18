"""
Facebook 公開粉絲專頁與活動抓取模組
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


class FacebookCrawler:
    def __init__(self, access_token: str = "", target_pages: List[str] = None):
        self.access_token = access_token
        self.target_pages = target_pages or [
            "taigitv",
            "twlangcenter",
            "dadaochengtheater",
            "taipeiculture",
            "ntpcculture",
            "tyculture"
        ]

    def fetch_activities(self) -> List[Activity]:
        activities: List[Activity] = []
        if self.access_token:
            for page in self.target_pages:
                try:
                    params = {
                        "access_token": self.access_token,
                        "fields": "id,name,description,start_time,end_time,place,cover"
                    }
                    url = f"https://graph.facebook.com/v19.0/{page}/events?{urllib.parse.urlencode(params)}"
                    req = urllib.request.Request(url)
                    with urllib.request.urlopen(req, timeout=5) as response:
                        if response.status == 200:
                            data = json.loads(response.read().decode("utf-8")).get("data", [])
                            for ev in data:
                                act = self._parse_graph_event(ev, page)
                                if act:
                                    activities.append(act)
                except Exception as e:
                    logger.debug(f"Facebook query notice for {page}: {e}")
        return activities

    def _parse_graph_event(self, ev: Dict[str, Any], page_name: str) -> Activity:
        title = ev.get("name", "")
        if not title:
            return None

        desc = ev.get("description", "")
        place = ev.get("place", {})
        venue = place.get("name", "")
        location = place.get("location", {})
        address = f"{location.get('city', '')} {location.get('street', '')}".strip() or venue

        city = ActivityProcessor.detect_city(title + " " + desc, venue, address)
        category = ActivityProcessor.detect_category(title, desc)
        start_time = ev.get("start_time", datetime.now().isoformat())
        end_time = ev.get("end_time")
        event_id = ev.get("id", "")
        cover = ev.get("cover", {}).get("source", "")

        return Activity(
            id=f"fb_{event_id}",
            title=title,
            description=desc,
            city=city,
            category=category,
            start_time=start_time,
            end_time=end_time,
            venue=venue,
            address=address,
            organizer=f"FB: {page_name}",
            source_platform=SourcePlatformEnum.FACEBOOK,
            source_url=f"https://www.facebook.com/events/{event_id}" if event_id else f"https://www.facebook.com/{page_name}",
            cover_image=cover,
            price_info="詳見 FB 活動頁",
            is_free=True,
            tags=["Facebook", "社群活動", category.value, city.value]
        )
