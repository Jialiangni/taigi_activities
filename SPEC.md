# 北北桃台語活動行事曆：系統規格與交接

本版更新於 2026-09-18，以實際程式與來源核查結果取代舊版「全部來源自動抓取」「100% 有效」等未經證實描述。

## 1. 工作目的與範圍

協助民眾找到臺北市、新北市、桃園市可實際參加的台語活動。正確的單場日期、時間、地點、語言內容與報名來源優先於活動數量。前端為靜態 HTML，資料內嵌，不依賴執行時 API。

## 2. 資料與模組

- `data/verified_activities.json`：正式活動場次入口。
- `crawler/verified.py`：核實紀錄、時間、地區、費用、重複場次與來源內容檢查。
- `main.py`：載入資料，移除已結束場次，暫存完整產物後替換 HTML / ICS。
- `build_html.py`：前端模板；CSS / JavaScript 大括號須在 Python f-string 中寫成 `{{`、`}}`。
- `crawler/sources/google_workspace.py`：ICS 與 Google 日曆加入連結；**沒有 Calendar API 同步功能**。
- `data/audit/2026-09-18-legacy.json`：原 64 筆資料、程式來源、搜尋語句及不刊登理由。
- `SOURCE_AUDIT.md`：核查摘要、官方證據、限制與後續事項。
- `CRAWLER_AUDIT.md`：所有指定平台、場館、局處的爬蟲實況；`crawler/audit_endpoints.py` 提供售票搜尋端點診斷，不是爬蟲驗收或發布輸入。
- `crawler/collect.py`：158 個入口的候選收集流程；`collection.py` 提供安全 HTTP、HTML、候選結構；`culture.py` 解析文化部場次，`social.py` 處理 Meta 游標。
- `data/source_registry.json`：149 個官方機構／團體與分區入口與主管機關映射；`COLLECTORS.md` 說明方法、上限與授權。
- `crawler/sources/`：已改為真實資料收集；不再回傳固定資料。舊 `fetch_activities()` 接口會明確拒絕未審核資料，請改用 `.collect(client)`。
- `crawler/sample_data.py` 及 `processor.py`：保留的歷史實作；正式建置／候選收集均不使用。
- `config.example.json`：現行候選收集設定；僅含公開搜尋條件和流量上限。全部 Python 程式只需標準庫。

## 3. 正式資料規則

`schema_version: 1`；`sources` 按來源 ID 建立索引；`activities` 每筆包含 `activity` 與 `verification`。

來源需包含 HTTPS 活動／報名專頁 `url`、`title`、`checked_at`（含 +08:00）、核查當時原始 HTML 的 `snapshot_sha256`，以及可重查的 `required_text`。SHA-256 是本次讀取指紋，不是活動真實性的自動證明；未把整份第三方 HTML 納入 Git。

每筆活動需具備：

1. 穩定 `id`，不能使用 Python 隨機 hash。
2. 官方可支持的標題、主辦／活動計畫名稱、場館及北北桃城市。
3. `start_time` 與可取得的 `end_time`，完整 ISO-8601 `+08:00`。不使用抓取時間、貼文時間或任意兩小時作為活動時間。結束時間未公告時可設 null。
4. `source_url` 必須等於核實來源；不允許首頁或搜尋頁。
5. 費用三態：`true` 確認免費、`false` 確認收費、`null` 未公告。未知不得歸為免費或付費。
6. `verification.status=verified`、`language_evidence` 及 `confirmed_fields`。已核實欄位異動後必須重新核對，不得只機械複製欄位繞過審查。
7. 系列活動逐場拆分，不能把首場至末場的總期間當成連續活動。
8. 圖片必須有可靠來源及使用依據；目前正式活動未核實圖片，使用文字底圖，不將舊代表照片當作現場照。

人工核實是事實判讀步驟；程式只能驗證結構、一致性與必要字串，不能自動證明活動必然舉辦或永不異動。

## 4. 建置與失敗處理

`python3 main.py`：離線驗證已核實資料。`python3 main.py --check-sources`：額外連線讀取所有來源，驗證 HTTPS、HTTP 成功、未轉址至其他網域及必要文字存在。

