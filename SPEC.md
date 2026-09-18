# 北北桃台語活動行事曆：系統規格與交接

本版更新於 2026-09-18，以實際程式與來源核查結果取代舊版「全部來源自動抓取」「100% 有效」等未經證實描述。

## 1. 工作目的與範圍

協助民眾找到臺北市、新北市、桃園市可實際參加的台語活動。正確的單場日期、時間、地點、語言內容與報名來源優先於活動數量。前端為靜態 HTML，資料內嵌，不依賴執行時 API。

## 2. 資料與模組

- `data/verified_activities.json`：目前唯一正式資料入口。
- `crawler/verified.py`：核實紀錄、時間、地區、費用、重複場次與來源內容檢查。
- `main.py`：載入資料，移除已結束場次，暫存完整產物後替換 HTML / ICS。
- `build_html.py`：前端模板；CSS / JavaScript 大括號須在 Python f-string 中寫成 `{{`、`}}`。
- `crawler/sources/google_workspace.py`：ICS 與 Google 日曆加入連結；**沒有 Calendar API 同步功能**。
- `data/audit/2026-09-18-legacy.json`：原 64 筆資料、程式來源、搜尋語句及不刊登理由。
- `SOURCE_AUDIT.md`：核查摘要、官方證據、限制與後續事項。
- `crawler/sample_data.py`、舊 `crawler/sources/` 模組及 `processor.py`：保留的舊實作；正式建置不使用。
- `config.example.json`、`requirements.txt`：舊爬蟲構想的參考，不是目前建置必需配置／依賴。

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
8. 圖片必須有可靠來源及使用依據；目前 8 場未核實圖片，使用文字底圖，不將舊代表照片當作現場照。

人工核實是事實判讀步驟；程式只能驗證結構、一致性與必要字串，不能自動證明活動必然舉辦或永不異動。

## 4. 建置與失敗處理

`python3 main.py`：離線驗證已核實資料。`python3 main.py --check-sources`：額外連線讀取所有來源，驗證 HTTPS、HTTP 成功、未轉址至其他網域及必要文字存在。

任何檢查失敗都在產物替換前拋出錯誤；不得回退示範資料、默默略過壞來源或標記整體成功。空清單是合法結果，頁面需說明「目前没有已核實場次」，不是認定當地沒有活動。

來源抓取時間與人工核實時間分開：建置不改寫 `checked_at`。來源文字仍存在不保證沒有新增取消通知；接近活動日期仍需人工重查。自動發現新活動尚待後續實作，不在本次完成範圍。

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
- 舊李江却、樂暢、圖書館、年代、Threads 抓取函式為空；博物館及市府模組為固定資料。Accupass、OPENTIX 與社群解析亦未通過正式來源驗證，暫不啟用。
- 後續新增爬蟲應先寫入候選區，通過場次核實後才進入正式清單。
- 維護時先讀 README / SPEC / SOURCE_AUDIT、確認 Git 狀態，保留他人未提交修改。
