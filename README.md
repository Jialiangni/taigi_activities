# 北北桃台語活動行事曆 (Taigi Activities Calendar Hub)

全台最完整的北北桃台語活動整合行事曆系統！為**臺北市、新北市、桃園市**的台語文化推廣活動提供單檔互動式行事曆與多平台資料彙整。

---

## 🌐 讓其他人也可以在線上瀏覽 (GitHub Pages 免費上線)

本專案已為您配置好 **GitHub Actions 自動化每日爬蟲與 GitHub Pages 部屬工作流程** (`.github/workflows/deploy.yml`)。

### 📌 上線步驟（只需 3 分鐘）：

1. **在 GitHub 建立新儲存庫**：
   - 到 [GitHub 新增儲存庫](https://github.com/new)
   - 專案名稱設為 `taigi_activities`（設為 **Public** 公開）

2. **將專案推送到 GitHub**：
   在終端機執行本專案提供的快速腳本：
   ```bash
   ./setup_github.sh
   ```
   或手動執行：
   ```bash
   git init -b main
   git add .
   git commit -m "🎉 初始發布：北北桃台語活動行事曆"
   git remote add origin https://github.com/您的GitHub帳號/taigi_activities.git
   git push -u origin main
   ```

3. **啟用 GitHub Pages**：
   - 進入 GitHub 儲存庫頁面，點選 **Settings** ➔ **Pages**
   - 在 **Build and deployment** 下方的 **Source**，切換為 **GitHub Actions** 即可！

🎉 **完成！**
- 所有人都可以透過網址瀏覽：`https://您的GitHub帳號.github.io/taigi_activities/`
- **全自動維護**：GitHub Actions 每天凌晨 04:00 (台灣時間) 會自動啟動爬蟲更新台語活動資料，並重新部署網站，完全不需手動維護！

---

## 💻 本機與區域網路預覽

如果您想先在自己的電腦瀏覽，或讓同一 Wi-Fi 下的手機/同事瀏覽：

```bash
python3 server.py
```
- 本機網址：`http://localhost:8080`
- 同 Wi-Fi 手機網址：終端機會自動顯示您的區網 IP（例如 `http://192.168.x.x:8080`）

---

## 🌟 整合資料來源與平台

1. **李江却台語文教基金會**（阿却賞、文化講堂、母語讀書會）
2. **樂暢親子共學**（幼兒台語繪本、故事屋、親子自然生態體驗）
3. **北北桃公立圖書館**（臺北市立圖書館、新北市立圖書館、桃園市立圖書館各區分館推廣活動）
4. **OPENTIX 兩廳院文化生活**（兩廳院售票、國家戲劇院、臺灣戲曲中心台語劇目）
5. **年代售票 (Era Ticket)**（歌仔戲、布袋戲、台語音樂會）
6. **Accupass 活動通**（台語工作坊、手作體驗、文史走讀活動）
7. **Facebook**（各大台語劇團、文化局官方粉絲頁公開活動）
8. **Instagram**（台語共學、幼兒繪本社群標籤貼文）
9. **Threads**（即時發起的社群台語走讀與聚會）
10. **Google Workspace**（一鍵加入 Google 日曆、匯出 `.ics` 日曆訂閱檔、Google 日曆 API 雙向同步）

---

## 🎭 涵蓋台語活動類別

- 🎭 **台語舞台劇**（阮劇團、狂想劇場、綠光劇團等現代與傳統劇目）
- 🎪 **台語表演**（歌仔戲、掌中戲/布袋戲、台語唸歌、月琴民謠、脫口秀）
- 📖 **台語故事**（囡仔古故事屋、圖書館志工說故事）
- 📚 **台語繪本**（親子共讀、台語童書新書分享會、繪本工作坊）
- 🎨 **台語體驗**（手作、傳統米食、陶瓷拉坯、木藝童玩、語言工作坊）
- 🚶 **台語導覽**（大稻埕、艋舺、淡水滬尾、大溪老街文史走讀）

---

## 📁 專案檔案結構

```
taigi_activities/
├── index.html                   # 【核心交付】單檔互動式台語活動行事曆
├── taigi_activities.ics         # iCalendar 標準日曆訂閱檔 (支援 Google/Apple 日曆)
├── server.py                    # 本機與區域網路 (手機) 即時預覽伺服器
├── setup_github.sh              # 一鍵發布至 GitHub Pages 助手腳本
├── .github/workflows/deploy.yml # GitHub Actions 自動排程爬蟲與部屬腳本
├── main.py                      # 一鍵爬取資料與生成 index.html 主程式
├── build_html.py                # 單檔 HTML 編譯渲染引擎
├── config.example.json          # 各平台 API 金鑰與設定檔範本
└── crawler/
    ├── __init__.py
    ├── models.py                # Activity 統一資料模型
    ├── processor.py             # 分類、去重、地區判定引擎
    ├── sample_data.py           # 北北桃精選台語示範資料集
    └── sources/                 # 10 大平台爬蟲與串接模組
```
