# Meta Model API 活動翻譯

2026-10-01 使用者選擇改用 Muse API。正式提供者識別為 `meta-model-api`，指定模型 `muse-spark-1.3`。
目前傳輸方式是 **Muse Code 1.4.2 背景呼叫官方 Model API**，不是 Desktop 操作，也不是繞過 Muse 管理的登入直接抽出 OAuth 權杖。
Muse Code 與模型版本分開記錄。CLI 登入方式為 `muse login`；憑證不放 Git、不寫入翻譯結果。

## 翻譯及核對

```sh
python3 scripts/muse_translate.py --input /批次/中文.txt --facts /批次/保護資料.json --output /批次/翻譯.txt
python3 scripts/muse_translate.py --verify /批次/翻譯.txt
python3 scripts/meta_result.py --workspace /批次 --plan plans/活動ID.json
```

`--facts` 是原文內必須逐字保留的 JSON 字串清單，包含姓名、作品、角色必要專名、日期、金額與單位。
例如需保留 `200元`，不能只列 `200`。中文稿由 Codex 依核實來源整理，台文完全由 Muse Spark 產生。
模型呼叫沒有 shell、寫檔或網路搜尋工具權限，不載入其他個人技能，最多一個模型步驟，外層120秒截止。
原文與模型回覆視為資料，不能當作操作指令。

輸出含模型原樣的 `.txt`、`.translation.json`，以及 `.txt.audit/` 內的提示詞、事件串流、診斷及原文。
程式只接收同一次 run 的完整終結回覆，核對指定模型、原文提示詞與固定資料。
缺固定資料時只留 `.draft.txt` 並回傳 exit 3；失敗不自動換模型或重送。既有成功輸出先核對來源與事件雜湊後重用。
`ready` 只表示回覆完成及固定資料存在，並非已通過語意核對。Codex仍逐項核對人物、角色、內容、否定、限制、數量與費用。
不作独立自然度評審、不潤飾模型台文。無法忠實還原的語意錯誤保留草稿，不組裝可發布结果。

## 結果 v3

沿用交接契約的來源／規範雜湊、活動ID、長短文及事實引句；`editor` 為 `meta-model-api` / `muse-spark-1.3`。
`translation` 包含 model、transport=`muse-code`、fields。每欄含 verified_translation、input_sha256、report_sha256、output_sha256、artifact_verified、run_id、protected_literals、user_overrides。
`meta_result.py` 必須從實際保存的事件與原稿重建，不能由編輯者手填執行證據。
run_id 是 Muse CLI 的執行識別，不是 API response ID；不捏造雲端模型 digest。
`review.natural_taiwanese=false`，facts_match 和 people_and_content_complete 必須依核對結果為 true，issues空且引句吻合。
原有「免費→免錢」使用者修訂仍另存追溯，官方名稱與原始引句保留。
遠端驗證只能證明內容與追溯資料一致，不能獨立認證模型服務確實執行或譯文自然度。

## 排程與舊資料

沿用 `editorial_gate.py`：週二／五08:00檢查，0筆不啟動AI；有工作才由 Codex 整理中文與核對、Muse API翻譯、一般程式驗證及回傳。
`runner.json` 新增 `meta-model-api` worker；Git內的 `data/editorial/config.json` 選同名provider。
其他排程與既有149筆保留活動、已發布文案不重寫。旧v1/v2保留；新提交必須符合目前provider與v3。
沒有新增 Desktop 定時測試。電腦仍需可執行並連網；Muse授權或服務不可用時明確失敗，無替代模型。

## 直接 HTTP 入口

`scripts/meta_translate.py` 是另外準備的單次 HTTP 試譯入口，使用環境變數 `MODEL_API_KEY`，不讀取 Muse OAuth Keychain。
它尚未接入正式結果組裝，也不自動從 Muse Code 切換過去。直接 HTTP 實測需另有官方 API key；現行已登入 CLI 的 API 路徑可先運作。
官方文件：[Quickstart](https://dev.meta.ai/docs/quickstart)、[Responses API](https://dev.meta.ai/docs/protocols/responses)。
