import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('dashboard/data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

w42_chats = d.get('CHATS_BY_WEEK', {}).get('2026-W42', [])
phone_only = [c for c in w42_chats if c.get('channel') == '전화']

mgrs = {}
for c in phone_only:
    a = c.get('agent') or 'None'
    mgrs[a] = mgrs.get(a, 0) + 1

print(f'2026-W42 phone calls total={len(phone_only)}, breakdown={mgrs}')
