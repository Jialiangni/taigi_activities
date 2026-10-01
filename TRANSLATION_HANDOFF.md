# 台文翻譯快速接手

共用方法只有一份：[taiwanese-language/SKILL.md](skills/taiwanese-language/SKILL.md)。
先理解整段中文與上下文，再按台語敘述方式重寫，查證疑詞，最後修稿及核對原意。
目前由 Codex 直接完成；模型只是執行者，不是這份方法的依賴。

## 在其他專案使用

把 `skills/taiwanese-language/` 整個資料夾複製過去即可，內含方法與最小交接格式。
Codex 已安裝同名個人技能，可直接說「用 `$taiwanese-language` 翻譯這段文字」。
其他工具或模型不支援技能時，請它讀 `SKILL.md`，再提供完整原文、用途、必要上下文及專案用語。
可直接貼的交接指令與JSON輸入示例見 [references/handoff.md](skills/taiwanese-language/references/handoff.md)。
不需要本專案爬蟲、排程、API key或原本的聊天紀錄；網站用語只在明確適用時帶過去。

## 本網站換模型或執行器

- **仍用 Codex，只換模型：** 調整本機 `runner.json` 的 `workers.codex.argv` 模型參數，模型ID使用實際可用且使用者選定的值；未指定時沿用CLI的模型設定。語言規範、網站schema與排程不用改。
- **改由其他工具執行：** 在同一個 `runner.json` 新增 `workers.<provider>.argv`，將 Git 的 `data/editorial/config.json` 中 `provider` 改成同名識別值並提交。新執行器必須可接 stdin 提示詞、在 `{workspace}` 批次目錄讀寫並輸出原契約的 `results/*.json`。無對應本機命令便停止，不自動換人執行。

本機設定：`~/Library/Application Support/TaigiEditorial/runner.json`。命令及登入資料留在本機，不放公開Git。
手動交接也可使用既有命令：

```sh
python3 scripts/editorial_sync.py download --provider codex --output .editorial-work
# 交給指定執行者：.editorial-work/input.json、共用技能、編輯規範與用語表。
# 接手者只把完成稿寫到 .editorial-work/results/。
python3 scripts/editorial_sync.py validate --results .editorial-work/results
python3 scripts/editorial_sync.py submit --results .editorial-work/results
```

換provider時，download的參數一起改為該識別值。發布權限仍由原任務決定；複製技能本身不授權發布。
每批自帶 `skills/taiwanese-language/` 和 `translation_terminology.json`，不依賴個人技能是否安裝。
正式schema見 [EDITORIAL_HANDOFF.md](EDITORIAL_HANDOFF.md)。新稿使用通用v1，記實際執行者；寫作者整句自檢不冒稱獨立評審或母語者審定。
舊稿、TW-Hokkien v2歷史紀錄及149筆保留名單不因換執行者失效。
