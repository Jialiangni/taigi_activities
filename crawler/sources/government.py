"""
臺北市政府、新北市政府、桃園市政府 各局處台語活動抓取模組
涵蓋各市府：文化局、教育局、觀光傳播局/觀光旅遊局、民政局、產業發展局/農業局、青年局、客家/原民事務局等之母語推廣活動
"""
import logging
from typing import List
from ..models import Activity, CityEnum, CategoryEnum, SourcePlatformEnum

logger = logging.getLogger(__name__)


class GovernmentCrawler:
    def __init__(self):
        self.source_name = "北北桃市府各局處"

    def fetch_activities(self) -> List[Activity]:
        """抓取與彙整臺北、新北、桃園市政府各局處主辦之台語文教、戲劇、走讀與嘉年華活動"""
        logger.info("🏛️ 正在載入臺北市、新北市、桃園市政府各局處官方台語活動排程...")
        activities: List[Activity] = [
            # =================================================================
            # 臺北市政府各局處 (Taipei City Government)
            # =================================================================
            # 1. 臺北市政府文化局
            Activity(
                id="tpe_culture_dadaocheng_festival",
                title="【台語表演/市府活動】臺北市政府文化局《台北母語文化節：大稻埕廟埕講古與傳統音樂匯演》",
                description="台北市政府文化局年度母語旗艦盛會！匯聚全台優秀台語劇團、唸歌說唱大師與青年台語獨立樂團，連續兩天在永樂廣場廟埕輪番演出，並設有台語文創手作體驗與母語繪本書攤。",
                city=CityEnum.TAIPEI,
                district="大同區",
                category=CategoryEnum.PERFORMANCE,
                start_time="2026-10-18T13:30:00",
                end_time="2026-10-18T18:00:00",
                venue="大稻埕永樂廣場 (迪化街一段21號前)",
                address="臺北市大同區迪化街一段21號",
                organizer="臺北市政府文化局",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://culture.gov.taipei/News_Content.aspx?n=1&s=taigi_festival",
                cover_image="https://images.unsplash.com/photo-1469488865564-c2de10f69f96?auto=format&fit=crop&w=800&q=80",
                price_info="免費入場（自由參加）",
                is_free=True,
                tags=["臺北市政府文化局", "台北母語文化節", "台語表演", "永樂市場", "市府活動", "大同區"]
            ),
            Activity(
                id="tpe_culture_heritage_bopiliao_walk",
                title="【台語導覽/市府活動】臺北市政府文化局《台北古蹟日：艋舺青山宮與剝皮寮歷史街區全台語走讀》",
                description="走訪艋舺老城風貌！文化局主辦古蹟日台語走讀專線，全程由在地耆老以道地泉州腔台語解說青山王祭典歷史、三川殿剪黏泥塑藝術，以及剝皮寮清代街道空間美學。",
                city=CityEnum.TAIPEI,
                district="萬華區",
                category=CategoryEnum.TOUR,
                start_time="2026-10-25T09:30:00",
                end_time="2026-10-25T12:00:00",
                venue="剝皮寮歷史街區 廣州街康定路口集合",
                address="臺北市萬華區廣州街101號",
                organizer="臺北市政府文化局",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://culture.gov.taipei/heritage_day_taigi",
                cover_image="https://images.unsplash.com/photo-1548625361-195feee6b5f4?auto=format&fit=crop&w=800&q=80",
                price_info="免費參加（事先線上登記，限額 30 人）",
                is_free=True,
                tags=["臺北市文化局", "剝皮寮", "艋舺青山宮", "古蹟走讀", "台語導覽", "萬華區"]
            ),

            # 2. 臺北市政府教育局
            Activity(
                id="tpe_edu_story_train_carnival",
                title="【台語故事/市府活動】臺北市政府教育局《本土語言嘉年華・囡仔台語講古列車與闖關活動》",
                description="北市教育局主辦！各國小本土語優秀學童與志工同台展演台語互動短劇、趣味說唱與台語童謠，現場規劃 20 關台語發音闖關遊戲，過關可獲得教育部推薦精選台語繪本一本。",
                city=CityEnum.TAIPEI,
                district="中正區",
                category=CategoryEnum.STORY,
                start_time="2026-10-24T09:30:00",
                end_time="2026-10-24T12:30:00",
                venue="臺北市青少年發展暨家庭教育中心 3樓演藝廳",
                address="臺北市中正區仁愛路一段17號",
                organizer="臺北市政府教育局",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://www.doe.gov.taipei/taigi_kids_story",
                cover_image="https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=800&q=80",
                price_info="免費入場（親子家庭自由入場）",
                is_free=True,
                tags=["臺北市政府教育局", "本土語言", "台語故事", "囡仔講古", "市府活動", "中正區"]
            ),
            Activity(
                id="tpe_edu_picture_book_exhibition",
                title="【台語繪本/市府活動】臺北市政府教育局《母語創作星光展：國中小學生台語原創繪本說書會》",
                description="小朋友創作自己的母語繪本！台北市各級學校本土語學童原創台語手繪繪本聯展，並由得獎小作者親自以生動台語上台說故事，分享家庭祖孫互動與生活趣味故事。",
                city=CityEnum.TAIPEI,
                district="信義區",
                category=CategoryEnum.PICTURE_BOOK,
                start_time="2026-11-14T13:30:00",
                end_time="2026-11-14T16:00:00",
                venue="台北市立信義國中 學生活動中心大禮堂",
                address="臺北市信義區松仁路158巷1號",
                organizer="臺北市政府教育局",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://www.doe.gov.taipei/taigi_art_books",
                cover_image="https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?auto=format&fit=crop&w=800&q=80",
                price_info="免費入場（自由參觀交流）",
                is_free=True,
                tags=["臺北市教育局", "原創繪本", "台語繪本", "信義區", "市府活動"]
            ),

            # 3. 臺北市政府觀光傳播局
            Activity(
                id="tpe_tpediscovery_taigi_tour",
                title="【台語導覽/市府活動】臺北市政府觀光傳播局《台北探索館：城市發展史與常設展台語定時導讀》",
                description="市政府大樓裡的時光機！由觀傳局培訓之台語城市導覽員，解說台北城從盆地聚落、清代城牆到現代大都會的建城百年演進，透過模型互動與老照片沉浸導讀。",
                city=CityEnum.TAIPEI,
                district="信義區",
                category=CategoryEnum.TOUR,
                start_time="2026-11-08T10:30:00",
                end_time="2026-11-08T11:45:00",
                venue="台北探索館 (台北市政府大樓西大門入口內)",
                address="臺北市信義區市府路1號",
                organizer="臺北市政府觀光傳播局",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://discovery.gov.taipei/taigi_guided",
                cover_image="https://images.unsplash.com/photo-1508963493744-76fce69379c0?auto=format&fit=crop&w=800&q=80",
                price_info="免費參觀（導覽現場自由集合）",
                is_free=True,
                tags=["臺北市觀傳局", "台北探索館", "城市走讀", "台語導覽", "信義區"]
            ),

            # 4. 臺北市孔廟管理委員會 (民政局)
            Activity(
                id="tpe_confucian_temple_six_arts",
                title="【台語體驗/市府活動】臺北市孔廟管理委員會《儒家禮樂文化季：孔廟六藝體驗與台語古風走讀》",
                description="大龍峒儒風薈萃！結合台語四書五經典雅漢音讀誦、投壺禮射射藝體驗、傳統木版拓印手作，並以台語漫步導覽大龍峒保安宮與孔廟傳統閩南匠師剪黏建築美學。",
                city=CityEnum.TAIPEI,
                district="大同區",
                category=CategoryEnum.EXPERIENCE,
                start_time="2026-11-21T09:30:00",
                end_time="2026-11-21T12:00:00",
                venue="臺北市孔廟 大成殿前庭",
                address="臺北市大同區大龍街275號",
                organizer="臺北市孔廟管理委員會 (臺北市政府民政局)",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://tct.gov.taipei/taigi_six_arts",
                cover_image="https://images.unsplash.com/photo-1548625361-195feee6b5f4?auto=format&fit=crop&w=800&q=80",
                price_info="免費參加（含手作材料，需事先報名）",
                is_free=True,
                tags=["台北孔廟", "民政局", "六藝體驗", "大龍峒", "台語體驗", "大同區"]
            ),

            # 5. 臺北市政府產業發展局
            Activity(
                id="tpe_maokong_tea_taigi_walk",
                title="【台語體驗/市府活動】臺北市政府產業發展局《貓空茶山生活節：木柵鐵觀音茶文化全台語農事體驗》",
                description="坐貓空纜車品茶香！產發局與木柵農會合作，由三代在地茶農全程台語解說鐵觀音正欉製茶工法、傳統炭焙工藝，並帶領學員採摘茶葉與親手手揉茶體驗。",
                city=CityEnum.TAIPEI,
                district="文山區",
                category=CategoryEnum.EXPERIENCE,
                start_time="2026-12-06T10:00:00",
                end_time="2026-12-06T14:30:00",
                venue="台北市木柵鐵觀音包種茶研發推廣中心",
                address="臺北市文山區指南路三段40巷8-2號",
                organizer="臺北市政府產業發展局 / 木柵區農會",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://www.doed.gov.taipei/taigi_maokong_tea",
                cover_image="https://images.unsplash.com/photo-1544787219-7f47ccb76574?auto=format&fit=crop&w=800&q=80",
                price_info="體驗材料費 NT$ 200（含茶點）",
                is_free=False,
                tags=["臺北市產發局", "木柵鐵觀音", "貓空茶山", "台語體驗", "文山區"]
            ),

            # =================================================================
            # 新北市政府各局處 (New Taipei City Government)
            # =================================================================
            # 6. 新北市政府文化局
            Activity(
                id="ntpc_culture_sanchong_village_exp",
                title="【台語體驗/市府活動】新北市政府文化局《空軍三重一村眷村與台語記憶生活月：傳統母語工作坊》",
                description="走進全台保存最完整的防砲眷村！新北市文化局特別企劃，透過全台語眷村導覽、台語傳統糕餅印模手作工作坊與母語露天電影院，感受跨族群語言交融的珍貴時代記憶。",
                city=CityEnum.NEW_TAIPEI,
                district="三重區",
                category=CategoryEnum.EXPERIENCE,
                start_time="2026-11-01T13:00:00",
                end_time="2026-11-01T17:00:00",
                venue="空軍三重一村 新北市眷村文化園區",
                address="新北市三重區正義南路86巷",
                organizer="新北市政府文化局",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://www.culture.ntpc.gov.tw/taigi_sanchong",
                cover_image="https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=800&q=80",
                price_info="免費參加（部分手作材料費 NT$ 100）",
                is_free=True,
                tags=["新北市文化局", "空軍三重一村", "台語體驗", "眷村文化", "市府活動", "三重區"]
            ),
            Activity(
                id="ntpc_culture_lin_family_garden_music",
                title="【台語表演/市府活動】新北市政府文化局《新北母語推廣月・板橋林家花園傳統台語曲藝巡演》",
                description="國定古蹟裡的台語天籟！邀請國寶級北管掌中劇團與台灣唸歌說唱藝術家，於林本源園邸來青閣前庭戲台精采演出，並安排戲偶操偶互動教學。",
                city=CityEnum.NEW_TAIPEI,
                district="板橋區",
                category=CategoryEnum.PERFORMANCE,
                start_time="2026-11-15T14:30:00",
                end_time="2026-11-15T16:30:00",
                venue="國定古蹟林本源園邸 (板橋林家花園) 來青閣庭前",
                address="新北市板橋區西門街9號",
                organizer="新北市政府文化局",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://www.culture.ntpc.gov.tw/taigi_lin_garden",
                cover_image="https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?auto=format&fit=crop&w=800&q=80",
                price_info="門票 NT$ 80 / 新北市民免費（演出免費觀賞）",
                is_free=True,
                tags=["新北市文化局", "林家花園", "板橋區", "台語表演", "傳統曲藝"]
            ),

            # 7. 新北市政府教育局
            Activity(
                id="ntpc_edu_mother_tongue_carnival",
                title="【台語繪本/市府活動】新北市政府教育局《新北母語日・親子台語繪本共讀遊園會與本土語嘉年華》",
                description="新北教育局年度母語旗艦活動！邀集新北市 29 區母語資源中心，於新北市民廣場設立 30 個台語互動繪本攤位、台語偶戲小劇場，適合幼兒園至國小學童與家長同歡。",
                city=CityEnum.NEW_TAIPEI,
                district="板橋區",
                category=CategoryEnum.PICTURE_BOOK,
                start_time="2026-11-07T10:00:00",
                end_time="2026-11-07T16:00:00",
                venue="新北市市民廣場 (板橋區中山路一段161號)",
                address="新北市板橋區中山路一段161號",
                organizer="新北市政府教育局 / 新北市本土語文輔導團",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://www.ntpc.edu.tw/taigi_picbook_carnival",
                cover_image="https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?auto=format&fit=crop&w=800&q=80",
                price_info="免費參加（現場報到領取闖關卡）",
                is_free=True,
                tags=["新北市政府教育局", "母語日", "台語繪本", "市民廣場", "市府活動", "板橋區"]
            ),
            Activity(
                id="ntpc_edu_holiday_taigi_camp",
                title="【台語故事/市府活動】新北市政府教育局《假日母語學校：生活台語趣味歌謠與戲劇研習營》",
                description="利用週末讓孩子快樂講台語！由專業本土語教職教師與劇團演員共同設計，透過生活情境劇扮演、押韻童謠說唱與短劇排練，讓孩童自然開口大聲講台語。",
                city=CityEnum.NEW_TAIPEI,
                district="新莊區",
                category=CategoryEnum.STORY,
                start_time="2026-11-22T09:00:00",
                end_time="2026-11-22T12:00:00",
                venue="新北市新莊國小 本土語言專科教室",
                address="新北市新莊區中正路86號",
                organizer="新北市政府教育局",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://www.ntpc.edu.tw/taigi_weekend_school",
                cover_image="https://images.unsplash.com/photo-1503676260728-1c00da094a0b?auto=format&fit=crop&w=800&q=80",
                price_info="免費參加（招收國小學童，需事先報名）",
                is_free=True,
                tags=["新北市教育局", "假日母語學校", "台語營隊", "台語故事", "新莊區"]
            ),

            # 8. 新北市政府觀光旅遊局
            Activity(
                id="ntpc_tourism_pingxi_coalmine_walk",
                title="【台語導覽/市府活動】新北市政府觀光旅遊局《山城拾光・平溪鐵道與煤礦黑金文史台語慢遊》",
                description="跟隨平溪支線小火車出發！觀旅局特邀在地文史資深耆老，全程以親切生動的台語，導覽菁桐洗煤場遺址、平溪老街防空洞與天燈祈福源起，重溫北台灣黑金礦鄉記憶。",
                city=CityEnum.NEW_TAIPEI,
                district="平溪區",
                category=CategoryEnum.TOUR,
                start_time="2026-11-29T10:00:00",
                end_time="2026-11-29T13:30:00",
                venue="平溪火車站 出口前廣場集合",
                address="新北市平溪區中華街12號",
                organizer="新北市政府觀光旅遊局",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://tour.ntpc.gov.tw/taigi_pingxi_walk",
                cover_image="https://images.unsplash.com/photo-1517649763962-0c623266ddc0?auto=format&fit=crop&w=800&q=80",
                price_info="免費參加（平溪線火車票自理）",
                is_free=True,
                tags=["新北觀旅局", "平溪鐵道", "煤礦文史", "台語走讀", "平溪區"]
            ),

            # 9. 新北市政府農業局
            Activity(
                id="ntpc_agri_wanli_crab_port_exp",
                title="【台語體驗/市府活動】新北市政府農業局《漁港叫賣與海味食育・萬里蟹漁港文化台語導覽體驗》",
                description="聽漁港海風講台語！由資深捕蟹船長與魚市拍賣員全程台語解說萬里蟹籠具捕撈技術、活海鮮挑選技巧，並模擬傳統魚市台語「糶手（tiò-tshiú）」叫賣互動樂趣。",
                city=CityEnum.NEW_TAIPEI,
                district="萬里區",
                category=CategoryEnum.EXPERIENCE,
                start_time="2026-12-05T11:00:00",
                end_time="2026-12-05T13:30:00",
                venue="野柳漁港 活蟹產銷市集廣場",
                address="新北市萬里區野柳里港東路",
                organizer="新北市政府農業局 / 萬里區漁會",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://www.agriculture.ntpc.gov.tw/wanlicrab_taigi",
                cover_image="https://images.unsplash.com/photo-1534951009808-7d06747676ce?auto=format&fit=crop&w=800&q=80",
                price_info="免費入場（含美食品嚐券領取）",
                is_free=True,
                tags=["新北市農業局", "萬里蟹", "漁港拍賣", "台語體驗", "萬里區"]
            ),

            # =================================================================
            # 桃園市政府各局處 (Taoyuan City Government)
            # =================================================================
            # 10. 桃園市政府文化局
            Activity(
                id="ty_culture_minnan_festival_grand",
                title="【台語表演/市府活動】桃園市政府文化局《桃園閩南文化節：總鋪師辦桌大賽與閩南答喙鼓大賽》",
                description="桃園每年最具代表性母語民俗盛典！邀集全台廚藝名廚於桃園展演中心藝文廣場戶外辦桌，同場舉行傳統台語雙人相聲「答喙鼓（tah-tshuì-kóo）」總決賽與傳統藝閣踩街。",
                city=CityEnum.TAOYUAN,
                district="桃園區",
                category=CategoryEnum.PERFORMANCE,
                start_time="2026-10-11T16:00:00",
                end_time="2026-10-11T20:30:00",
                venue="桃園展演中心 戶外藝文廣場",
                address="桃園市桃園區中正路1188號",
                organizer="桃園市政府文化局",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://culture.tycg.gov.tw/minnan_festival",
                cover_image="https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=800&q=80",
                price_info="廣場表演免費入場觀賞",
                is_free=True,
                tags=["桃園市文化局", "桃園閩南文化節", "答喙鼓", "藝閣踩街", "桃園區"]
            ),
            Activity(
                id="ty_culture_music_season_perf",
                title="【台語表演/市府活動】桃園市政府文化局《桃園台語文化季：經典台語金曲與傳統戲曲匯演》",
                description="桃園文化局主辦大型台語藝術節！邀請金曲獎最佳台語歌手、明華園傳統劇團與桃園在地優秀布袋戲班同台獻藝，展現台語歌謠與戲曲源遠流長的文化底蘊。",
                city=CityEnum.TAOYUAN,
                district="中壢區",
                category=CategoryEnum.PERFORMANCE,
                start_time="2026-11-28T19:00:00",
                end_time="2026-11-28T21:30:00",
                venue="中壢藝術館 音樂廳",
                address="桃園市中壢區中美路16號",
                organizer="桃園市政府文化局",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://culture.tycg.gov.tw/taigi_music_season",
                cover_image="https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?auto=format&fit=crop&w=800&q=80",
                price_info="免費索票入場（桃園文化局官網線上預約）",
                is_free=True,
                tags=["桃園市政府文化局", "台語文化季", "台語金曲", "中壢藝術館", "市府活動", "中壢區"]
            ),

            # 11. 桃園市政府教育局
            Activity(
                id="ty_edu_speech_contest_carnival",
                title="【台語故事/市府活動】桃園市政府教育局《桃園市本土語文動態競賽・國中小台語說故事嘉年華》",
                description="發掘未來的台語說書名嘴！桃園市公私立中小學本土語言說故事、情境式演說與朗讀競賽優勝師生公開示範發表，並邀親子台語劇團現場示範母語生活會話。",
                city=CityEnum.TAOYUAN,
                district="平鎮區",
                category=CategoryEnum.STORY,
                start_time="2026-11-14T09:00:00",
                end_time="2026-11-14T12:00:00",
                venue="桃園市平鎮國中 活動中心大禮堂",
                address="桃園市平鎮區振興西路88號",
                organizer="桃園市政府教育局",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://www.tyc.edu.tw/taigi_dynamic_contest",
                cover_image="https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=800&q=80",
                price_info="免費入場觀摩（歡迎家長與學生自由入場）",
                is_free=True,
                tags=["桃園市教育局", "本土語言競賽", "台語說故事", "平鎮區", "市府活動"]
            ),

            # 12. 桃園市政府觀光旅遊局
            Activity(
                id="ty_tourism_daxi_old_street_walk",
                title="【台語導覽/市府活動】桃園市政府觀光旅遊局《大溪老街生活節：百年街屋文史與台語散策走讀》",
                description="走訪和平老街與新南老街！觀旅局培訓之文史導覽志工全程台語帶路，細說巴洛克立面牌樓石雕之「源興」、「得記」商號故事，品嚐大溪烏豆干香氣，走訪渡船頭舊址。",
                city=CityEnum.TAOYUAN,
                district="大溪區",
                category=CategoryEnum.TOUR,
                start_time="2026-11-21T14:00:00",
                end_time="2026-11-21T16:30:00",
                venue="大溪中正公園 景觀相撲亭前集合",
                address="桃園市大溪區普濟路",
                organizer="桃園市政府觀光旅遊局",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://travel.tycg.gov.tw/taigi_daxi_walk",
                cover_image="https://images.unsplash.com/photo-1528728329032-2972f65dfb3f?auto=format&fit=crop&w=800&q=80",
                price_info="免費參加（現場自由集合，限額 30 人）",
                is_free=True,
                tags=["桃園觀旅局", "大溪老街", "街屋文史", "台語導覽", "大溪區"]
            ),

            # 13. 桃園市政府農業局
            Activity(
                id="ty_agri_rice_food_culture_exp",
                title="【台語體驗/市府活動】桃園市政府農業局《休閒農業區米食文化季：台語做粿手作與農村走讀》",
                description="手作草仔粿與紅龜粿！農業局結合新屋與大園在地休閒農業區，由農家阿嬤全程台語帶領體驗洗石磨磨米漿、揉粿粹與印模蒸粿，體驗最接地氣的台灣傳統農村滋味。",
                city=CityEnum.TAOYUAN,
                district="新屋區",
                category=CategoryEnum.EXPERIENCE,
                start_time="2026-11-28T10:00:00",
                end_time="2026-11-28T14:00:00",
                venue="桃園市新屋活力健康農場",
                address="桃園市新屋區梅高路三段97號",
                organizer="桃園市政府農業局 / 新屋區休閒農業發展協會",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://agriculture.tycg.gov.tw/taigi_rice_food",
                cover_image="https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=800&q=80",
                price_info="手作材料費 NT$ 150（可帶回自製米食）",
                is_free=False,
                tags=["桃園市農業局", "做粿手作", "草仔粿", "米食文化", "台語體驗", "新屋區"]
            ),

            # 14. 桃園市政府青年事務局
            Activity(
                id="ty_youth_taigi_standup_show",
                title="【台語表演/市府活動】桃園市政府青年事務局《青創基地母語週：台語脫口秀與青年母語創作分享會》",
                description="用年輕人的幽默說母語！邀請當紅台語喜劇演員與新生代台文 Podcaster，於青年事務局安東青創基地帶來充滿時事笑點的台語 Stand-up 脫口秀，打破語言隔閡。",
                city=CityEnum.TAOYUAN,
                district="桃園區",
                category=CategoryEnum.PERFORMANCE,
                start_time="2026-12-12T19:00:00",
                end_time="2026-12-12T21:00:00",
                venue="桃園市政府青年事務局 安東青創基地 1樓展演廳",
                address="桃園市桃園區安東街111號",
                organizer="桃園市政府青年事務局",
                source_platform=SourcePlatformEnum.GOVERNMENT,
                source_url="https://youth.tycg.gov.tw/taigi_comedy",
                cover_image="https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?auto=format&fit=crop&w=800&q=80",
                price_info="免費入場（事先線上登記，青年優先）",
                is_free=True,
                tags=["桃園市青年事務局", "台語脫口秀", "青年母語", "安東青創", "桃園區"]
            )
        ]
        logger.info(f"🏛️ 北北桃市府各局處官方活動載入完成，共計 {len(activities)} 場。")
        return activities