任何檢查失敗都在產物替換前拋出錯誤；不得回退示範資料、默默略過壞來源或標記整體成功。空清單是合法結果，頁面需說明「目前没有已核實場次」，不是認定當地沒有活動。

來源抓取時間與人工核實時間分開：建置不改寫 `checked_at`。來源文字仍存在不保證沒有新增取消通知；接近活動日期仍需人工重查。新活動由獨立候選收集器發現；需人工核查再寫入正式清單，不能把收集時間當成核實時間。

OPENTIX 官方 HTML 的場次選單由動態 API 提供，不能只檢查節目內文。已核實來源另保存 `opentix_sessions`、`api_snapshot_sha256` 與 `api_checked_at`；正式活動以 `opentix_session_id` 對應。每日重查會比對官方 API 的場次時間、地點、票價、狀態與異動通知；缺場次或欄位改變即阻擋發布，不自動接受新值。

2026-09-18 本輪正式清單由 8 增為 58 場，新增與暫緩原因見 `data/audit/2026-09-18-published-expansion.json`。測試中的初始 8 場固定樣本保存在 `tests/fixtures/verified_catalog_base.json`，避免日常擴充正式清單破壞基礎驗證測試。

## 5. 前端與日曆

- 顯示台灣時間；篩選支援地區、六類活動、來源、費用、文字。
- 詳情直接連結官方活動／報名頁，顯示人工核對日期。
- Google 搜尋只是輔助查找，不是資料證據或保證能報名。
- Google Calendar 以 UTC 起迄時間搭配 `ctz=Asia/Taipei`。
- ICS 使用 UTC 時間、CRLF、文字跳脫、UTF-8 每行不超過 75 octets，保留穩定 UID；未提供結束時間時不產生虛構 DTEND。
- 單場下載、篩選下載與訂閱檔使用同一套後端序列化結果。
- 已下載並手動匯入的舊活動不會由本網站自動刪除；這次只更正公開訂閱檔及網頁。
- PWA manifest 保留；未實作 service worker，不宣稱離線快取可用。

## 6. GitHub Actions 與部署

`main` push、`workflow_dispatch`、UTC 20:00 排程觸發：單元測試 → 官方來源重查 → 建置 → `public/` 靜態檔案上傳 → Pages 部署。`public/` 僅包含 HTML、ICS、manifest、assets；不部署爬蟲、核查記錄、設定或測試。

新來源或網站改版造成檢查失敗時，需讀取原公告並修正檢查內容，不能關閉驗證。不要把字串檢查通過當成新增活動已完成事實核實。

## 7. 接續事項

- 逐步增加臺北及其他北北桃來源；不為各城市配額加入無證據場次。
- 已重建公開 API、RSS、機構網站與 Meta 授權讀取接口；執行結果與剩餘限制見 `COLLECTORS.md`、`data/audit/2026-09-18-collection-report.json`。
- 社群缺 App／帳號授權，尚待真實 API 驗收；動態網站、防護頁、圖片公告及未連出的舊活動仍可能需要人工或瀏覽器補查。
- 新增來源先寫入候選區，通過場次核實後才進入正式清單。
- 維護時先讀 README / SPEC / SOURCE_AUDIT、確認 Git 狀態，保留他人未提交修改。

## 8. 指定館舍、台語路與非場次資訊

2026-09-18 第二輪新增國臺圖與台語路合作故事 3 場、臺博館台語繪本親子共作 2 場，正式清單共 63 場（臺北 11、新北 10、桃園 42），另有 5 項導覽／展覽資訊。

`data/verified_resources.json` 與 `crawler/resources.py` 管理非單場資訊：台語語音、預約導覽、展期資訊。必須有語言證據、核對時間、來源 SHA-256 與 required_text；`--check-sources` 同樣重查內容，失敗不覆寫。含 expires_at 的展覽到期後排除；不產生 ICS、不計入場次數。正式 UI 提供獨立資訊區及頁首跳轉入口，資料經 HTML escape。

