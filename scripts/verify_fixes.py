# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('dashboard/data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

# 1. Check August sealing tag items
print("=== 1. August Sealing Tag Items ===")
for cid in ['6a8a8906594dae54a1ca', '6a6cb1cfdfe288eb6e34']:
    found = False
    for wk, clist in d.get('CHATS_BY_WEEK', {}).items():
        for c in clist:
            if c.get('id') == cid:
                print(f"Found {cid} in {wk}: journey={c.get('journey')}, tag={c.get('tag')}, prod={c.get('prod')}, act={c.get('act')[:30]}")
                found = True
                break
        if found: break
    if not found:
        print(f"{cid} NOT FOUND in CHATS_BY_WEEK")

# 2. Check W42 target chats
print("\n=== 2. W42 Targets from Screenshot ===")
w42_chats = d.get('CHATS_BY_WEEK', {}).get('2026-W42', [])
targets = ['전광석', '정은주', '김하윤', '심원규', '최윤명', '김관나']
for c in w42_chats:
    cust = c.get('cust') or ''
    if any(t in cust for t in targets) and c.get('journey') in ('제품사용', '품질'):
        print(f"[{c.get('date')}] {cust} | {c.get('sub')} | Prod: {c.get('prod')}")
        print(f"   Mfg: {c.get('mfg')} | Mall: {c.get('mall')}")
        print(f"   Issue: {c.get('issue')[:50]}")
        print(f"   Act: {c.get('act')[:50]}")
        print()
