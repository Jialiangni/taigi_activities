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
        if any(kw in combined for kw in ["桃園", "中壢", "平鎮", "八德", "楊梅", "大溪", "龜山", "蘆竹", "大園", "觀音", "新屋", "復興", "桃園展演中心", "中壢藝術館", "米倉劇場", "大溪木藝", "青埔"]):
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
    def assign_representative_image(cls, act: Activity):
        """
        確保每個活動都擁有高度貼合實際活動現場的專屬圖片：
        1. 若爬蟲有抓取到官方活動封面（如 Accupass / OPENTIX 等），保留真實圖片。
        2. 若無真實圖片或為通用無效圖，依據場館、劇團、藝術形式精準對應在地代表性高清照片。
        """
        # 如果已經指派本地專屬 assets 圖片，直接保留
        if act.cover_image and act.cover_image.startswith('assets/images/'):
            return

        # 如果已有真實售票或社群平台的封面圖，予以保留
        if act.cover_image and any(domain in act.cover_image for domain in ['accupass', 'opentix', 'fbcdn', 'cdninstagram']):
            return

        text = f"{act.title} {act.venue} {act.organizer} {act.description} {' '.join(act.tags)}".lower()

        # -------------------------------------------------------------
        # 依場館與景點精準對應
        # -------------------------------------------------------------
        if any(kw in text for kw in ['北美館', '臺北市立美術館', '台北市立美術館', 'tfam']):
            act.cover_image = 'assets/images/tfam_museum.jpg'
        elif any(kw in text for kw in ['鐵道部', '鐵路']):
            act.cover_image = 'assets/images/railway_department.jpg'
        elif any(kw in text for kw in ['國立臺灣博物館', '臺博館', '臺灣博物館', '二二八紀念館']):
            act.cover_image = 'assets/images/ntm_museum.jpg'
        elif any(kw in text for kw in ['鶯歌', '陶博館', '陶瓷', '拉胚', '陶泥']):
            act.cover_image = 'assets/images/yingge_ceramics.jpg'
        elif any(kw in text for kw in ['十三行', '八里', '史前考古']):
            act.cover_image = 'assets/images/shisanhang_museum.jpg'
        elif any(kw in text for kw in ['橫山書法', '書藝', '書法', '硯池']):
            act.cover_image = 'assets/images/hengshan_calligraphy.jpg'
        elif any(kw in text for kw in ['大溪木藝', '大溪老街', '木博館', '木藝', '李騰芳']):
            act.cover_image = 'assets/images/daxi_wood_museum.jpg'
        elif any(kw in text for kw in ['淡水古蹟', '紅毛城', '洋樓', '滬尾']):
            act.cover_image = 'assets/images/tamsui_fort_heritage.jpg'
        elif any(kw in text for kw in ['北投溫泉', '溫泉博物館']):
            act.cover_image = 'assets/images/beitou_hotspring.jpg'
        elif any(kw in text for kw in ['當代藝術館', 'moca']):
            act.cover_image = 'assets/images/moca_contemporary.jpg'
        elif any(kw in text for kw in ['天文館', '星空', '天文']):
            act.cover_image = 'assets/images/taipei_astronomy.jpg'
        elif any(kw in text for kw in ['林安泰古厝', '古厝']):
            act.cover_image = 'assets/images/lin_antai_courtyard.jpg'
        elif any(kw in text for kw in ['林本源', '林家花園']):
            act.cover_image = 'assets/images/lin_family_garden.jpg'
        elif any(kw in text for kw in ['黃金博物館', '金瓜石', '九份', '採金']):
            act.cover_image = 'assets/images/gold_museum_mining.jpg'
        elif any(kw in text for kw in ['坪林茶業', '茶博館', '包種茶', '鐵觀音', '貓空', '茶山']):
            act.cover_image = 'assets/images/taiwan_tea_culture.jpg'
        elif any(kw in text for kw in ['孔廟', '儒家', '六藝']):
            act.cover_image = 'assets/images/confucian_temple.jpg'
        elif any(kw in text for kw in ['空軍三重一村', '馬祖新村', '眷村']):
            act.cover_image = 'assets/images/sanchong_military_village.jpg'
        elif any(kw in text for kw in ['萬里蟹', '漁港', '野柳']):
            act.cover_image = 'assets/images/wanli_fishing_port.jpg'
        elif any(kw in text for kw in ['兒童美術館', '兒美館', '兒藝中心']):
            act.cover_image = 'assets/images/taoyuan_children_art.jpg'
        elif any(kw in text for kw in ['新北市立美術館', '新美館']):
            act.cover_image = 'assets/images/ntcam_new_art_museum.jpg'
        elif any(kw in text for kw in ['大稻埕', '迪化街', '永樂市場', '艋舺', '剝皮寮']):
            act.cover_image = 'assets/images/dadaocheng_walk.jpg'
        # -------------------------------------------------------------
        # 依藝術表演類型與手作主題精準對應
        # -------------------------------------------------------------
        elif any(kw in text for kw in ['歌仔戲', '明華園', '傳統戲曲', '交響', '音樂會', '金曲']):
            act.cover_image = 'assets/images/taiwanese_opera.jpg'
        elif any(kw in text for kw in ['布袋戲', '掌中戲', '操偶', '偶戲']):
            act.cover_image = 'assets/images/glove_puppetry.jpg'
        elif any(kw in text for kw in ['做粿', '紅龜粿', '草仔粿', '米食']):
            act.cover_image = 'assets/images/traditional_rice_cake.jpg'
        elif any(kw in text for kw in ['講古', '答喙鼓', '說書', '相聲']):
            act.cover_image = 'assets/images/temple_storytelling.jpg'
        elif any(kw in text for kw in ['脫口秀', 'standup', '喜劇', '漫才']):
            act.cover_image = 'assets/images/standup_comedy.jpg'
        elif any(kw in text for kw in ['繪本', '圖畫書', '共讀']):
            act.cover_image = 'assets/images/taigi_picture_book.jpg'
        elif any(kw in text for kw in ['舞台劇', '話劇', '劇場', '黑盒子']):
            act.cover_image = 'assets/images/theater_stage_play.jpg'
        elif act.category == CategoryEnum.TOUR:
            act.cover_image = 'assets/images/dadaocheng_walk.jpg'
        elif act.category in (CategoryEnum.PICTURE_BOOK, CategoryEnum.STORY):
            act.cover_image = 'assets/images/taigi_picture_book.jpg'
        elif act.category == CategoryEnum.PERFORMANCE:
            act.cover_image = 'assets/images/taiwanese_opera.jpg'
        elif act.category == CategoryEnum.EXPERIENCE:
            act.cover_image = 'assets/images/traditional_rice_cake.jpg'
        else:
            act.cover_image = 'assets/images/taiwanese_opera.jpg'

    @classmethod
    def clean_and_normalize(cls, activities: List[Activity]) -> List[Activity]:
        """
        嚴格去重與資料正規化：
        1. 同一活動 ID 不重複。
        2. 同一日期時間 + 同一場館/地點 不重複。
        3. 同一日期 + 相同核心標題關鍵字 不重複。
        4. 自動指派貼近實際活動現場之真實封面圖片。
        """
        seen_exact = set()
        seen_time_venue = set()
        seen_time_title = set()
        cleaned: List[Activity] = []

        for act in activities:
            if not act.title or not act.start_time:
                continue

            # 1. 依據唯一識別 ID 去重
            if act.id in seen_exact:
                continue
            seen_exact.add(act.id)

            # 2. 提取標準化時間字串（精確至分鐘及日期）
            dt_minute = act.start_time[:16] if len(act.start_time) >= 16 else act.start_time
            date_day = act.start_time[:10] if len(act.start_time) >= 10 else act.start_time

            # 3. 同一時間 + 同一場館/地點 嚴格去重
            clean_venue = re.sub(r'[\s\-_0-9樓層號A-Za-z]', '', act.venue.split('(')[0].split('（')[0])
            time_venue_key = f"{dt_minute}_{clean_venue}" if clean_venue else None
            if time_venue_key and time_venue_key in seen_time_venue:
                continue

            # 4. 同一日期 + 核心標題關鍵字 嚴格去重
            clean_title = re.sub(r'[\s【】（）()\[\]\-_《》「」・·\d]', '', act.title)
            for fluff in ['台語導覽', '台語走讀', '全台語', '市府活動', '台語表演', '台語故事', '台語繪本', '台語體驗', '台語舞台劇', '親子', '專場', '定時導覽']:
                clean_title = clean_title.replace(fluff, '')
            core_keyword = clean_title[:8]
            time_title_key = f"{date_day}_{core_keyword}" if core_keyword else None
            if time_title_key and time_title_key in seen_time_title:
                continue

            # 註冊已處理鍵值
            if time_venue_key:
                seen_time_venue.add(time_venue_key)
            if time_title_key:
                seen_time_title.add(time_title_key)

            # 重新檢查城市歸屬
            if act.city == CityEnum.OTHER:
                act.city = cls.detect_city(act.title, act.venue, act.address)

            # 指派最貼近實際活動之代表性圖片
            cls.assign_representative_image(act)

            cleaned.append(act)

        # 依開始時間升冪排序
        cleaned.sort(key=lambda x: x.start_time)
        return cleaned
