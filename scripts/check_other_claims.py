import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\dev\VOC리포트\dashboard\data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

chats = d.get('CHATS_BY_WEEK', {}).get('2026-W41', [])
other_claims = [c for c in chats if c.get('nature') == '클레임' and c.get('brand') != '물티슈' and c.get('mid') not in ['배송', '시스템']]
print(f"Total other quality claims in 2026-W41: {len(other_claims)}")
for c in other_claims:
    print(f"  brand={c.get('brand')}, mid={c.get('mid')}, sub={c.get('sub')}, prod={c.get('prod')}")
