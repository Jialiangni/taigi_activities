# 北北桃台語活動行事曆

彙整臺北、新北、桃園的台語表演、故事、繪本、體驗與導覽場次，提供搜尋、篩選、月曆，以及 Google / Apple 日曆加入與 ICS 訂閱。

- 網站：https://jialiangni.github.io/taigi_activities/
- ICS：https://jialiangni.github.io/taigi_activities/taigi_activities.ics
- 系統規格：[SPEC.md](SPEC.md)
- 本次核查：[SOURCE_AUDIT.md](SOURCE_AUDIT.md)
- 現行收集器與授權設定：[COLLECTORS.md](COLLECTORS.md)
- 重建前爬蟲核查：[CRAWLER_AUDIT.md](CRAWLER_AUDIT.md)

## 資料現況（2026-09-18）

既有 64 筆均來自寫在程式內的固定資料；其中 63 筆未取得支持原場次的公告，1 筆與官方節慶日期不符。它們已退出正式清單，原始內容與逐筆理由保存在 `data/audit/2026-09-18-legacy.json`。**未核實不等於證明活動不存在。**

第一輪先恢復 8 場已核實活動；本輪再逐場核對並新增 50 場，隨後補入臺博館2場與國臺圖×台語路3場，目前正式網站／ICS 共 **63 場：臺北 11、新北 10、桃園 42**。14 場確認免費、12 場需付費、37 場費用未公告。另有5項台語導覽／展覽資訊，不計入場次、不產生ICS。共使用 18 個官方活動專頁，OPENTIX 場次另外核對官方 API；詳見[本輪刊登摘要](data/audit/2026-09-18-published-expansion.json)。這不是北北桃全部活動。

目前採用**自動收集候選、人工核實、每日重查正式來源與建置**。收集器涵蓋售票、官方訂閱、機構網站與文化部開放資料；社群 API 接口已實作，但目前未設定授權。每筆資料保留核對時間；出發前仍應查看官方最新公告。內容重查只檢查必要資訊仍存在，不能取代人工判讀新增的取消／延期通知。

每站上限提高至30頁後，MOCA與三市文化局取得的兩筆候選已完成核實：一筆已過期，另一筆系列剩餘場次缺少台語演出證據，本輪未新增場次。詳見[核實結果](data/audit/2026-09-18-30-page-review.json)。

爬蟲驗收階段的 45 個入口保留 684 筆候選；本輪新增的 50 個場次是從其中逐場核對後另行刊登，候選原檔保留供追溯。ACCUPASS／機構網站／Feed 仍有執行上限；文化部親子 API 空回應、桃園美術館間歇 HTTP 428、社群缺授權均明確列入[逐來源報告](data/audit/2026-09-18-collection-report.json)，不能宣稱全部來源已完整取得。

## 建置與檢查

僅需 Python 3 標準庫（GitHub Actions 使用 Python 3.11）：

```bash
python3 -m unittest discover -s tests -v
python3 -m crawler.collect      # 自動收集候選與逐來源狀態，尚不刊登
python3 main.py                 # 以已核實資料建置，不連網
python3 main.py --check-sources # 重查所有官方頁必要內容，失敗不覆寫產物
node tests/test_frontend.cjs    # JS、篩選與下載內容檢查（需 Node.js 18+）
python3 server.py               # http://localhost:8080
```

若 macOS 的 Python 缺少系統 CA，可以指定系統憑證：

```bash
SSL_CERT_FILE=/etc/ssl/cert.pem python3 main.py --check-sources
```

不要關閉 TLS 憑證驗證。DNS、TLS、HTTP 或公告必要內容檢查失敗時，修復問題或重新核實後再執行。

## 發布流程

GitHub Actions 每日台灣時間 04:00、推送 `main` 或手動觸發時：執行測試 → 重查官方頁 → 建置 HTML / ICS → 僅上傳 `public/` 至 GitHub Pages。失敗不部署；排程成功時另將 HTML / ICS 提交回 Git。

`main.py` 只讀 `data/verified_activities.json`，不再載入示範資料、固定博物館／市府活動或未驗證的 API 結果。各來源已重建為候選收集器；使用 `python3 -m crawler.collect` 執行，結果寫入 `data/candidates/`。

新增活動前，請依 `SPEC.md` 核對活動名稱、單場日期時間、地點、台語內容及費用，留下活動專頁與核查紀錄。不用官方首頁、搜尋結果或一般景點頁替代活動證據。


## 各區圖書館與活動中心爬蟲

已加入臺北12區、新北29區、桃園13區，共54個圖書館分區入口及54個區公所活動中心公告入口；現有158個收集器，預設每入口30頁，納入每日收集排程。可分別使用 `--sources public_libraries` 與 `--sources community_centers`。方法、逐區名錄及連線限制見 [DISTRICT_SOURCES.md](DISTRICT_SOURCES.md)；有來源入口不代表所有場館與近三週資料完整，也不會直接新增未核實活動。
