"""Show publication-ready and unresolved work separately in GitHub's run summary."""
import json,os
from pathlib import Path
from collections import Counter
root=Path(__file__).resolve().parents[1]
audit=json.loads((root/'data/audit/latest-candidate-review.json').read_text())
queue=json.loads((root/'data/editorial/queue.json').read_text())
pending=[d for d in audit['decisions'] if d['decision']=='pending']
lines=['### 活動核實與待辦',f"合格待編輯：{len(queue['items'])} 場；仍待核實：{len(pending)} 筆。",
       '待編輯為 0 不代表全部候選已核實。待核實候選會保存，下輪重新核對官方來源。','', '| 待核實原因 | 筆數 |','|---|---:|']
for reason,count in Counter(d['reason'] for d in pending).most_common():lines.append(f'| {reason} | {count} |')
lines+=['','完整逐筆原因、來源重查結果與後續處理方式：`data/audit/latest-candidate-review.json`。']
message='\n'.join(lines)+'\n'
print(message)
if os.environ.get('GITHUB_STEP_SUMMARY'):
 with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(message)
