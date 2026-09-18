# 北北桃台語活動行事曆 (Taigi Activities) 系統規格書與維護交接指南 (SPEC.md)

本文件旨在為任何接手本專案的 AI 工具、開發者或自動化管線提供完整、清晰、具體且無相依性黑箱的工程架構說明。

---

## 1. 專案目標與願景
1. **業務目標**：聚合臺北市、新北市、桃園市三大都會區內所有「台語/母語」相關之藝文表演、美術館/博物館導覽、市府局處活動、親子繪本與文史走讀活動。
2. **架構目標**：
   - **完全自給自足 (Zero-backend at runtime)**：前端為單檔 `index.html`，所有活動資料直接內嵌為 JavaScript 常數物件 `ACTIVITIES_DATA`，免去執行時期 API 依賴。
   - **100% 穩定連線**：嚴禁死連結或無效憑證，所有連結必須為現存活官方域名或自動帶入關鍵字之 Google 即時搜尋。
   - **貼近現場之代表性圖片**：不使用 generic/無關插圖，優先使用爬蟲原圖，次之對應至內建之在地高清現場照片庫 (`assets/images/`)。
   - **每日全自動部署**：透過 GitHub Actions 定時執行 `python3 main.py`，更新 `index.html` 與 `taigi_activities.ics` 並發布至 GitHub Pages。

---

## 2. 系統架構圖 (Architecture Overview)

```
[排程觸發器]
GitHub Actions (每日 04:00 台灣時間 / UTC 20:00)
    │
    ▼
[資料收集層 (crawler/sources/)]
├── museums.py           (北北桃各大公私立美術館與博物館)
├── government.py        (北北桃市政府文化局、教育局、觀傳局、農業局、青年局)
├── public_libraries.py (臺北市立圖書館、新北市立圖書館、桃園市立圖書館)
├── sample_data.py       (李江却基金會、樂暢親子共學、OPENTIX、年代售票、Accupass)
    │
    ▼
[資料處理與去重引擎 (crawler/processor.py)]
├── ActivityProcessor.clean_and_normalize()
│   ├── 同 ID 去重
│   ├── 同一時間 (精確到分) + 同場館 去重
│   ├── 同一日 + 核心標題關鍵字 去重
│   ├── 縣市與行政區正規化 (TAIPEI / NEW_TAIPEI / TAOYUAN)
│   ├── 六大分類推論 (舞台劇/表演/故事/繪本/體驗/導覽)
│   └── 智慧真實場景圖片指派 (assign_representative_image)
    │
    ▼
[發布建置層 (build_html.py & main.py)]
├── 生成 taigi_activities.ics (iCal 通用行事曆訂閱檔)
└── 生成 index.html (單檔響應式 PWA 視覺網頁，內嵌完整資料與樣式)
    │
    ▼
[部署發布 (GitHub Pages)]
https://jialiangni.github.io/taigi_activities/
```

---

## 3. 資料結構規格 (`crawler/models.py`)

所有活動資料均使用 Python 標準庫 `dataclasses` 定義，不依賴任何外部 ORM。

```python
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
    LIBRARIES = "北北桃市立圖書館"
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
    start_time: str = ""         # ISO-8601: "YYYY-MM-DDTHH:MM:SS"
    end_time: Optional[str] = None
    venue: str = ""
    address: str = ""
    organizer: str = ""
    source_platform: SourcePlatformEnum = SourcePlatformEnum.OPENTIX
    source_url: str = ""         # 必須為有效可連通之官方網站或查詢入口
    cover_image: str = ""        # 本地 assets/images/*.jpg 或官方原圖
    price_info: str = "免費"
    is_free: bool = True
    tags: List[str] = field(default_factory=list)
```

---

## 4. 關鍵模組規範

### 4.1. 連結穩定性規範 (URL Health & Fallback)
1. **不使用暫時性或無效憑證網址**：新北市政府部分內部子網域因憑證鏈問題對特定手機瀏覽器不相容，統一採用 `https://tour.ntpc.gov.tw/zh-tw/Attraction/Detail?wnd_id=60&id=...` 或官方入口。
2. **社群平台無效連結處理**：嚴禁將 `source_url` 設為泛用首頁（例如 `threads.net`, `instagram.com`, `calendar.google.com`），若該活動源自社群發起，`source_url` 指向該活動舉辦場地之官方網站（例如剝皮寮、米倉劇場、信誼親子館）。
3. **前端雙重保險**：
   - 點擊「前往官方網站」直接開啟已校驗之官方場館/售票網頁。
   - 點擊「Google 查詢本活動報名/購票」，前端自動組裝 `${title} ${organizer} 台語 報名 售票` 帶入 Google 搜尋，確保使用者 100% 找到確切購票與報名資訊。

