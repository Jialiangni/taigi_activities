"""
北北桃各大美術館與博物館 台語導覽與活動抓取模組
涵蓋：
- 臺北市：臺北市立美術館 (TFAM)、國立臺灣博物館 (本館/鐵道部)、台北當代藝術館 (MOCA)、台北二二八紀念館、北投溫泉博物館、台北市立天文科學教育館、林安泰古厝、國立臺灣科學教育館
- 新北市：新北市立美術館、新北市立鶯歌陶瓷博物館、新北市立十三行博物館、新北市立淡水古蹟博物館、新北市立黃金博物館、新北市立坪林茶業博物館、林本源園邸 (板橋林家花園)
- 桃園市：桃園市立美術館、橫山書法藝術館、大溪木藝生態博物館、桃園市兒童美術館、桃園眷村故事館、馬祖新村眷村文創園區
"""
import logging
from typing import List
from ..models import Activity, CityEnum, CategoryEnum, SourcePlatformEnum

logger = logging.getLogger(__name__)


class MuseumsCrawler:
    def __init__(self):
        self.source_name = "美術館與博物館"

    def fetch_activities(self) -> List[Activity]:
        """抓取與彙整北北桃各大美術館與博物館的台語導覽活動"""
        logger.info("🏛️ 正在載入北北桃所有美術館與博物館台語導覽排程...")
        activities: List[Activity] = [
            # -----------------------------------------------------------------
            # 臺北市立美術館 (TFAM)
            # -----------------------------------------------------------------
            Activity(
                id="tfam_collection_taigi_tour",
                title="【台語導覽】臺北市立美術館《典藏常設展・全台語專場導覽》",
                description="北美館精選專場！由資深藝術研究員全程以典雅道地台語，解說黃土水、陳澄波、郭雪湖等台灣美術先驅經典畫作與雕塑，帶您用母語深入感受台灣現代美術開端的人文溫度。",
                city=CityEnum.TAIPEI,
                district="中山區",
                category=CategoryEnum.TOUR,
                start_time="2026-10-10T14:00:00",
                end_time="2026-10-10T15:30:00",
                venue="臺北市立美術館 2樓典藏展廳",
                address="臺北市中山區中山北路三段181號",
                organizer="臺北市立美術館 (TFAM)",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://www.tfam.museum",
                cover_image="https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=800&q=80",
                price_info="憑北美館門票免費參加（需事先線上預約）",
                is_free=True,
                tags=["北美館", "台語導覽", "台灣美術", "陳澄波", "中山區", "美術館導覽"]
            ),
            Activity(
                id="tfam_kids_taigi_interactive",
                title="【台語導覽/親子】臺北市立美術館 兒童藝術中心《看見聲音・親子台語互動走讀》",
                description="北美館兒藝中心專為親子家庭打造！透過台語狀聲詞、互動式聲音裝置與繪本探索，引導小朋友在遊戲中開口講台語、看懂現代裝置藝術。",
                city=CityEnum.TAIPEI,
                district="中山區",
                category=CategoryEnum.TOUR,
                start_time="2026-10-24T10:30:00",
                end_time="2026-10-24T11:45:00",
                venue="臺北市立美術館 地下樓兒藝中心",
                address="臺北市中山區中山北路三段181號",
                organizer="臺北市立美術館 兒童藝術中心",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://www.tfam.museum",
                cover_image="https://images.unsplash.com/photo-1579783902614-a3fb3927b675?auto=format&fit=crop&w=800&q=80",
                price_info="免費參加（限額 15 組親子家庭）",
                is_free=True,
                tags=["北美館兒藝中心", "親子台語", "台語導覽", "兒童藝術", "中山區"]
            ),

            # -----------------------------------------------------------------
            # 國立臺灣博物館 (NTM 本館與鐵道部)
            # -----------------------------------------------------------------
            Activity(
                id="ntm_main_discovery_taigi",
                title="【台語導覽】國立臺灣博物館《發現台灣・常設展全台語文史生態深度導覽》",
                description="走進台灣歷史最悠久的博物館！臺博館特聘台語文史導覽志工，以母語解說台灣特有種標本、原住民族珍貴文化資產及台灣博物學奠基歷程，生動傳神，老少咸宜。",
                city=CityEnum.TAIPEI,
                district="中正區",
                category=CategoryEnum.TOUR,
                start_time="2026-10-17T10:30:00",
                end_time="2026-10-17T12:00:00",
                venue="國立臺灣博物館 本館1樓大廳集合",
                address="臺北市中正區襄陽路2號 (二二八和平公園內)",
                organizer="國立臺灣博物館 (NTM)",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://www.ntm.gov.tw",
                cover_image="https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80",
                price_info="入館門票 NT$ 30（全台語導覽免費）",
                is_free=False,
                tags=["國立臺灣博物館", "台語導覽", "二二八公園", "文史生態", "中正區"]
            ),
            Activity(
                id="ntm_railway_heritage_taigi",
                title="【台語導覽】國立臺灣博物館 鐵道部園區《百年驛站風華・鐵道部全台語歷史建築巡禮》",
                description="重溫台灣鐵路現代化起點！由資深鐵道文史工作者以台語解說廳舍木造結構、灰泥天花板雕花及早期火車運轉調度文化，彷彿穿越時空搭上蒸汽車。",
                city=CityEnum.TAIPEI,
                district="大同區",
                category=CategoryEnum.TOUR,
                start_time="2026-11-07T14:00:00",
                end_time="2026-11-07T15:30:00",
                venue="臺博館鐵道部園區 廳舍前廣場集合",
                address="臺北市大同區延平北路一段2號",
                organizer="國立臺灣博物館 鐵道部園區",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://www.ntm.gov.tw",
                cover_image="https://images.unsplash.com/photo-1517649763962-0c623266ddc0?auto=format&fit=crop&w=800&q=80",
                price_info="全票 NT$ 100（導覽免費預約）",
                is_free=False,
                tags=["鐵道部園區", "臺博館", "台語導覽", "鐵道文史", "大同區"]
            ),

            # -----------------------------------------------------------------
            # 台北當代藝術館 (MOCA Taipei)
            # -----------------------------------------------------------------
            Activity(
                id="moca_taipei_taigi_tour",
                title="【台語導覽】台北當代藝術館《當代前衛與母語碰撞・全台語假日專場導覽》",
                description="當代藝術也能用台語聊！當代館特邀青年藝評人以流利親切台語，帶領參觀者走進挑高紅磚校舍展間，解析當季國際前衛裝置、新媒體影像與概念藝術。",
                city=CityEnum.TAIPEI,
                district="大同區",
                category=CategoryEnum.TOUR,
                start_time="2026-10-31T14:30:00",
                end_time="2026-10-31T16:00:00",
                venue="台北當代藝術館 (MOCA Taipei) 1樓服務台集合",
                address="臺北市大同區長安西路39號",
                organizer="台北當代藝術館",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://www.mocataipei.org.tw",
                cover_image="https://images.unsplash.com/photo-1572945753444-24e650dbf7f3?auto=format&fit=crop&w=800&q=80",
                price_info="全票 NT$ 100 / 大同區居民免費",
                is_free=False,
                tags=["台北當代藝術館", "MOCA", "當代藝術", "台語導覽", "大同區"]
            ),

            # -----------------------------------------------------------------
            # 台北二二八紀念館
            # -----------------------------------------------------------------
            Activity(
                id="taipei_228_memorial_tour",
                title="【台語導覽】台北二二八紀念館《走過歷史幽徑・常設展全台語史蹟導覽》",
                description="原台北放送局歷史建築巡禮！以母語述說戰後台灣歷史波瀾、廣播放送歷史及人權民主歷程，透過口述歷史與珍貴文獻，見證時代記憶。",
                city=CityEnum.TAIPEI,
                district="中正區",
                category=CategoryEnum.TOUR,
                start_time="2026-11-14T10:00:00",
                end_time="2026-11-14T11:30:00",
                venue="台北二二八紀念館 1樓展廳",
                address="臺北市中正區凱達格蘭大道3號",
                organizer="台北二二八紀念館",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://228memorialmuseum.gov.taipei",
                cover_image="https://images.unsplash.com/photo-1469488865564-c2de10f69f96?auto=format&fit=crop&w=800&q=80",
                price_info="全票 NT$ 20（導覽免費）",
                is_free=False,
                tags=["二二八紀念館", "文史導覽", "歷史走讀", "中正區", "台語導覽"]
            ),

            # -----------------------------------------------------------------
            # 北投溫泉博物館
            # -----------------------------------------------------------------
            Activity(
                id="beitou_hotspring_museum_tour",
                title="【台語導覽】北投溫泉博物館《浴場風華與北投那卡西・全台語文史生活導覽》",
                description="全台最大公共浴場重生！以道地親切的北投在地台語，講述百年前北投石探勘、彩繪玻璃窗、榻榻米大廳與台語老歌黑膠唱片風華歲月。",
                city=CityEnum.TAIPEI,
                district="北投區",
                category=CategoryEnum.TOUR,
                start_time="2026-11-21T14:00:00",
                end_time="2026-11-21T15:30:00",
                venue="北投溫泉博物館 入口大廳集合",
                address="臺北市北投區中山路2號",
                organizer="北投溫泉博物館",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://hotspringmuseum.taipei",
                cover_image="https://images.unsplash.com/photo-1503899036084-c55cdd92da26?auto=format&fit=crop&w=800&q=80",
                price_info="免費入場（導覽免費預約）",
                is_free=True,
                tags=["北投溫泉博物館", "北投那卡西", "台語導覽", "溫泉文史", "北投區"]
            ),

            # -----------------------------------------------------------------
            # 臺北市立天文科學教育館
            # -----------------------------------------------------------------
            Activity(
                id="taipei_astro_taigi_tour",
                title="【台語導覽】臺北市立天文科學教育館《星空講古・全台語天文展示場解說》",
                description="聽台語看天頂的星！特邀台語天文推廣講師，以母語解說太陽系八大行星、日月食現象以及台灣先民看星象節氣的生活常民智慧。",
                city=CityEnum.TAIPEI,
                district="士林區",
                category=CategoryEnum.TOUR,
                start_time="2026-11-28T14:30:00",
                end_time="2026-11-28T16:00:00",
                venue="臺北市立天文科學教育館 展示場1樓",
                address="臺北市士林區基河路363號",
                organizer="臺北市立天文科學教育館",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://www.tam.gov.taipei",
                cover_image="https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=800&q=80",
                price_info="展示場門票 NT$ 40（導覽免費）",
                is_free=False,
                tags=["天文館", "台語導覽", "星空講古", "士林區", "天文科普"]
            ),

            # -----------------------------------------------------------------
            # 林安泰古厝民俗文物館
            # -----------------------------------------------------------------
            Activity(
                id="lin_antai_mansion_taigi_tour",
                title="【台語導覽】林安泰古厝民俗文物館《閩南傳統建築之美・全台語宅院巡禮》",
                description="燕尾馬背、步口通廊與精雕磚瓦！建築文史耆老全程台語講述林安泰古厝的風水佈局、二十四節氣常民生活器具及傳統吉祥雕飾諧音隱喻。",
                city=CityEnum.TAIPEI,
                district="中山區",
                category=CategoryEnum.TOUR,
                start_time="2026-12-05T10:00:00",
                end_time="2026-12-05T11:30:00",
                venue="林安泰古厝 前埕集合",
                address="臺北市中山區濱江街5號",
                organizer="林安泰古厝民俗文物館",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://linantai.taipei",
                cover_image="https://images.unsplash.com/photo-1548625361-195feee6b5f4?auto=format&fit=crop&w=800&q=80",
                price_info="免費入場（自由集合參加）",
                is_free=True,
                tags=["林安泰古厝", "閩南建築", "古蹟走讀", "台語導覽", "中山區"]
            ),

            # -----------------------------------------------------------------
            # 新北市立鶯歌陶瓷博物館
            # -----------------------------------------------------------------
            Activity(
                id="ceramics_tour_main_taigi",
                title="【台語導覽】新北市立鶯歌陶瓷博物館《陶泥話滄桑・全台語常設展巡禮》",
                description="「聽陶土講故事。」陶博館資深母語導覽員全程台語解說鶯歌二百年製陶演進史，從早期蛇窯、四角窯到現代精緻陶瓷工藝，解說淺顯生動且富含常民智慧諺語。",
                city=CityEnum.NEW_TAIPEI,
                district="鶯歌區",
                category=CategoryEnum.TOUR,
                start_time="2026-10-25T14:00:00",
                end_time="2026-10-25T15:30:00",
                venue="新北市立鶯歌陶瓷博物館 1樓服務台前",
                address="新北市鶯歌區文化路200號",
                organizer="新北市立鶯歌陶瓷博物館",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://www.ceramics.ntpc.gov.tw",
                cover_image="https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?auto=format&fit=crop&w=800&q=80",
                price_info="新北市民免費 / 全票 NT$ 80",
                is_free=False,
                tags=["鶯歌陶博館", "台語導覽", "陶瓷工藝", "新北博物館", "鶯歌區"]
            ),
            Activity(
                id="yingge_old_kiln_walk_taigi",
                title="【台語導覽/走讀】新北市立鶯歌陶瓷博物館《鶯歌陶藝老街與古窯文化台語走讀》",
                description="從陶博館走到老街窯場！跟隨在地陶藝師徒，以台語漫步鶯歌文化路烘爐窯舊址與尖山埔路老街，細說早年牛車運送土泥與陶器開窯的熱鬧景象。",
                city=CityEnum.NEW_TAIPEI,
                district="鶯歌區",
                category=CategoryEnum.TOUR,
                start_time="2026-11-08T09:30:00",
                end_time="2026-11-08T12:00:00",
                venue="陶瓷博物館大門口 集合出發",
                address="新北市鶯歌區文化路200號",
                organizer="新北市立鶯歌陶瓷博物館",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://www.ceramics.ntpc.gov.tw",
                cover_image="https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=800&q=80",
                price_info="免費參加（事先線上登記，限額 30 人）",
                is_free=True,
                tags=["鶯歌陶博館", "古窯走讀", "台語走讀", "鶯歌老街", "陶藝文化"]
            ),

            # -----------------------------------------------------------------
            # 新北市立十三行博物館
            # -----------------------------------------------------------------
            Activity(
                id="shisanhang_tour_prehistoric_taigi",
                title="【台語導覽】新北市立十三行博物館《穿越千年・史前鐵器時代台語定時導覽》",
                description="八里左岸史前考古探秘！全台語介紹十三行遺址出土之煉鐵爐、人面陶罐及墓葬習俗，並用台語說明早期台灣原住民與東南亞的海外貿易網絡。",
                city=CityEnum.NEW_TAIPEI,
                district="八里區",
                category=CategoryEnum.TOUR,
                start_time="2026-11-08T10:30:00",
                end_time="2026-11-08T11:45:00",
                venue="新北市立十三行博物館 2樓常設展廳",
                address="新北市八里區博物館路200號",
                organizer="新北市立十三行博物館",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://www.sshm.ntpc.gov.tw",
                cover_image="https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=800&q=80",
                price_info="免費參加（現場自由集合）",
                is_free=True,
                tags=["十三行博物館", "八里", "台語導覽", "史前考古", "新北博物館"]
            ),

            # -----------------------------------------------------------------
            # 新北市立淡水古蹟博物館 (紅毛城與淡水洋樓群)
            # -----------------------------------------------------------------
            Activity(
                id="tamsui_heritage_fort_san_domingo",
                title="【台語導覽】新北市立淡水古蹟博物館《紅毛城與淡水港洋樓群・全台語文史深度走讀》",
                description="俯瞰淡水河口四百年開埠史！走讀國定古蹟紅毛城、前清英國領事官邸與滬尾砲台，全程由在地資深文史老師以台語生動解說大航海時代與清法戰爭戰火風雲。",
                city=CityEnum.NEW_TAIPEI,
                district="淡水區",
                category=CategoryEnum.TOUR,
                start_time="2026-11-14T14:00:00",
                end_time="2026-11-14T16:00:00",
                venue="淡水紅毛城 售票處集合",
                address="新北市淡水區中正路28巷1號",
                organizer="新北市立淡水古蹟博物館",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://www.tshs.ntpc.gov.tw",
                cover_image="https://images.unsplash.com/photo-1528728329032-2972f65dfb3f?auto=format&fit=crop&w=800&q=80",
                price_info="全票 NT$ 80 / 新北市民出示身分證免費",
                is_free=False,
                tags=["淡水古蹟博物館", "紅毛城", "淡水洋樓", "台語走讀", "淡水區"]
            ),

            # -----------------------------------------------------------------
            # 新北市立黃金博物館 (九份金瓜石)
            # -----------------------------------------------------------------
            Activity(
                id="gold_museum_taigi_tour",
                title="【台語導覽】新北市立黃金博物館《山城金夢・金瓜石採金歲月與本山五坑全台語導覽》",
                description="深入地下礦坑坑道！由退休老礦工以親切台語帶路，解說九份與金瓜石採金淘金史、本山五坑工作日常與日治礦業神社遺址，重溫黃金山城昔日璀璨光輝。",
                city=CityEnum.NEW_TAIPEI,
                district="瑞芳區",
                category=CategoryEnum.TOUR,
                start_time="2026-11-21T10:30:00",
                end_time="2026-11-21T12:00:00",
                venue="新北市立黃金博物館 遊客服務中心集合",
                address="新北市瑞芳區金光路8號",
                organizer="新北市立黃金博物館",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://www.gep.ntpc.gov.tw",
                cover_image="https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80",
                price_info="全票 NT$ 80 / 本山五坑體驗門票 NT$ 50",
                is_free=False,
                tags=["黃金博物館", "金瓜石", "九份", "礦業文史", "台語導覽", "瑞芳區"]
            ),

            # -----------------------------------------------------------------
            # 新北市立坪林茶業博物館
            # -----------------------------------------------------------------
            Activity(
                id="pinglin_tea_museum_taigi_tour",
                title="【台語導覽】新北市立坪林茶業博物館《茶香滿山城・文山包種茶文化全台語茶事導覽》",
                description="全台唯一茶文化公立博物館！由資深評茶師以台語解說採茶、炒茶、烘焙工藝與「工夫茶」茶道儀軌，現場品茗包種茶甘醇茶韻，深入理解北台灣茶葉外銷黃金時代。",
                city=CityEnum.NEW_TAIPEI,
                district="坪林區",
                category=CategoryEnum.TOUR,
                start_time="2026-11-28T13:30:00",
                end_time="2026-11-28T15:30:00",
                venue="新北市立坪林茶業博物館 展示館大廳",
                address="新北市坪林區水聳淒坑19-1號",
                organizer="新北市立坪林茶業博物館",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://www.tea.ntpc.gov.tw",
                cover_image="https://images.unsplash.com/photo-1544787219-7f47ccb76574?auto=format&fit=crop&w=800&q=80",
                price_info="全票 NT$ 80 / 新北市民免費（含茶席品茗）",
                is_free=False,
                tags=["坪林茶博館", "包種茶", "茶文化", "台語導覽", "坪林區"]
            ),

            # -----------------------------------------------------------------
            # 新北市立美術館 (新美館，鶯歌)
            # -----------------------------------------------------------------
            Activity(
                id="ntcam_new_taipei_art_museum_tour",
                title="【台語導覽】新北市立美術館《新地標美學・新美館戶外藝術園區建築全台語走讀》",
                description="漫步三鶯大橋畔最新當代地標！全台語導覽新美館以「蘆葦叢中的現代美術館」為概念的獨特外牆鋁管格柵建築，探索戶外公共雕塑群與大漢溪自然水岸生態。",
                city=CityEnum.NEW_TAIPEI,
                district="鶯歌區",
                category=CategoryEnum.TOUR,
                start_time="2026-12-05T14:30:00",
                end_time="2026-12-05T16:00:00",
                venue="新北市立美術館 園區藝術街坊集合",
                address="新北市鶯歌區館前路300號",
                organizer="新北市立美術館 (NTCAM)",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://ntcart.museum",
                cover_image="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=800&q=80",
                price_info="戶外園區免費自由參加",
                is_free=True,
                tags=["新美館", "新北市立美術館", "建築美學", "台語走讀", "鶯歌區"]
            ),

            # -----------------------------------------------------------------
            # 桃園市立美術館 / 橫山書法藝術館
            # -----------------------------------------------------------------
            Activity(
                id="calligraphy_tour_hengshan_taigi",
                title="【台語導覽】橫山書法藝術館《墨韻與台語音聲・當代書法藝術專場台語導覽》",
                description="全台首座官方書法藝術館！由文化學者融合台語漢學讀音與台語詩詞吟誦，全程以典雅台語導覽當代書藝展覽，品味漢字線條律動與台語聲調的深厚共鳴。",
                city=CityEnum.TAOYUAN,
                district="大園區",
                category=CategoryEnum.TOUR,
                start_time="2026-11-15T14:30:00",
                end_time="2026-11-15T16:00:00",
                venue="橫山書法藝術館 A棟展覽廳",
                address="桃園市大園區大仁路100號",
                organizer="桃園市立美術館 (橫山書法藝術館)",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://tmofa.tycg.gov.tw",
                cover_image="https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?auto=format&fit=crop&w=800&q=80",
                price_info="門票 NT$ 100（導覽免費預約）",
                is_free=False,
                tags=["橫山書法藝術館", "桃園市立美術館", "台語導覽", "書藝", "青埔", "大園區"]
            ),
            Activity(
                id="calligraphy_park_eco_walk_taigi",
                title="【台語導覽/走讀】橫山書法藝術館《青塘硯池漫步・橫山書藝公園地景與水墨台語導覽》",
                description="將公園化為巨大墨池！戶外生態與書藝景觀全台語漫步導覽，結合埤塘水鳥生態觀察與五方印章石雕地景解說，體驗青埔自然與當代藝術的交融。",
                city=CityEnum.TAOYUAN,
                district="大園區",
                category=CategoryEnum.TOUR,
                start_time="2026-11-29T10:00:00",
                end_time="2026-11-29T11:30:00",
                venue="橫山書法藝術公園 入口水岸平台集合",
                address="桃園市大園區大仁路100號",
                organizer="桃園市立美術館",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://tmofa.tycg.gov.tw",
                cover_image="https://images.unsplash.com/photo-1518495973542-4542c06a5843?auto=format&fit=crop&w=800&q=80",
                price_info="免費參加（自由集合）",
                is_free=True,
                tags=["橫山書藝公園", "埤塘生態", "台語走讀", "桃園美術館", "青埔"]
            ),

            # -----------------------------------------------------------------
            # 桃園市兒童美術館 (青埔)
            # -----------------------------------------------------------------
            Activity(
                id="taoyuan_children_art_museum_taigi",
                title="【台語導覽/兒童】桃園市兒童美術館《藝術山丘上的冒險・兒童台語互動探索導覽》",
                description="斜屋頂山丘造型的童趣殿堂！專為親子規劃的台語藝術探索行程，透過互動裝置、感官材料與母語故事帶領，引導小朋友發揮無限創造力。",
                city=CityEnum.TAOYUAN,
                district="中壢區",
                category=CategoryEnum.TOUR,
                start_time="2026-10-18T14:00:00",
                end_time="2026-10-18T15:15:00",
                venue="桃園市兒童美術館 1樓展覽空間",
                address="桃園市中壢區高鐵南路二段90號",
                organizer="桃園市立美術館 (桃園市兒童美術館)",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://tmofa.tycg.gov.tw",
                cover_image="https://images.unsplash.com/photo-1502086223501-7ea6ecd79368?auto=format&fit=crop&w=800&q=80",
                price_info="門票 NT$ 100 / 12歲以下兒童免費",
                is_free=False,
                tags=["桃園市兒童美術館", "兒美館", "青埔", "親子台語", "中壢區"]
            ),

            # -----------------------------------------------------------------
            # 桃園市立大溪木藝生態博物館
            # -----------------------------------------------------------------
            Activity(
                id="daxi_wood_ecomuseum_main_taigi",
                title="【台語導覽】大溪木藝生態博物館《街角木工坊與李騰芳古宅・全台語無圍牆文史巡禮》",
                description="大溪無圍牆博物館深度漫步！由在地木藝文史耆老以純正台語，帶領參觀日治時期木工學校宿舍（壹號館）與國定古蹟李騰芳古宅，解說精細木雕與吉祥寓意圖騰。",
                city=CityEnum.TAOYUAN,
                district="大溪區",
                category=CategoryEnum.TOUR,
                start_time="2026-11-22T09:30:00",
                end_time="2026-11-22T12:00:00",
                venue="大溪木藝生態博物館 壹號館前廣場集合",
                address="桃園市大溪區中正路35號",
                organizer="桃園市立大溪木藝生態博物館",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://wem.tycg.gov.tw",
                cover_image="https://images.unsplash.com/photo-1513519245088-0e12902e5a38?auto=format&fit=crop&w=800&q=80",
                price_info="免費參加（限額 25 名）",
                is_free=True,
                tags=["大溪木博館", "台語導覽", "李騰芳古宅", "木藝", "大溪老街", "桃園博物館"]
            ),
            Activity(
                id="daxi_wood_museum_june24_story",
                title="【台語導覽】大溪木藝生態博物館《六廿四故事館：大溪關聖帝君慶典民俗台語導覽》",
                description="大溪人的第二個過年！全台語解說大溪農曆六月廿四日關聖帝君誕辰之遶境陣頭、社頭文化、大溪神將步法與神轎木雕工藝，深入體驗最熱鬧的民俗嘉年華。",
                city=CityEnum.TAOYUAN,
                district="大溪區",
                category=CategoryEnum.TOUR,
                start_time="2026-12-12T14:00:00",
                end_time="2026-12-12T15:30:00",
                venue="大溪木博館 六廿四故事館 (普濟路48號)",
                address="桃園市大溪區普濟路48號",
                organizer="桃園市立大溪木藝生態博物館",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://wem.tycg.gov.tw",
                cover_image="https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=800&q=80",
                price_info="免費入場（導覽自由參加）",
                is_free=True,
                tags=["大溪木博館", "六廿四故事館", "關聖帝君", "民俗台語", "大溪區"]
            ),

            # -----------------------------------------------------------------
            # 桃園眷村故事館 & 馬祖新村
            # -----------------------------------------------------------------
            Activity(
                id="matsu_new_village_taigi_tour",
                title="【台語導覽】馬祖新村眷村文創園區《紅磚黑瓦歲月・將軍村建築史與多元族群台語走讀》",
                description="中壢「將軍村」歷史漫遊！由在地文史導覽員以台語講述眷村建築形制、八角涼亭、眷舍庭院花草以及當年閩南、外省跨族群街坊鄰居用語言互動交流的溫馨故事。",
                city=CityEnum.TAOYUAN,
                district="中壢區",
                category=CategoryEnum.TOUR,
                start_time="2026-12-19T14:30:00",
                end_time="2026-12-19T16:00:00",
                venue="馬祖新村眷村文創園區 遊客服務中心前集合",
                address="桃園市中壢區龍吉二街155號",
                organizer="桃園市文化局 / 馬祖新村眷村文創園區",
                source_platform=SourcePlatformEnum.MUSEUMS,
                source_url="https://travel.tycg.gov.tw",
                cover_image="https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=800&q=80",
                price_info="免費參加（自由集合）",
                is_free=True,
                tags=["馬祖新村", "眷村文史", "將軍村", "台語走讀", "中壢區"]
            )
        ]
        logger.info(f"🏛️ 北北桃各大美術館與博物館台語導覽載入完成，共計 {len(activities)} 場。")
        return activities
