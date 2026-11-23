# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('dashboard/data.json', encoding='utf-8'))
w43 = d['CTI_BY_WEEK']['2026-W43']

out_missed = [c for c in w43 if c.get('dir') == 'outbound' and c.get('ans') == 0]
print(f"Total Outbound Missed (ans=0) in W43: {len(out_missed)}")
for i, c in enumerate(out_missed[:10]):
    print(f"[{i+1}] {c.get('time')} | 상담사: {c.get('agent')} | 고객: {c.get('cust')} ({c.get('phone')}) | 통화시간: {c.get('talk')}초 | 대기(신호): {c.get('wait')}초 | 태그: {c.get('tag')} | 사유: {c.get('reason')}")
