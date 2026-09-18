"""
Activity Processor, Deduplication, and Auto-Classification Engine
"""
import re
from typing import List, Optional
from datetime import datetime
from .models import Activity, CityEnum, CategoryEnum, SourcePlatformEnum


class ActivityProcessor:
    @staticmethod
    def detect_city(text: str, venue: str = "", address: str = "") -> CityEnum:
        combined = f"{text} {venue} {address}".lower()
        if any(kw in combined for kw in ["臺北", "台北", "大安", "中正", "信義", "中山", "大同", "萬華", "文山", "南港", "內湖", "士林", "北投", "松山", "國家戲劇院", "大稻埕", "西門", "華山", "松菸", "臺灣戲曲中心"]):
            return CityEnum.TAIPEI
        if any(kw in combined for kw in ["新北", "板橋", "三重", "中和", "永和", "新莊", "新店", "樹林", "鶯歌", "三峽", "淡水", "汐止", "瑞芳", "土城", "蘆洲", "五股", "泰山", "林口", "深坑", "石碇", "坪林", "三芝", "石門", "八里", "平溪", "雙溪", "貢寮", "金山", "萬里", "烏來", "新北藝文中心", "空軍三重一村"]):
            return CityEnum.NEW_TAIPEI
        if any(kw in combined for kw in ["桃園", "中壢", "平鎮", "八德", "楊梅", "大溪", "龜山", "蘆竹", "大園", "觀音", "新屋", "復興", "桃園展演中心", "中壢藝術館", "米倉劇場", "大溪木藝"]):
            return CityEnum.TAOYUAN
        return CityEnum.TAIPEI  # Default for Greater Taipei Area

    @staticmethod
    def detect_category(title: str, description: str = "", tags: List[str] = None) -> CategoryEnum:
        combined = f"{title} {description} {' '.join(tags or [])}".lower()
        
        # 1. 舞台劇
        if any(kw in combined for kw in ["舞台劇", "話劇", "戲劇節", "音樂劇", "劇場演出", "歌舞劇", "劇團", "戲劇", "巡演劇"]):
            return CategoryEnum.STAGE_PLAY
        
        # 2. 導覽 / 走讀
        if any(kw in combined for kw in ["導覽", "走讀", "散策", "踏查", "巡禮", "文史漫步", "巷弄探險", "文史導覽"]):
            return CategoryEnum.TOUR
        
        # 3. 繪本
        if any(kw in combined for kw in ["繪本", "圖畫書", "台語童書", "台語讀本", "親子共讀"]):
            return CategoryEnum.PICTURE_BOOK
        
        # 4. 故事
        if any(kw in combined for kw in ["故事", "講古", "囡仔古", "聽故事", "說故事", "講故事", "故事屋", "故事坊"]):
            return CategoryEnum.STORY
        
        # 5. 體驗 / 工作坊
        if any(kw in combined for kw in ["體驗", "工作坊", "手作", "烘焙", "研習", "營隊", "料理", "互動體驗", "桌遊", "闖關"]):
            return CategoryEnum.EXPERIENCE
        
        # 6. 表演 (歌仔戲、布袋戲、說唱、音樂會、脫口秀)
        if any(kw in combined for kw in ["表演", "歌仔戲", "布袋戲", "掌中戲", "音樂會", "說唱", "唸歌", "相聲", "脫口秀", "演唱會", "傳統戲曲", "合唱團", "皮影戲"]):
            return CategoryEnum.PERFORMANCE
        
        return CategoryEnum.STAGE_PLAY

    @classmethod
    def clean_and_normalize(cls, activities: List[Activity]) -> List[Activity]:
        """Deduplicate and normalize activities list"""
        seen_keys = set()
        cleaned: List[Activity] = []

        for act in activities:
            # Generate deduplication key based on title + start_time
            normalized_title = re.sub(r'[\s【】（）()\[\]\-_]', '', act.title)
            date_key = act.start_time[:10] if len(act.start_time) >= 10 else act.start_time
            dedup_key = f"{normalized_title}_{date_key}"

            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            # Re-verify city and category if ambiguous
            if act.city == CityEnum.OTHER:
                act.city = cls.detect_city(act.title, act.venue, act.address)
            
            cleaned.append(act)

        # Sort activities by start_time ascending
        cleaned.sort(key=lambda x: x.start_time)
        return cleaned
