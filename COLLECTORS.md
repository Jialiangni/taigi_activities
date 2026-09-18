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
| 圖書館、館舍、市府局處、民間團體 | `data/source_registry.json` 的 149 個入口；官方站內活動／消息連結發現與專頁讀取 | 通用網站收集器預設每站 30 頁、導航深度 3，翻頁不耗導航深度；PDF、圖片公告與未連出的舊資料需要另行核對 |
| 桃園市立美術館所屬館群 | 官網首頁 `__NEXT_DATA__` 的公開 news／info 資料集，保留公告內文 | 取代只會讀到防護頁的內頁爬取；實測可解析，但首頁亦可能間歇回傳 HTTP 428，屆時標失敗並需正常瀏覽器補查 |
| 文化部開放資料 | 依[官方介接文件](https://opendata.culture.tw/upload/dataSource/2021-02-18/9bee99c4-0732-4abd-b8c6-1a4bd0b62e64/db83c7223217e1d9947778256768153f.pdf)讀取各類別，保留 `showInfo` 各場次，依地址篩選北北桃，記錄命中的機構 | 補充上述機構與售票平台，不能保證各機構都有提供資料。`onSales=N` 不等於免費 |
| Facebook | 授權粉專 `/feed` 及逐篇 `/comments?filter=stream` 游標分頁，保留留言／回覆報名連結 | 指定名單的貼文先讀留言，不因本文無關鍵字排除；無完整留言可見性承諾 |
| Instagram | `ig_hashtag_search` → `/{hashtag-id}/recent_media`，兩次均帶真實 `user_id`，支援平台的同值 after 游標 | 專業帳號、Facebook Login、Public Content Access；近期 24 小時公開媒體，非全站歷史搜尋 |
| Threads | `https://graph.threads.com/v1.0/keyword_search`，RECENT／KEYWORD，游標分頁 | 需要 `threads_keyword_search` 才能搜尋公開貼文；缺該權限可能僅搜尋自己的貼文 |

票務搜尋 API 是本次從網站公開前端觀察並實測成功的網站介面，不是承諾永久穩定的第三方服務合約。格式改變、HTTP 失敗、重複頁面、缺少欄位均需處理為錯誤。

149 個入口包含三市圖書館、指定館舍、局處與台語路，以及54個圖書館分區和54個活動中心公告來源；部分同主管機關入口涵蓋多個館舍，原機構名保留於 aliases。文化部結果的 `matched_sources` 是來源映射，不保證該機構全部活動已取得。

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

預設每個售票來源最多 20 頁／關鍵字、200 個節目詳情，RSS 5 頁，通用網站收集器每站 30 頁，3 個來源並行，每個客戶端請求間隔至少 0.25 秒。北美館、桃園美術館使用各自的資料介面，不套用通用網站頁數上限。HTTP 429／5xx 僅有限重試，不繞過 CAPTCHA、不關閉 TLS。

網站頁數上限是流量控制，包含入口、列表及詳情頁，不是活動數或日期範圍；30 頁不代表最近三週已完整搜尋。可用 `--website-pages 60` 覆寫單次上限，或增加確認過的活動列表入口。到達上限仍標 partial，沒有硬把有限的掃描範圍標為全站完整。配合預設從 8 頁提高到 30 頁，候選收集排程的執行時限由 40 分鐘提高到 90 分鐘。

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
| `FACEBOOK_PAGE_ID_MAP` | 指定粉專 handle 到已確認數字 Page ID 的 JSON 對照；四個待查粉專須逐一設定 |
| `FACEBOOK_PAGE_IDS` | 額外數字粉專 ID，以逗號分隔；仍相容，但無法用來證明指定 handle 已涵蓋 |
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

爬蟲驗收當時，42 項 Python 測試、前端檢查及正式清單的 5 個官方來源重查通過，正式行事曆當時仍為 8 場。後續已逐場審核並新增 50 場，現在共 58 場；刊登紀錄另見 [正式清單擴充摘要](data/audit/2026-09-18-published-expansion.json)，不改寫上述歷史收集數。

## 指定館舍與台語路補強（2026-09-18 第二輪）

第二輪當時共 **50 個收集器**，registry 共 41 個入口。新增 `ntl`（國立臺灣圖書館／四號公園）、`yingge_library`、`228_national`、`dadaocheng`、`taigiloo`。`organizations` 群組可選取台語路。

- **北美館**：使用官網 JavaScript 的公開 `POST /ashx/Event.ashx?ddlLang=zh-tw`，JSON `State=Now, JJMethod=GetEv`。檢查 Status/Data 結構，逐筆篩選完整活動內容；本次 12 筆當期公告沒有台語關鍵字，不把手語當台語。
- **臺博館**：直接從本館、古生物館、南門館、鐵道部活動列表，跟隨官方連出的 `event.culture.tw/mocweb/reg/NTM/Detail.init.ctr` 報名頁。解析真正標題、排除「相關系列活動」污染，讀取 `viewDetail('id')` 連結但不執行網頁程式。個別場次仍需核對，不用系列首末日生成連續活動。
- **台北二二八紀念館**：監測藝文活動與特展列表；另新增不同館舍「二二八國家紀念館」台語團體預約服務，不能混為同一館。
- **陶博、十三行**：教育活動與展覽列表加已知導覽服務頁。`guide_service` 不自動生成日曆場次；華語定時真人導覽與臺語語音服務分開辨識。
- **鶯歌分館**：使用新北市圖 `area=239&branch=EA` 活動清單，EA 由官方 `getBranch?area=239` 回傳；分館介紹頁的 UUID 不能拿來當查詢代碼。候選標題須對應鶯歌，排除全市公告中其他分館的台語活動。
- **四號公園圖書館**：是國立臺灣圖書館，不是新北市圖；新增官網、官方最新消息 RSS 與台語路合作故事專頁。
- **迪化街**：先依大稻埕戲苑加入藝文處官方列表、已知《請戲—布袋戲一條街》特展；尚待確認使用者是否另指原林柳新／台原亞洲偶戲博物館，未宣稱兩館同一處。
- **台語路**：官方 `taigiloo.tw` RSS、最新消息及活動文章；aliases 包含台語路／台語鹿／台語路親子樂團／taigilok。官方粉專 `https://www.facebook.com/taigilok` 已登記，仍需 Meta 授權及正式 Page ID 才能透過既有 Facebook API 取得貼文。官網 RSS 內容可能較舊，合作圖書館／售票平台仍是目前新活動的重要來源，不能說已完整取得粉專。

本輪指定網站驗收採每站 20 頁，當時日常預設為 8 頁（後續已提高至 30 頁）；到達上限如實列 partial，沒有全站完整涵蓋承諾。詳見 `data/audit/2026-09-18-museum-collection-report.json`。

```bash
python3 -m crawler.collect --sources tfam,ntm,228,228_national,ceramics,sshm,ntl,yingge_library,dadaocheng,taigiloo --website-pages 20
```

## 網站上限提高至 30 頁（2026-09-18）

設定檔、無設定時的預設值與機構群組入口均改為 30 頁；39 個通用網站收集器適用。51 項 Python 測試通過，另確認明確指定 60 頁仍會覆寫預設。

使用新預設實際重跑 MOCA、臺北文化局、新北文化局、桃園文化局，各成功讀取 30 頁且無請求錯誤；待核實候選分別為 0、1、1、0 筆。四站均達頁數上限而標 partial，沒有宣稱全站或最近三週已完整涵蓋。臺北文化局較先前 8 頁實測多取得 1 筆候選；候選仍需人工核對，不直接新增正式場次。詳見 [30 頁實測摘要](data/audit/2026-09-18-30-page-collection-report.json)。

後續已完成這兩筆候選核實：臺北公告已過期，新北系列剩餘場次缺少個別台語演出證據，新增 0 場；正式清單維持 63 場與 5 項導覽／展覽資訊。[逐筆核實紀錄](data/audit/2026-09-18-30-page-review.json)獨立保存，不改寫原始收集快照。


## 各區圖書館與活動中心擴充

新增108個分區來源後，現共有158個收集器（registry149個）。名錄、方法及驗收範圍見 [DISTRICT_SOURCES.md](DISTRICT_SOURCES.md)。每入口預設30頁；日常排程會自動納入，無須逐一勾選。

```bash
python3 -m crawler.collect --sources public_libraries
python3 -m crawler.collect --sources community_centers
python3 -m crawler.collect --sources tpml_district_a,ntpclib_district_239,typl_district_14
```

臺北使用官方閱讀網的分館活動列表及數字分頁；新北使用官方行政區代碼及原表單分頁；桃園使用完整Filter欄位及CurrentPage表單。列表、詳情共用每入口30頁上限，優先讀含台語關鍵字的詳情。HTTP成功之外還會檢查桃園回傳行政區、重複列表與格式異動，避免把全市第一頁重複當作各區資料。

活動中心沿各區公所公開公告收集，需同時含中心及台語相關內容；不把場地租借、管理或收費辦法認作活動，不表示該區每一場館的未公開課表都有取得。候選收集不改變公開63場活動及5項導覽資訊。


## Facebook 指定粉專與留言報名連結（2026-09-18）

`data/facebook_pages.json` 是 Facebook 收集器實際載入的待查名單，與機構官網 registry 分開。排程仍有158個收集器，Facebook這一個收集器內含4個粉專目標：

- [出外講台語 Chhut-gōa kóng Tâi-gí](https://www.facebook.com/ChhutGoaKongTaiGi)
- [阿熒的教室](https://www.facebook.com/Guaayingla)
- [牽囡仔ê手 行台語ê路－台灣台語路協會](https://www.facebook.com/taigiloo)
- 先前指定的 [taigilok](https://www.facebook.com/taigilok)

前三個公開網址本次皆回HTTP200並取得上述頁面標題，僅證明公開頁可讀，不代表貼文、留言或數字Page ID已驗收。不同handle先獨立保留；經確認對應相同數字ID後才去重請求。

讀取方法：

1. 從授權的Page feed逐頁取得貼文，包含附件連結。指定名單內的貼文即使本文沒有台語關鍵字、沒有報名網址或只是一張圖片，仍保留候選並嘗試留言查詢。
2. 每篇貼文查 `/POST_ID/comments`，設定 `filter=stream`、`order=chronological`，追蹤after游標取得API可見的各層留言（含回覆）。不是只看預設精選留言，也不只取第一頁。
3. 擷取本文、留言與附件URL；Facebook `l.php?u=`包裝還原目的網址，短網址原樣保留，**不自動開啟或提交報名表**。保存貼文／留言出處、父留言ID、核對指紋及是否由粉專留言；若作者欄位不可見則標未知，不推定為主辦。一般留言者姓名／作者ID不保存。
4. 缺少comment ID時仍保留文字與連結，改用內容指紋辨識重複分頁。留言讀取失敗或超頁數保留已讀貼文及連結，標 `comments_incomplete`，不中止後續貼文。空回應只標「沒有可見留言」，不代表沒有留言或報名資訊。
5. 連結及留言只是核實線索，不自動視為官方報名頁；需核對主辦、活動日期、場地、語言、費用及是否取消後才刊登。圖片文字仍需人工核對。

預設每粉專最多200篇貼文（`limits.facebook_posts_per_page`），每篇留言最多20頁（`limits.facebook_comment_pages`），feed頁數仍為 `search_pages`。達上限明列未完成；每輪會重查讀取範圍內舊貼文的留言，不因貼文ID曾出現就跳過。沒有承諾完整歷史或近三週覆蓋。

授權設定範例（以下只是格式，數字是占位示例，不是真實Page ID）：

```json
{"ChhutGoaKongTaiGi":"123","Guaayingla":"456","taigiloo":"789","taigilok":"012"}
```

將實際對照設為 `FACEBOOK_PAGE_ID_MAP` 環境變數／GitHub Secret；token仍使用 `FACEBOOK_ACCESS_TOKEN`。需確認對每個Page及留言都具讀取資格；能讀本文不保證能讀留言，尤其非自己管理的粉專。不能將任意登入token當作通用粉專讀取權限。

目前無Meta授權，實跑是 **needs_configuration / 0候選**，4個目標逐一列於 `facebook.json` 及 `report.json` 的 `page_status`，不是「四個粉專都沒有活動」。本輪74項測試通過（含11項留言／待查名單測試）；官方API仍待授權後實測。見[公開頁與待設定紀錄](data/audit/2026-09-18-facebook-watchlist-review.json)、[Meta官方Post SDK](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/post.py)及[留言介面文件](https://developers.facebook.com/docs/graph-api/reference/object/comments/)。

原有artifact排除規則持續排除facebook.json，授權貼文及留言不公開、不自動寫入Git或網站。


## 李江却基金會：公告正文與系列核實清單（2026-09-18）

漏刊原因是已有文章候選卻未完成系列拆場核實，並非Feed頁數不足；舊候選ID與檔案指紋已保存在[核實紀錄](data/audit/2026-09-18-foundation-review.json)。本輪4個未來場次經逐場核實後進入正式清單。

- 持續讀取官方Blogger Atom及核准的Blogger分頁；每輪重讀收集範圍內的舊文章，沒有以近期發文篩掉未來場次。
- 從Feed本文保留超連結和純文字網址，擷取每個有效數字月日及鄰近文字。年份未明列時仍為null，發文年份僅作排序提示，不填入正式start_time。
- `limits.foundation_details`預設30篇，與Feed的5頁上限分開。含未來日期線索的文章優先；直接重讀文章的post-body正文、post-title標題，排除側欄推薦文章，保存原Feed與文章兩份證據。正文失敗保留Feed候選並標不完整，超限文章也保留。
- 每個 `li_kang_khiok.json` 額外輸出 `review_queue`，一篇文章內保留所有日期線索、報名與其他連結。Google表單單列為registration_links，其他報名平台仍在content_links，不能只看Google表單。report.json列review_item_count。
- 清單全部仍為pending；日期可能是截止日或歷程，不能自動認作場次。共用時間、上午／下晡、地點、年份、圖片公告、取消與延期需人工核對；不自動打開或提交報名表。

本次實跑5頁Feed＋30篇詳情，35個成功回應、0請求錯誤、246候選、182篇日期／報名核實項目；達兩項上限標partial，coverage_complete=false。`python3 -m crawler.collect --sources li_kang_khiok`可重跑。83項Python測試通過，新增回歸涵蓋三場公告、純文字報名、側欄隔離、共用時間、年份待核、上限、詳情失敗與未核實禁止刊登。