### 4.2. 代表性圖片映射規格 (`assets/images/`)
所有圖片皆位於本地 `assets/images/`，依活動主題自動配對，避免網路外連圖源失效：
- `tfam_museum.jpg`：臺北市立美術館
- `ntm_museum.jpg`：國立臺灣博物館本館
- `railway_department.jpg`：臺博館鐵道部園區
- `moca_contemporary.jpg`：台北當代藝術館
- `beitou_hotspring.jpg`：北投溫泉博物館
- `taipei_astronomy.jpg`：臺北市立天文科學教育館
- `lin_antai_courtyard.jpg`：林安泰古厝
- `confucian_temple.jpg`：臺北孔廟
- `yingge_ceramics.jpg`：鶯歌陶瓷博物館 / 老街
- `shisanhang_museum.jpg`：十三行博物館
- `tamsui_fort_heritage.jpg`：淡水紅毛城 / 淡水古蹟博物館
- `gold_museum_mining.jpg`：黃金博物館 / 金瓜石採金
- `taiwan_tea_culture.jpg`：坪林茶業博物館
- `ntcam_new_art_museum.jpg`：新北市立美術館
- `lin_family_garden.jpg`：板橋林家花園
- `sanchong_military_village.jpg`：空軍三重一村
- `hengshan_calligraphy.jpg`：橫山書法藝術館
- `taoyuan_children_art.jpg`：桃園市兒童美術館
- `daxi_wood_museum.jpg`：大溪木藝生態博物館
- `taiwanese_opera.jpg`：歌仔戲演出
- `glove_puppetry.jpg`：布袋戲 / 掌中戲
- `theater_stage_play.jpg`：現代台語舞台劇
- `standup_comedy.jpg`：台語脫口秀 / 說唱
- `taigi_picture_book.jpg`：親子繪本 / 幼兒共讀
- `temple_storytelling.jpg`：廟埕講古 / 故事屋
- `traditional_rice_cake.jpg`：米食手作 / 做粿體驗
- `wanli_fishing_port.jpg`：萬里蟹 / 漁港文化
- `dadaocheng_walk.jpg`：大稻埕 / 迪化街走讀

---

## 5. 自動化部署管線規格 (`.github/workflows/deploy.yml`)

1. **觸發條件**：
   - 每日定時：`cron: '0 20 * * *'` (台灣時間凌晨 04:00)。
   - 手動觸發：`workflow_dispatch`。
   - 代碼推送：`push` 到 `main` 分支。
2. **建置步驟**：
   ```bash
   python3 main.py
   git add index.html taigi_activities.ics assets/
   # 若有變更則自動提交並部署至 GitHub Pages
   ```
3. **零依賴環境**：執行環境僅需標準 Python 3.x，無需安裝額外 pip 套件。

---

## 6. 接手與擴充指南 (Handoff Instructions)

若任何新工具或工程師欲擴充此專案：
1. **新增資料來源**：
   - 於 `crawler/sources/` 建立新的 crawler 類別（例如 `new_source.py`），實作 `fetch_activities() -> List[Activity]`。
   - 在 `main.py` 中引入並將其活動加入 `all_activities`。
2. **調整去重規則**：
   - 修改 `crawler/processor.py` 中之 `clean_and_normalize`。
3. **調整前端樣式與互動**：
   - 編輯 `build_html.py`。注意該檔案為 Python f-string 模板，內部所有 JavaScript 與 CSS 雙大括號 `{}` 必須轉義為 `{{}}`。
4. **驗證指令**：
   ```bash
   python3 main.py
   python3 -c "import json, re; c = open('index.html').read(); print('Events count:', len(json.loads(re.search(r'const ACTIVITIES_DATA = (\[.*?\]);', c, re.S).group(1))))"
   ```
