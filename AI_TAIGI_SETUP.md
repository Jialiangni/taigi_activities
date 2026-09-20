# 舊 API 模式設定（保留備用，非現行排程）

2026-09-20 已依使用者最新決定改為 GitHub 核實佇列＋地端編輯，
詳見 [EDITORIAL_HANDOFF.md](EDITORIAL_HANDOFF.md)。**日常流程不需要 API key，也不在 Actions 呼叫 AI。**
下列內容是原先 API 實作的設定與驗收歷史；僅在未來明確選用手動 API 模式時適用。
原先「設定金鑰後每日自動生成」已不適用，目前 deploy workflow 不注入該金鑰。

# 原 API 模式設定

## 一次設定

1. 登入 [OpenAI API 平台](https://platform.openai.com/)，建立／選擇專案，設定 API 付費方式或可用額度。
   API 按所選模型的輸入、輸出用量計費，參考[官方費率](https://developers.openai.com/api/docs/pricing)。
2. 在 [API keys](https://platform.openai.com/api-keys) 建立該專案的 Secret key，確保有 Responses API 和所選模型的使用權限。
3. 開啟本儲存庫 [Actions secrets 設定](https://github.com/Jialiangni/taigi_activities/settings/secrets/actions)，
   按 **New repository secret**，Name 填 `OPENAI_API_KEY`，Secret 貼上金鑰後儲存。
   不把金鑰貼入對話、程式碼或公開設定檔。
4. 預設使用 `gpt-5.4`。若要換模型，在同一設定區的 **Variables** 建立 `TAIGI_AI_MODEL`，
   填帳號可用且支援 Responses API structured outputs 的模型 ID。
   更換模型不會重寫既有成稿。
5. 等下一次每日發布，或到 [Actions](https://github.com/Jialiangni/taigi_activities/actions/workflows/deploy.yml)
   選 **Run workflow**。只會處理未列入保留名單、尚無成稿且通過來源重查的新活動。
   沒有新活動時，API 呼叫數為0；工作成功不代表已實際測試金鑰或模型品質。

實作參考：[OpenAI 文字生成](https://developers.openai.com/api/docs/guides/text)、
[結構化輸出](https://developers.openai.com/api/docs/guides/structured-outputs)、
[GitHub secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)。

## 實際流程

通過既有核實、去重、正式來源重查後，AI 讀取該場次的官方介紹與事實，以及 `TAIGI_EDITORIAL.md`：

1. 撰寫卡片摘要、完整介紹並提出疑詞（最多8詞）。
2. 程式實際查萌典詞目；查詢未完成或未查得完整詞條時，暫不採用這次成稿，不拼湊讀音。
3. AI 根據詞義與來源校訂。
4. 另一個獨立 API 請求只審查成稿，核對台語自然度、人物角色、內容完整度與事實，並回傳原文引句。
5. 程式檢查結構、引句確實存在、成稿事實片段確實存在、未新增原文沒有的數字或超連結。
   通過才保存成稿；自動檢查仍不能保證母語語感或排除所有誤譯。

本機的 `lookup_taiwanese` 功能已有標準庫版本移入 `crawler/taiwanese_dictionary.py`，
GitHub 不依賴個人電腦上的 MCP 安裝。尚無使用者認可的範例集，因此目前不假冒已有 few-shot 標準答案。

## 保留既有文案與限制

- 啟用前149筆正式紀錄全部保護，不進 AI 重寫；包含歷史場次，不等同當日網站場數。
- 人工／對話校訂文案優先，不修改 `ui_taigi.json` 或原有各平台 `*_editorial.json`。
- 新活動成稿按活動 ID 與原文、人物／主辦、時間、地點等內容綁定；內容未變，不再呼叫模型。
- 原文或場次重要欄位變動時，舊 AI 稿不再套用，只重新處理那筆新制活動；來源核實門檻仍照常阻擋未核實變更。
- 每臺灣日最多開始5筆編輯，每筆最多3次 API 請求，每次最多5000輸出 token，輸入上限50000字元。
  這是用量限制，並非固定金額保證。單筆通常少於上限，但尚待真實 API 試跑量測。
- 同一份活動內容同日不重試，最多跨日嘗試2次；仍未通過列 `needs_attention`，保留原文，不每日重寫。
- API 連線或權限錯誤後停止本輪後續呼叫；缺金鑰不消耗嘗試次數，新增活動先以原文發布。
- 嘗試及快取隨成功發布提交至 Git；失敗工作的結果留在14天附件。
  如果工作在提交前失敗，下次全新 runner 不會自動還原該附件，因此可能再嘗試；需要時先檢查附件再補跑。
- 網站建置、前端測試、來源核實或 Git 推送失敗時，原有發布阻擋規則維持不變。

## 如何確認真的運作

查看 Actions 摘要「新活動台文編輯」和 `ai-editorial-results` 附件：

| 狀態 | 意義 |
| --- | --- |
| `existing_copy_preserved` | 既有活動／文案，沒有 AI 重寫 |
| `cached` | 已生成且內容相同，直接重用 |
| `approved` | 這輪完成3個 API 步驟、查詞（有疑詞時）及程式檢查 |
| `missing_api_key` | 還沒設定金鑰，保留原文 |
| `pending` | 呼叫或校訂失敗，原因見 `reason` |
| `retry_next_day`／`daily_limit` | 等下一輪符合重試／額度條件時再處理 |
| `needs_attention` | 同內容已嘗試兩次，需處理具體問題；Actions 留警告 |
| `service_unavailable` | 本輪 API 已失敗，暫停後續付費請求 |
| `source_too_long` | 來源超過安全長度，保留原文待處理 |

只有 `approved` 和保存的 API response ID／usage，才表示有完成實際生成；
「已提供金鑰」或以假 API 執行單元測試，不代表真實模型已通過驗收。

## 首次驗收紀錄（2026-09-20 16:03 臺灣時間）

- 實作提交 `e9f12e9`；[GitHub 工作 35498290586](https://github.com/Jialiangni/taigi_activities/actions/runs/35498290586) 的191項測試全部通過。
- 本機重新建置後的前端篩選／ICS檢查通過；移植後的字典已用「費氣」完成真實網路查詢。
- 尚未設定 `OPENAI_API_KEY`，沒有真實 AI 付費請求或台文生成品質驗收。
- 該次部署在 AI 步驟之前被原有來源檢查阻擋：OPENTIX 節目 `2085288862221320193`
  的 HTML 缺場地文字；直接重查官方 API 後，場地仍在，但 `events` 是空陣列，
  無法比對場次 `2085288863274115073`。已存場次為9/20 15:10–17:10，不能據此推論取消或任意修改時間。
- 未停用核實門檻、未改舊台文／官方資料、該次未更新 Pages。後續必須重新通過來源檢查，
  並在有 API 金鑰與合格新活動時，才能驗收完整真實生成與發布鏈路。
