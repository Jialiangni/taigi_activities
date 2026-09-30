"""Show publication-ready and unresolved work separately in GitHub's run summary."""
import json,os
from pathlib import Path
from collections import Counter
root=Path(__file__).resolve().parents[1]
audit=json.loads((root/'data/audit/latest-candidate-review.json').read_text())
queue=json.loads((root/'data/editorial/queue.json').read_text())
pending=[d for d in audit['decisions'] if d['decision']=='pending']
backlog_path=root/'data/review_backlog.json'
backlog=json.loads(backlog_path.read_text())['candidates'] if backlog_path.exists() else pending
followup_path=root/'data/review_followups.json'
cases=json.loads(followup_path.read_text()).get('cases',{}) if followup_path.exists() else {}
owned=[cases[c.get('id',c.get('candidate_id'))] for c in backlog if c.get('id',c.get('candidate_id')) in cases]
lines=['### 活動核實與待辦',f"合格待編輯：{len(queue['items'])} 場；仍待核實（含系列未決場次）：{len(backlog)} 筆。",
       f'其中 {len(owned)} 筆已有 Codex 逐筆查證紀錄、缺少欄位與下次追查時間；新待辦由核實追查流程接手。',
       '待編輯為 0 不代表全部候選已核實。不得把連線失敗或資訊不足當成非台語活動。','', '| 本輪待核實原因 | 筆數 |','|---|---:|']
for reason,count in Counter(d['reason'] for d in pending).most_common():lines.append(f'| {reason} | {count} |')
lines+=['','完整逐筆原因：`data/audit/latest-candidate-review.json`；責任、查證發現與期限：`data/review_followups.json`；處理流程：`REVIEW_TRIAGE.md`。']
message='\n'.join(lines)+'\n'
print(message)
if os.environ.get('GITHUB_STEP_SUMMARY'):
 with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(message)