臺博館2020年導覽公告明示為舊頁，目前可讀取不代表真人導覽時間已確定。國臺圖故事每月日期採公告明列值，不能從「第3或4週」自行展開；系列總述11:00–12:00與單場11:00–11:50差異已向使用者顯示，採單場時間。臺博館活動需購票入館，is_free=false，說明活動本身免費。

第二輪當時收集入口共50個／registry41個；北美館改用官網實際 JSON 活動API，其餘指定館舍方法與限制詳見COLLECTORS.md。候選與正式刊登持續分離，相關推薦文字不可作為該展覽的台語證據。

通用網站收集器預設每站最多30頁（原8頁），包含入口、列表及詳情；可用 `--website-pages` 覆寫。候選收集排程時限為90分鐘，維持3個來源並行及既有請求間隔。頁數上限不代表最近三週完整涵蓋；達上限仍標 partial，`coverage_complete` 保持 false。


## 9. 各區圖書館與活動中心

新增54個圖書館分區來源、54個區公所活動中心公告來源，對應臺北12、新北29、桃園13區。registry共149入口，全部收集器共158個。每個入口預設最多30頁，可用 `public_libraries`（59入口，含原有5個）及 `community_centers`（54入口）群組執行，每日候選收集排程自動納入。

`crawler/library_sources.py` 直接讀官方分館清單與實際分頁：臺北閱讀網53個分館／閱覽室列表分配至12區，沿同一列表的數字頁碼翻頁；新北依官方area代碼查該區所有館別，依表單及CSRF續頁；桃園送出完整Filter[0]至Filter[4]查詢、以CurrentPage表單翻頁，並逐筆比對data-area防止篩選失效。桃園區另含總館。行政區是收集範圍，不直接當作活動實際地點。列表至少預留所有初始分館入口，最多約一半頁數用於翻頁，其餘讀活動詳情，優先台語關鍵字；未讀完明確列partial。

活動中心範圍為區公所官網公開的里民、市民、社區、區民中心公告；沿活動、課程、研習及中心相關連結收集。場地租借／收費規則不是可參加活動，不納入候選。此設計不宣稱各里私有社團、未公開課表或每一活動中心的社群已全數涵蓋。來源名錄與端點驗收見 DISTRICT_SOURCES.md。

新北圖書館若HTTP502或其他連線失敗，保留failed，不用舊快照假裝本輪取得資料。列表重複、行政區篩選被忽略、頁面格式異動均作為錯誤；候選仍須人工核實後才可發布。


## 10. 各區候選核實刊登（2026-09-18）

本輪14筆候選新增18個場次及4項資源，現為81場（臺北27、新北10、桃園44）及9項資訊。逐筆紀錄位於 `data/audit/2026-09-18-district-publication-review.json`。

官方明示起訖日期、固定星期與時間的整期課程，可在確認總時數一致後拆成實際日期；永春課程16次共32小時，每次標示整期報名及影印費自付，不能當作16個獨立可報名活動，也不能因免學費而標示全免。

非場次類型增加 `reading_resource`，呈現臺語閱讀推廣；`exhibition_resource` 標籤為「台語相關展覽」，避免一般書展被誤稱為語音導覽。日期範圍但沒有固定時刻的活動以資源卡呈現，沒有日曆事件；日期到期界線使用結束日的次日零時，並非推定館方營業時間。全部資源仍須通過相同官方來源檢查。


## 11. Facebook 粉專留言收集

`data/facebook_pages.json` 為Facebook待查名單，包含ChhutGoaKongTaiGi、Guaayingla、taigiloo及既有taigilok；由Facebook收集器自動載入。以 `FACEBOOK_PAGE_ID_MAP` 明確綁定數字ID；未設定逐項標needs_configuration。名稱或網址相似不可直接合併。

指定粉專預算內每篇feed貼文均先查comments stream游標分頁，涵蓋API可見回覆，不能因正文沒台語或報名連結就略過。保留留言連結出處與粉專作者判斷；其他留言者身份不保存。圖片貼文、留言失敗／超限保留待核實候選，空留言不視為零留言證明。每粉專200篇、每篇留言20頁為預設上限，可在config limits調整；所有結果仍待人工核實，不直接刊登。詳見COLLECTORS.md。
