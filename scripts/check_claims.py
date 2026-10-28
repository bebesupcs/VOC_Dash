import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\dev\VOC리포트\dashboard\data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

chats_w41 = d.get('CHATS_BY_WEEK', {}).get('2026-W41', [])
print(f"Total chats in 2026-W41: {len(chats_w41)}")

claims_w41 = [c for c in chats_w41 if c.get('nature') == '클레임']
print(f"Total claims in 2026-W41: {len(claims_w41)}")

print("\n--- All Claims in 2026-W41 ---")
for c in claims_w41:
    print(f"ID={c.get('id')} | brand={c.get('brand')} | mid={c.get('mid')} | sub={c.get('sub')} | prod={c.get('prod')} | valid={c.get('valid')}")

print("\n--- Current Quality Claims filter: brand in [물티슈, 스킨케어, 패밀리, 헬로, 홈] and mid != '배송' ---")
q = [c for c in claims_w41 if c.get('brand') in ["물티슈", "스킨케어", "패밀리", "헬로", "홈"] and c.get('mid') != '배송']
print(f"Count: {len(q)}")
for c in q:
    print(f"  ID={c.get('id')} | brand={c.get('brand')} | mid={c.get('mid')} | sub={c.get('sub')} | prod={c.get('prod')}")
