# TW-Hokkien 翻譯歷史契約

目前已改回由接手的寫作者直接翻譯；本檔僅供舊 v2 紀錄核對或使用者明確要求本機模型時參考，不是日常執行指令。

## 歷史 TW-Hokkien 流程（2026-10-01稍早）

本節取代下方原先的 Codex 直接撰寫／兩輪台文校訂要求。排程時段與 GitHub 核實、接收、發布順序不變。
`data/editorial/config.json` 的 provider 為 `tw-hokkien`。本機同名 worker 使用 Codex 整理中文及核對事實，
台文必須實際透過 `~/.local/bin/taigi-translate` 由 `Taigi-Llama-2-Translator-13B:latest` 產生。
不依賴桌面任務保持開啟，不另建排程；模型不可用就停止，沒有其他模型備援。
無待編輯活動時仍是一般程式直接結束，不啟動 Codex 或翻譯模型。

每批包含 `input.json`、兩份規範及 `translation_terminology.json`。依 `scripts/tw_hokkien_worker_prompt.txt`：
先整理中文摘要／完整介紹與各自保護清單，分別翻譯；依工具紀錄還原固定資料，逐项核對事實與語意完整性。
使用者已接受模型，不另要求自然度審查；不能填寫虛構的自然度通過。漏譯、否定、角色、條件或新增事實仍攔下。
既有正式活動、保留名單與已接收稿件不重寫；試譯草稿不直接匯入。

### 正式結果 v2

保留 v1 所有欄位，`schema_version=2`，`editor={"provider":"tw-hokkien","model":"Taigi-Llama-2-Translator-13B:latest"}`。
`review.natural_taiwanese=false` 表示未另行評審，`facts_match` 和 `people_and_content_complete` 必須 true，`issues=[]` 且事實引句吻合。
新增 `translation`：`model`、64位十六進位 `model_digest`，以及 `fields` 的 summary_taigi／description_taigi。
每欄包含 `verified_translation`（CLI核對後、使用者用語修訂前的完整譯文）、`input_sha256`、`report_sha256`、`output_sha256`、
`cli_verified=true`、`protected_literals`、`user_overrides`（start/end字元位置、source、replacement、rule_id）。
目前只授權 `free-admission-mian-tsinn` 的 免費→免錢，不更動被保護的官方名稱、引句或固定資料。
結果只放文案、來源綁定與翻譯紀錄，不可修改活動欄位。文案不嵌入URL／HTML，連結仍由原activity欄位顯示。

由一般程式組裝，不能手填模型執行證明：

```sh
python3 scripts/tw_hokkien_result.py --workspace /批次目錄 --plan plans/活動ID.json
```

plan格式為 `{"activity_id":"ID","fields":{"summary_taigi":"translations/ID.summary.txt","description_taigi":"translations/ID.description.txt"},"review_file":"reviews/ID.json"}`。
review_file 包含上述review六欄，必須依實際核對填寫。程式重跑 CLI verify、檢查模型名稱與digest一致，保存地端紀錄，
套用已確認用語並更新evidence.claim（quote保留），通過v2檢查才寫results。原始中文、工具原稿和報告保留。
GitHub重建用語修改及比對雜湊；雜湊是追溯證據，不是遠端模型執行的獨立認證。
舊 v1 已接收資料繼續顯示；provider切換後的新稿必須為 v2，不偽造v1自然度通過。

下載命令改用 `python3 scripts/editorial_sync.py download --provider tw-hokkien`，validate/submit仍由外部程式處理。

