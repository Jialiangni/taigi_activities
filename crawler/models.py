"""
Data Models for Taigi Activities (Zero-dependency using dataclasses)
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


class CityEnum(str, Enum):
    TAIPEI = "臺北市"
    NEW_TAIPEI = "新北市"
    TAOYUAN = "桃園市"
    OTHER = "其他"


class CategoryEnum(str, Enum):
    STAGE_PLAY = "台語舞台劇"
    PERFORMANCE = "台語表演"
    STORY = "台語故事"
    PICTURE_BOOK = "台語繪本"
    EXPERIENCE = "台語體驗"
    TOUR = "台語導覽"
    OTHER = "台語活動"


class SourcePlatformEnum(str, Enum):
    OPENTIX = "OPENTIX 兩廳院"
    ERATICKET = "年代售票"
    ACCUPASS = "Accupass 活動通"
    LI_KANG_KHIOK = "李江却基金會"
    LE_CHANG = "樂暢親子共學"
    GAME_IS_LEARNING = "台語站"
    LIBRARIES = "北北桃市立圖書館"
    NATIONAL_LIBRARY = "國立臺灣圖書館"
    MUSEUMS = "美術館與博物館"
    GOVERNMENT = "北北桃市府局處"
    FACEBOOK = "Facebook"
    INSTAGRAM = "Instagram"
    THREADS = "Threads"
    GOOGLE_CALENDAR = "Google 日曆"


@dataclass
class Activity:
    id: str
    title: str
    description: str = ""
    city: CityEnum = CityEnum.TAIPEI
    district: str = ""
    category: CategoryEnum = CategoryEnum.STAGE_PLAY
    start_time: str = ""
    end_time: Optional[str] = None
    venue: str = ""
    address: str = ""
    organizer: str = ""
    source_platform: SourcePlatformEnum = SourcePlatformEnum.OPENTIX
    source_url: str = ""
    registration_url: str = ""
    cover_image: str = ""
    price_info: str = "費用未公告，請洽主辦單位"
    is_free: Optional[bool] = None
    tags: List[str] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["city"] = self.city.value if isinstance(self.city, CityEnum) else self.city
        d["category"] = self.category.value if isinstance(self.category, CategoryEnum) else self.category
        d["source_platform"] = self.source_platform.value if isinstance(self.source_platform, SourcePlatformEnum) else self.source_platform
        return d
