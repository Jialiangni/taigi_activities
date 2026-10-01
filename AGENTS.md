# 專案協作規則

先閱讀 README.md 與 SPEC.md；以目前程式、資料與使用者最新決定為準。

## 台語內容

撰寫、翻譯或校訂本專案的活動簡介、活動紹介、介面台文前，必須閱讀
[TAIGI_EDITORIAL.md](TAIGI_EDITORIAL.md)，並使用可用的 `taiwanese-language` skill。
不確定的詞義、用字或臺羅，先用 `lookup_taiwanese` 核對；工具不可用時依 skill 的備援方式處理。

現行活動翻譯依 `TAIGI_EDITORIAL.md` 首節與 [共用技能](skills/taiwanese-language/SKILL.md)：由接手的寫作者先理解整段中文及上下文，再按台語語序重寫；現在由 Codex 直接完成。
不自動呼叫 TW-Hokkien、Muse 或其他翻譯模型。寫作者可修稿，並完成整句自檢及事實核對；不另啟動獨立自然度評審，也不要求逐筆人工批准。
可攜交接見 [TRANSLATION_HANDOFF.md](TRANSLATION_HANDOFF.md)；使用者已確認的用語須按適用語境採用。

- 預設採自然、親切、資訊具體的活動編輯語氣，漢字為主、必要時配臺羅。
- 先理解活動，再按台語語序重寫整句；不可只替換華語單字。
- 主講／演出者、內容重點與參加限制不可為了精簡而省略，也不可添加來源未支持的事實或評價。
- 字典確認詞義，編輯確認整句；查得到每個字不代表整句自然。
- 不以生僻字、俗諺、羅馬字或語尾詞數量判斷台語品質。
- 保留官方標題、姓名、地點、時間、費用、URL、原始資料和已採用的介面詞語。
- 使用者的新修訂優先；例句未經使用者確認，不可標記為使用者偏好或母語者審定。
- 已確認的翻譯用語見 [data/translation_terminology.json](data/translation_terminology.json)，只套用所列語境；模型原稿及核對紀錄保留，使用者指定修訂另存並記錄，不冒稱模型原樣輸出。

自動流程採 GitHub 核實佇列 → 地端編輯 → GitHub 接收發布，詳見
[EDITORIAL_HANDOFF.md](EDITORIAL_HANDOFF.md)。執行者可為 Codex 或其他 AI，格式與品質要求相同。
由 `scripts/editorial_gate.py` 一般程式先下載檢查；0筆不啟動AI。AI僅在獨立批次工作目錄編輯，
不重讀整個儲存庫、不重跑爬蟲、不自行呼叫API；下載、驗證及回傳由外部程式負責。
只回傳 `data/editorial/results/` 的文案結果，由 GitHub 檢查來源版本及校訂後發布。
日常排程不使用 `main.py --write-ai`；舊 API 編輯器僅保留為明確手動使用的備用工具。
`data/ai_taigi.json` 的保留名單和既有校訂文案不得為了補跑而移除、重設或覆寫。
