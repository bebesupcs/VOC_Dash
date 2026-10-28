# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('dashboard/data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

chats = d.get('CHATS_BY_WEEK', {}).get('2026-W42', [])
print(f'2026-W42 chats count: {len(chats)}')

targets = ['전광석', '김관나', '정은주', '심원규', '최윤명', '김하윤']

for c in chats:
    cust = c.get('cust') or c.get('custName') or ''
    if any(t in cust for t in targets):
        print(f"\nID: {c.get('id')} | Cust: {cust} | Date: {c.get('date')} {c.get('time')}")
        print(f"  Brand: {c.get('brand')} | Mid: {c.get('mid')} | Sub: {c.get('sub')}")
        print(f"  Prod: {repr(c.get('prod'))}")
        print(f"  Mfg: {repr(c.get('mfg'))}")
        print(f"  Mall: {repr(c.get('mall'))}")
        print(f"  Issue: {repr(c.get('issue'))}")
        print(f"  Act: {repr(c.get('act'))}")
        print(f"  Note: {repr(c.get('note'))}")

# Also check QUALITY_RAW
q_raw = d.get('QUALITY_RAW', [])
print(f"\nTotal QUALITY_RAW count: {len(q_raw)}")
w42_q = [q for q in q_raw if q.get('week') == '2026-W42']
print(f"W42 in QUALITY_RAW: {len(w42_q)}")
if w42_q:
    print("Sample W42 in QUALITY_RAW:", w42_q[0])
