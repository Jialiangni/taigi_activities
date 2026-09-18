# 活動收集與授權設定

此文件描述 2026-09-18 重建後的實作。先前的失效端點與固定資料問題保存在 `CRAWLER_AUDIT.md`；該文件是修改前的歷史盤點。

## 資料流程

`python3 -m crawler.collect` → `data/candidates/<source_id>.json`、`report.json` → 人工核對 → `data/verified_activities.json` → `main.py --check-sources` → 網站／ICS。

**收集成功不等於活動已核實。** 候選文件、公告、節目期間與單場演出有不同 `kind`；全部 `review_status=pending`。沒有自動把貼文時間轉成活動日期、不猜地區／免費票價、不自動覆寫正式清單。

## 各來源採用方式

| 來源 | 現行收集方式 | 邊界 |
|---|---|---|
| ACCUPASS | 網站實際使用的 `POST https://api.accupass.com/v3/search/SearchEvents`，`currentIndex` 分頁與 `total` 校驗；逐筆讀活動專頁 JSON-LD 及內文，再確認實際關鍵字 | 搜尋有廣泛相關結果，不能照單全收；JSON-LD 可能是系列總期間，標 `event_period`，須另核對各梯次與票種 |
| OPENTIX | 網站實際使用的 `POST https://search.opentix.life/search`、`nextOffset` 分頁；`GET https://csm.api.opentix.life/programs/{id}` | 依 `eventVenues[].events[]` 拆場次及場館；不能用節目總起迄日期代替單場。語言、異動與票種仍需核對 |
| 年代售票 | 官方關鍵字搜尋頁＋完整節目索引，讀每個節目內文及場次表格 | 關鍵字搜尋偏向標題，因此索引詳情補足內文提到台語的節目；沒有結束時間就留空 |
| 李江却基金會 | 官方 Blogger Atom feed，支援 `rel=next` 及 OpenSearch 分頁資訊 | 文章發表日期與活動日期分開；依出版者 feed 提供範圍收集 |
| 樂暢親子共學 | 官方 Wix `blog-feed.xml` | 同上；RSS 未列出的舊文不推論已完整覆蓋 |
| 圖書館、館舍、市府局處 | `data/source_registry.json` 的 36 個機構入口；官方站內活動／消息連結發現與專頁讀取 | 預設每站 8 頁、導航深度 3，翻頁不耗導航深度；PDF、圖片公告與未連出的舊資料需要另行核對 |
| 桃園市立美術館所屬館群 | 官網首頁 `__NEXT_DATA__` 的公開 news／info 資料集，保留公告內文 | 取代只會讀到防護頁的內頁爬取；實測可解析，但首頁亦可能間歇回傳 HTTP 428，屆時標失敗並需正常瀏覽器補查 |
| 文化部開放資料 | 依[官方介接文件](https://opendata.culture.tw/upload/dataSource/2021-02-18/9bee99c4-0732-4abd-b8c6-1a4bd0b62e64/db83c7223217e1d9947778256768153f.pdf)讀取各類別，保留 `showInfo` 各場次，依地址篩選北北桃，記錄命中的機構 | 補充上述機構與售票平台，不能保證各機構都有提供資料。`onSales=N` 不等於免費 |
| Facebook | 授權的粉專 Graph `/feed`＋游標分頁，再依貼文文字篩選 | 指定粉專範圍；沒有全 Facebook 搜尋承諾 |
| Instagram | `ig_hashtag_search` → `/{hashtag-id}/recent_media`，兩次均帶真實 `user_id`，支援平台的同值 after 游標 | 專業帳號、Facebook Login、Public Content Access；近期 24 小時公開媒體，非全站歷史搜尋 |
| Threads | `https://graph.threads.com/v1.0/keyword_search`，RECENT／KEYWORD，游標分頁 | 需要 `threads_keyword_search` 才能搜尋公開貼文；缺該權限可能僅搜尋自己的貼文 |

票務搜尋 API 是本次從網站公開前端觀察並實測成功的網站介面，不是承諾永久穩定的第三方服務合約。格式改變、HTTP 失敗、重複頁面、缺少欄位均需處理為錯誤。

36 個機構入口包含三市圖書館、指定館舍與局處；部分同主管機關入口涵蓋多個館舍，原機構名保留於 aliases。文化部結果的 `matched_sources` 是來源映射，不保證該機構全部活動已取得。

## 執行方式

只需 Python 3.7+ 標準庫。`config.example.json` 現為收集器的可用設定，僅含關鍵字、標籤、執行上限與併發數，不含密鑰。

```bash
python3 -m crawler.collect
python3 -m crawler.collect --sources accupass,opentix,eraticket
python3 -m crawler.collect --sources public_libraries,museums,government
python3 -m crawler.collect --sources li_kang_khiok,le_chang
python3 -m crawler.collect --sources facebook,instagram,threads
# 小量連線檢查（報告會明確標示截斷，不能宣稱全量）
python3 -m crawler.collect --max-details 5 --website-pages 3 --output /tmp/taigi-smoke
python3 -m unittest discover -s tests -v
```

預設每個售票來源最多 20 頁／關鍵字、200 個節目詳情，RSS 5 頁，網站 8 頁，3 個來源並行，每個客戶端請求間隔至少 0.25 秒。HTTP 429／5xx 僅有限重試，不繞過 CAPTCHA、不關閉 TLS。

網站頁數上限是流量控制；要增加範圍可以調大上限或增加確認過的活動列表入口。沒有硬把有限的掃描範圍標為全站完整。

## 報告與錯誤

- `ok`：這次設定下的請求與解析完成；不是核實活動，也不代表全站沒有遺漏。
- `partial`：達頁數／詳情上限，或部分請求失敗；保留已取得候選及錯誤。
- `failed`：該來源本次未取得候選且有錯誤。不得當成「來源沒有活動」。
- `needs_configuration`：缺社群環境變數；不送無效 API 請求，也不宣稱成功。
- `coverage_complete` 目前保守設為 false；即使列出的搜尋頁全部讀完，也不能推論平台／全地區完整。

報告記錄各來源候選數、成功回應數、時間、來源 URL、成功回應 SHA-256（解壓後內容）、失敗碼與截斷原因。API POST 的公開搜尋條件一併留存，不儲存授權標頭。候選全文是本機待審資料，已排除於 Git 與 GitHub Pages；Git 只保存精簡測試樣本與驗證摘要。

GitHub Actions 每日臺灣時間 03:15 或手動執行候選收集。來源摘要及公開來源候選存為 artifact，保留 14 天供核對；Facebook／Instagram／Threads 的授權內容不放進 artifact。收集失敗仍上傳已完成來源。此工作不自動提交候選或修改公開行事曆。

任何來源的請求／格式錯誤會令 CLI 回傳非零碼，但仍完成其他獨立來源並保存報告；單純到達已設定上限會標 partial。設定缺漏的社群屬明確待設定狀態，無法以此視為已驗證。

`crawler.audit_endpoints` 只保留重現舊版 404 問題的診斷；**新收集器請用 `crawler.collect`**。

## 社群授權接入口

使用者已確認目前沒有 Meta App／授權，因此這三個來源目前只能完成介面與模擬回應測試，不能宣稱授權後實際回傳已驗證。

| 環境變數／GitHub Secret 名稱 | 用途 |
|---|---|
| `FACEBOOK_ACCESS_TOKEN` | 可讀取指定粉專的 token；不屬於自己的粉專需另外具備公開內容存取資格 |
| `FACEBOOK_PAGE_IDS` | 經確認的數字粉專 ID，以逗號分隔；不再預設未核對的帳號別名 |
| `INSTAGRAM_ACCESS_TOKEN` | Facebook Login 對應的使用者 token |
| `INSTAGRAM_USER_ID` | Instagram Business／Creator 帳號的數字 ID，不是 `me` |
| `THREADS_ACCESS_TOKEN` | 具 `threads_basic`、`threads_keyword_search` 的 Threads token |
| `META_GRAPH_VERSION` | 選用環境變數／GitHub Actions Variable，預設本次官方文件列出的 `v26.0` |

將值設在執行環境或 GitHub Actions Secrets，不要貼進聊天、Git、設定 JSON 或候選資料。專案不會自行建立 Meta App、申請擴大權限或代為完成授權同意。

Facebook 讀取範圍依[官方 Page feed 文件](https://developers.facebook.com/docs/graph-api/reference/page/feed/)的權限與角色要求；Instagram 依[官方 hashtag search](https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-hashtag-search/)及[recent media 文件](https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-hashtag/recent-media/)，7 天最多 30 個不同標籤，請維持固定標籤避免累積超額；Threads 依[官方 keyword search 文件](https://developers.facebook.com/docs/threads/keyword-search/)。

設定後先跑對應來源，檢查實際 token 權限、成功回應、分頁和候選內容，才能將社群來源標成已連線驗收。

## 2026-09-18 實測結果

45 個入口的完整執行，加上基金會／美術館／社群的指定重查，詳見 [逐來源驗收摘要](data/audit/2026-09-18-collection-report.json)。這是不同時間的最新逐來源結果彙整，並非假稱同時完成的單次快照。

| 來源 | 待核實候選 | 本次結果 |
|---|---:|---|
| ACCUPASS | 49 | 發現 942 個節目，讀取上限 200 筆詳情；全文過濾掉 151 筆無實際關鍵字的廣泛搜尋結果。兩個關鍵字亦達搜尋頁數上限；partial |
| OPENTIX | 306 場次 | 98 個節目拆分場次，無請求／解析錯誤 |
| 年代售票 | 12 場次 | 讀取 81 個節目詳情，無請求／解析錯誤；候選仍需核對所在地 |
| 文化部 | 49 場次 | 親子類別 4 及官方替代介面均回傳空內容，保留 partial 錯誤 |
| 李江却基金會 | 246 篇 | 正確跟隨官方 Blogger 分頁；到達 5 頁上限 |
| 樂暢 | 16 篇 | 官方 RSS 回應與解析完成 |
| 36 個機構入口 | 6 篇 | 多數到達 8 頁上限；桃園美術館 17:00 曾取得 1 篇，但 17:07 重查 HTTP 428，最新結果保留失敗，未以舊成功掩蓋 |
| Facebook／Instagram／Threads | 0 | 均為 needs_configuration；使用者尚未設定 App／授權 |

合計 684 筆候選，包含文章、公告、節目期間及場次，也可能含過期內容或尚未確認地區的資料；不是 684 場已核實活動。ACCUPASS 的最終關鍵字過濾以這輪剛取得的完整文字重算，原始來源欄位及回應指紋保留於本機，摘要另記錄重算時間。

42 項 Python 測試、前端檢查及正式清單的 5 個官方來源重查通過。正式行事曆仍為原來已核實的 8 場。
