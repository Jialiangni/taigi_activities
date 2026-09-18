# 北北桃台語活動行事曆

彙整臺北、新北、桃園的台語表演、故事、繪本、體驗與導覽場次，提供搜尋、篩選、月曆，以及 Google / Apple 日曆加入與 ICS 訂閱。

- 網站：https://jialiangni.github.io/taigi_activities/
- ICS：https://jialiangni.github.io/taigi_activities/taigi_activities.ics
- 系統規格：[SPEC.md](SPEC.md)
- 本次核查：[SOURCE_AUDIT.md](SOURCE_AUDIT.md)
- 全來源爬蟲驗收：[CRAWLER_AUDIT.md](CRAWLER_AUDIT.md)（ACCUPASS／OPENTIX 舊 API 實測 404；社群與其他來源尚未通過驗收）

## 資料現況（2026-09-18）

既有 64 筆均來自寫在程式內的固定資料；其中 63 筆未取得支持原場次的公告，1 筆與官方節慶日期不符。它們已退出正式清單，原始內容與逐筆理由保存在 `data/audit/2026-09-18-legacy.json`。**未核實不等於證明活動不存在。**

重新由 5 個官方活動／報名專頁核對後，收錄 8 場：新北 2 場、桃園 6 場，臺北尚無納入場次。5 場確認免費，3 場費用未公告。這是本次已核實清單，不代表北北桃全部活動。

目前採用**人工核實、每日重查來源與建置**，尚未完成全平台自動抓取。每筆資料保留核對時間；出發前仍應查看官方最新公告。內容重查只檢查必要資訊仍存在，不能取代人工判讀新增的取消／延期通知。

## 建置與檢查

僅需 Python 3 標準庫（GitHub Actions 使用 Python 3.11）：

```bash
python3 -m unittest discover -s tests -v
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

`main.py` 只讀 `data/verified_activities.json`，不再載入示範資料、固定博物館／市府活動或未驗證的 API 結果。舊爬蟲程式保留供後續改善，並非目前啟用的正式來源。

新增活動前，請依 `SPEC.md` 核對活動名稱、單場日期時間、地點、台語內容及費用，留下活動專頁與核查紀錄。不用官方首頁、搜尋結果或一般景點頁替代活動證據。
