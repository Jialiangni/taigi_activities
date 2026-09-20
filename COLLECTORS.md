# 活動收集與授權設定

此文件描述 2026-09-18 重建後的實作。先前的失效端點與固定資料問題保存在 `CRAWLER_AUDIT.md`；該文件是修改前的歷史盤點。

## 資料流程

現行排程與台文交接以 [EDITORIAL_HANDOFF.md](EDITORIAL_HANDOFF.md) 為準：候選核實後先進待編輯佇列，收到合格新稿才加入正式活動。下列來源方法及核實規則維持使用。

`python3 -m crawler.collect` → `data/candidates/<source_id>.json`、`report.json` → 規則核實／必要時人工核對 → `data/verified_activities.json` → `main.py --check-sources` → 網站／ICS。

**收集成功不等於活動已核實。** 候選文件、公告、節目期間與單場演出有不同 `kind`；全部 `review_status=pending`。沒有自動把貼文時間轉成活動日期、不猜地區／免費票價、不自動覆寫正式清單。

## 各來源採用方式

| 來源 | 現行收集方式 | 邊界 |
|---|---|---|
| ACCUPASS | 網站實際使用的 `POST https://api.accupass.com/v3/search/SearchEvents`，逐一搜尋設定中的台語關鍵字，並同時限制城市代碼 `1、2、3`（臺北、新北、桃園）；`currentIndex` 分頁與 `total` 校驗，逐筆讀活動專頁 JSON-LD 及內文，再確認實際關鍵字；另保留公告表格中明列的月日與起迄時間 | 搜尋有廣泛相關結果，不能照單全收；JSON-LD 可能是系列總期間。單一場次若明列「台語場」、完整起迄、北北桃地點、主辦、正常狀態與免費報名，可重新讀頁後自動核實；完整日期／時間表且全程台語、共用場地、明列免費的系列可逐場核實；混合語言／場地、費用不明或欄位矛盾仍保留待判讀 |
| OPENTIX | 網站實際使用的 `POST https://search.opentix.life/search`、`nextOffset` 分頁；`GET https://csm.api.opentix.life/programs/{id}` | 依 `eventVenues[].events[]` 拆場次及場館；不能用節目總起迄日期代替單場。語言、異動與票種仍需核對 |
| 年代售票 | 官方關鍵字搜尋頁＋完整節目索引，讀每個節目內文及場次表格 | 關鍵字搜尋偏向標題，因此索引詳情補足內文提到台語的節目；沒有結束時間就留空 |
| 李江却基金會 | 官方 Blogger Atom feed，支援 `rel=next` 及 OpenSearch 分頁資訊 | 文章發表日期與活動日期分開；依出版者 feed 提供範圍收集 |
| 樂暢親子共學 | 官方 Wix `blog-feed.xml` | 同上；RSS 未列出的舊文不推論已完整覆蓋 |
| 台語站 | `POST https://www.gameislearning.url.tw/taigi.php` 依臺北、新北、桃園篩選並逐頁讀活動詳情；來源頁由使用者指定為全部皆是台語活動 | 語言直接信任，不再送人工語言判讀；仍須有北北桃地點與明確場次日期／時間才刊登。純文字 HTTPS 網址會辨識成可點的報名連結；活動專頁 img#myPic 原始海報會隨核實結果收錄，限本站 HTTPS 圖片路徑並保存來源證據；系列逐場拆分、過期移除、疑似重複擋下 |
| 圖書館、館舍、市府局處、民間團體 | `data/source_registry.json` 的 149 個入口；官方站內活動／消息連結發現與專頁讀取 | 通用網站收集器預設每站 30 頁、導航深度 3，翻頁不耗導航深度；PDF、圖片公告與未連出的舊資料需要另行核對 |
| 桃園市立美術館所屬館群 | 官網首頁 `__NEXT_DATA__` 的公開 news／info 資料集，保留公告內文 | 取代只會讀到防護頁的內頁爬取；實測可解析，但首頁亦可能間歇回傳 HTTP 428，屆時標失敗並需正常瀏覽器補查 |
| 文化部開放資料 | 依[官方介接文件](https://opendata.culture.tw/upload/dataSource/2021-02-18/9bee99c4-0732-4abd-b8c6-1a4bd0b62e64/db83c7223217e1d9947778256768153f.pdf)讀取各類別，保留 `showInfo` 各場次，依地址篩選北北桃，記錄命中的機構 | 補充上述機構與售票平台，不能保證各機構都有提供資料。`onSales=N` 不等於免費 |
| Instagram | `ig_hashtag_search` → `/{hashtag-id}/recent_media`，兩次均帶真實 `user_id`，支援平台的同值 after 游標 | 專業帳號、Facebook Login、Public Content Access；近期 24 小時公開媒體，非全站歷史搜尋 |
| Threads | 2026-09-20 已依使用者要求移除 | 不再收集貼文、回覆或產生候選提醒 |

票務搜尋 API 是本次從網站公開前端觀察並實測成功的網站介面，不是承諾永久穩定的第三方服務合約。格式改變、HTTP 失敗、重複頁面、缺少欄位均需處理為錯誤。

149 個入口包含三市圖書館、指定館舍、局處與台語路，以及54個圖書館分區和54個活動中心公告來源；部分同主管機關入口涵蓋多個館舍，原機構名保留於 aliases。文化部結果的 `matched_sources` 是來源映射，不保證該機構全部活動已取得。

## 執行方式

只需 Python 3.7+ 標準庫。`config.example.json` 現為收集器的可用設定，僅含關鍵字、標籤、執行上限與併發數，不含密鑰。

```bash
python3 -m crawler.collect
python3 -m crawler.collect --sources accupass,opentix,eraticket
python3 -m crawler.collect --sources public_libraries,museums,government
python3 -m crawler.collect --sources li_kang_khiok,le_chang
python3 -m crawler.collect --sources gameislearning
python3 -m crawler.collect --sources instagram
# 小量連線檢查（報告會明確標示截斷，不能宣稱全量）
python3 -m crawler.collect --max-details 5 --website-pages 3 --output /tmp/taigi-smoke
python3 -m unittest discover -s tests -v
```

預設每個售票來源最多 20 頁／關鍵字、200 個節目詳情，RSS 5 頁，通用網站收集器每站 30 頁，3 個來源並行，每個客戶端請求間隔至少 0.25 秒。北美館、桃園美術館使用各自的資料介面，不套用通用網站頁數上限。HTTP 429／5xx 僅有限重試，不繞過 CAPTCHA、不關閉 TLS。

台語站使用同一組搜尋頁／詳情上限。日期列表下一行統一標示時間時，將該時間套用至列表內每個日期；不同列表保留各自時間，優惠截止日不繼承課程時間。報名網址可來自詳情頁的「活動資訊來源」欄或公告正文純文字；網址需為無帳密的 HTTPS，網站詳情會分開顯示「報名／買票」與「活動公告」。缺完整日期或開始時間的公告仍留在候選報告，原因是場次欄位不足，並非需要重新判斷語言。

網站頁數上限是流量控制，包含入口、列表及詳情頁，不是活動數或日期範圍；30 頁不代表最近三週已完整搜尋。可用 `--website-pages 60` 覆寫單次上限，或增加確認過的活動列表入口。到達上限仍標 partial，沒有硬把有限的掃描範圍標為全站完整。配合預設從 8 頁提高到 30 頁，候選收集排程的執行時限由 40 分鐘提高到 90 分鐘。

## 報告與錯誤

- `ok`：這次設定下的請求與解析完成；不是核實活動，也不代表全站沒有遺漏。
- `partial`：達頁數／詳情上限，或部分請求失敗；保留已取得候選及錯誤。
- `failed`：該來源本次未取得候選且有錯誤。不得當成「來源沒有活動」。
- `needs_configuration`：缺社群環境變數；不送無效 API 請求，也不宣稱成功。
- `coverage_complete` 目前保守設為 false；即使列出的搜尋頁全部讀完，也不能推論平台／全地區完整。

報告記錄各來源候選數、成功回應數、時間、來源 URL、成功回應 SHA-256（解壓後內容）、失敗碼與截斷原因。API POST 的公開搜尋條件一併留存，不儲存授權標頭。候選全文是本機待審資料，已排除於 Git 與 GitHub Pages；Git 只保存精簡測試樣本與驗證摘要。

GitHub Actions 每日臺灣時間 03:15 或手動執行候選收集。來源摘要及公開來源候選存為 artifact，保留 14 天供核對；Instagram／Threads 原始授權內容不放進 artifact。Threads 已移除；舊 Threads 原始內容與快照均排除於新 artifact。收集失敗仍上傳已完成來源。收集工作本身不提交候選；完成後會觸發獨立的候選核實與發布工作，通過官方證據規則及後續全部檢查者才加入網站。

任何來源的請求／格式錯誤會令 CLI 回傳非零碼，但仍完成其他獨立來源並保存報告；單純到達已設定上限會標 partial。設定缺漏的社群屬明確待設定狀態，無法以此視為已驗證。

`crawler.audit_endpoints` 只保留重現舊版 404 問題的診斷；**新收集器請用 `crawler.collect`**。

## 社群授權接入口

使用者已確認目前沒有 Meta App／授權，因此 Instagram 目前只能完成介面與模擬回應測試，不能宣稱授權後實際回傳已驗證。Facebook 與 Threads 已依使用者要求退出每日收集流程。

| 環境變數／GitHub Secret 名稱 | 用途 |
|---|---|
| `INSTAGRAM_ACCESS_TOKEN` | Facebook Login 對應的使用者 token |
| `INSTAGRAM_USER_ID` | Instagram Business／Creator 帳號的數字 ID，不是 `me` |
| `META_GRAPH_VERSION` | 選用環境變數／GitHub Actions Variable，預設本次官方文件列出的 `v26.0` |

將值設在執行環境或 GitHub Actions Secrets，不要貼進聊天、Git、設定 JSON 或候選資料。專案不會自行建立 Meta App、申請擴大權限或代為完成授權同意。

Instagram 依[官方 hashtag search](https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-hashtag-search/)及[recent media 文件](https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-hashtag/recent-media/)，7 天最多 30 個不同標籤，請維持固定標籤避免累積超額。

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
| Instagram／Threads（歷史驗收） | 0 | 當時均為 needs_configuration；Threads 已於 2026-09-20 移除，Facebook 已於 2026-09-19 停用 |

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
- **台語路**：官方 `taigiloo.tw` RSS、最新消息及活動文章；aliases 包含台語路／台語鹿／台語路親子樂團／taigilok。Threads 帳號追蹤已於2026-09-20移除。官網 RSS 內容可能較舊，合作圖書館／售票平台仍是目前新活動的重要來源，不能說已完整取得社群貼文。

本輪指定網站驗收採每站 20 頁，當時日常預設為 8 頁（後續已提高至 30 頁）；到達上限如實列 partial，沒有全站完整涵蓋承諾。詳見 `data/audit/2026-09-18-museum-collection-report.json`。

```bash
python3 -m crawler.collect --sources tfam,ntm,228,228_national,ceramics,sshm,ntl,yingge_library,dadaocheng,taigiloo --website-pages 20
```

## 網站上限提高至 30 頁（2026-09-18）

設定檔、無設定時的預設值與機構群組入口均改為 30 頁；39 個通用網站收集器適用。51 項 Python 測試通過，另確認明確指定 60 頁仍會覆寫預設。

使用新預設實際重跑 MOCA、臺北文化局、新北文化局、桃園文化局，各成功讀取 30 頁且無請求錯誤；待核實候選分別為 0、1、1、0 筆。四站均達頁數上限而標 partial，沒有宣稱全站或最近三週已完整涵蓋。臺北文化局較先前 8 頁實測多取得 1 筆候選；候選仍需人工核對，不直接新增正式場次。詳見 [30 頁實測摘要](data/audit/2026-09-18-30-page-collection-report.json)。

後續已完成這兩筆候選核實：臺北公告已過期，新北系列剩餘場次缺少個別台語演出證據，新增 0 場；正式清單維持 63 場與 5 項導覽／展覽資訊。[逐筆核實紀錄](data/audit/2026-09-18-30-page-review.json)獨立保存，不改寫原始收集快照。


## 各區圖書館與活動中心擴充

新增108個分區來源後，當時共有158個收集器（registry149個）；後續加入台語站後為159個。名錄、方法及驗收範圍見 [DISTRICT_SOURCES.md](DISTRICT_SOURCES.md)。每入口預設30頁；日常排程會自動納入，無須逐一勾選。

```bash
python3 -m crawler.collect --sources public_libraries
python3 -m crawler.collect --sources community_centers
python3 -m crawler.collect --sources tpml_district_a,ntpclib_district_239,typl_district_14
```

臺北使用官方閱讀網的分館活動列表及數字分頁；新北使用官方行政區代碼及原表單分頁；桃園使用完整Filter欄位及CurrentPage表單。列表、詳情共用每入口30頁上限，優先讀含台語關鍵字的詳情。HTTP成功之外還會檢查桃園回傳行政區、重複列表與格式異動，避免把全市第一頁重複當作各區資料。

活動中心沿各區公所公開公告收集，需同時含中心及台語相關內容；不把場地租借、管理或收費辦法認作活動，不表示該區每一場館的未公開課表都有取得。候選收集不改變公開63場活動及5項導覽資訊。


## Threads 已移除（2026-09-20）

移除四帳號追蹤、Keyword Search、conversation 回覆收集、去識別快照與待判讀 Issue。每日排程與手動指定來源均不再提供 Threads；舊候選附件的 Threads 來源也不送進核實。歷史執行紀錄保留原始結果，未設定狀態不代表目前仍需設定。

## 李江却基金會：公告正文與系列核實清單（2026-09-18）

漏刊原因是已有文章候選卻未完成系列拆場核實，並非Feed頁數不足；舊候選ID與檔案指紋已保存在[核實紀錄](data/audit/2026-09-18-foundation-review.json)。本輪4個未來場次經逐場核實後進入正式清單。

- 持續讀取官方Blogger Atom及核准的Blogger分頁；每輪重讀收集範圍內的舊文章，沒有以近期發文篩掉未來場次。
- 從Feed本文保留超連結和純文字網址，擷取每個有效數字月日及鄰近文字。年份未明列時仍為null，發文年份僅作排序提示，不填入正式start_time。
- `limits.foundation_details`預設30篇，與Feed的5頁上限分開。含未來日期線索的文章優先；直接重讀文章的post-body正文、post-title標題，排除側欄推薦文章，保存原Feed與文章兩份證據。正文失敗保留Feed候選並標不完整，超限文章也保留。
- 每個 `li_kang_khiok.json` 額外輸出 `review_queue`，一篇文章內保留所有日期線索、報名與其他連結。Google表單單列為registration_links，其他報名平台仍在content_links，不能只看Google表單。report.json列review_item_count。
- 清單全部仍為pending；日期可能是截止日或歷程，不能自動認作場次。共用時間、上午／下晡、地點、年份、圖片公告、取消與延期需人工核對；不自動打開或提交報名表。

本次實跑5頁Feed＋30篇詳情，35個成功回應、0請求錯誤、246候選、182篇日期／報名核實項目；達兩項上限標partial，coverage_complete=false。`python3 -m crawler.collect --sources li_kang_khiok`可重跑。83項Python測試通過，新增回歸涵蓋三場公告、純文字報名、側欄隔離、共用時間、年份待核、上限、詳情失敗與未核實禁止刊登。

## 三市總館明確涵蓋（2026-09-18 最新）

目前159個收集器、150個registry入口，public_libraries群組60個。

| 總館 | 日常收集設定 | 本次限量6頁驗收 |
|---|---|---|
| 臺北市立圖書館總館 | 新增 `tpml_main`：[官方總館-全列表](https://reading.tpml.gov.taipei/News.aspx?n=C4252F536DF57EC4&sms=9D72E82EC16F3E64)，使用數字分頁專用收集器 | 6次成功回應，0候選，詳情未讀完，partial；不代表沒有台語活動 |
| 新北市立圖書館總館 | `ntpclib_district_220`：[板橋區全部館別](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=220)，不指定branch，包含位於板橋的總館 | HTTP502，failed；已設定但本次未完成連線驗收 |
| 桃園市立圖書館總館 | `typl_district_2`：Filter[4]=2.1，包含桃園區2及總館1；[官方GetVenues](https://www.typl.gov.tw/zh-tw/Home/GetVenues)另列總館branch 52 | 6次成功回應，3筆待核實候選，達上限partial |

[本次證據與請求摘要](data/audit/2026-09-18-main-libraries-check.json)保存名錄與回應指紋。日常仍預設30頁，本次6頁僅驗收設定。總館列表也可能刊登他館公告，必須逐筆核實場地；本輪不新增正式場次。

## 收集後核實與去重（2026-09-19）

每日03:15收集完成後觸發網站工作，不再以04:00獨立排程搶先建置。來源失敗但完整報告已保存時，其他成功候選仍進入核實。每筆決策記錄於 `data/audit/latest-candidate-review.json`；核實來源、保守限制、去重方法及36小時新鮮度門檻見 SPEC 第23節。OPENTIX結構化單場及明列語言證據符合嚴格條件時可自動通過；其餘資料不會因這一步已執行就被當作核實成功。


## 官方活動圖片

ACCUPASS、李江却、圖書館網站與列表、博物館網站、北美館JSON、桃園美術館內嵌正文皆保存可確認的 cover_image。圖片來源限該活動主圖、正文或圖片附件，不使用網站logo或其他活動縮圖。發布時沿用必要的來源重讀結果重新擷取，詳情完整顯示並可點開圖片；欄位與發布行為見 SPEC 第24節。圖片不等於活動事實已核實，PDF／動態防護頁不做猜測。


### 台語站補時順序與OCR（2026-09-19）

台語站優先公告，再追公開報名表單（Google Forms、BeClass、ACCUPASS），短網址／Linktree最多兩層、六頁；只在文字不足時讀該活動海報。缺結束時間也能補查，已有文字衝突不以海報裁決。跨頁身分、日期、場地、過期與去重維持核實；OCR低信心、缺明列年份、未知格式與轉址失敗均保留候選原因。GitHub排程已有繁體中文Tesseract依賴，圖片、文字與逐場證據會在發布前重查；細節及執行上限見SPEC第26節。

### 台語站內容抽取與台文（2026-09-19）

候選的 `official_description` 保存公告內實質介紹。核實時重新讀取正文，優先套用相同正文指紋與場次的 `directory_editorial.json` 校訂版，否則使用清理過的公告原文；不再用「台語站收錄的台語活動」覆蓋內容。卡片與詳情分用短介、長文；沒有校訂台文時明示原文。文案引文隨正式來源重新查驗，場次、費用和去重門檻維持。

### 台語站 → ACCUPASS 主來源（2026-09-19）

核實會重新讀台語站公告的報名連結。若指向ACCUPASS活動專頁，依活動ID、開始時間、城市對照已核實場次；已有者只刊主來源，尚未核實者直接抓取ACCUPASS送入原有核實規則，台語站不再繞過主來源另行刊登。分享參數不影響辨識，同一系列不同時間不合併。HTTP失敗、無明確單場或主來源日期矛盾仍pending。核實報告的`source_priority`記錄舊資料的合併或暫停刊登理由。
