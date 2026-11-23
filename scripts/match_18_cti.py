# -*- coding: utf-8 -*-
import sys, json
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('dashboard/data.json', encoding='utf-8'))
chats_w43 = {c['id']: c for c in d['CHATS_BY_WEEK']['2026-W43']}
cti_w43 = d['CTI_BY_WEEK']['2026-W43']

ids = [
    '6ad960ddcc38aa812c02', '6ad96eb99f8f5c8602d8', '6adab675bb17cb5c2f5e',
    '6adab6c0c5801f58adcf', '6adac3e96866aa0d3f46', '6adac63bad715eebbd90',
    '6adae4ffcfd53fa4f4c0', '6adafd98409070fe85e7', '6adea98bb3ef87387978',
    '6adeab620319cce2a025', '6adeb733334ff561d354', '6adedafe2c35d72ad841',
    '6adf046d1accfdb6e3db', '6ae01189004f95939596', '6ae019106d552ede2c55',
    '6ae037a55192063d56a4', '6ae057d6b9f1a4bcd63b', '6ae194fb65d6b3a828b2'
]

print(f"{'No':^3} | {'Chat ID':^22} | {'채팅시간':^19} | {'CTI시간':^19} | {'오차':^5} | {'방향':^7} | {'ans':^4} | {'CTI 사유':^20} | {'CTI 태그':^20} | {'통화':^4} | {'대기':^4}")
print("-" * 140)

reason_counts = {}

for i, cid in enumerate(ids):
    chat = chats_w43.get(cid)
    ct = chat['time']
    cdt = datetime.strptime(ct, '%Y-%m-%d %H:%M:%S')
    
    matches = []
    for c in cti_w43:
        if not c.get('time'): continue
        t = datetime.strptime(c['time'], '%Y-%m-%d %H:%M:%S')
        diff = abs((t - cdt).total_seconds())
        if diff <= 60:
            matches.append((diff, c))
    matches.sort(key=lambda x: x[0])
    if matches:
        diff, b = matches[0]
        r = b.get('reason') or '사유없음(상담원연결전종료)'
        reason_counts[r] = reason_counts.get(r, 0) + 1
        print(f"{i+1:^3} | {cid:^22} | {ct:^19} | {b.get('time'):^19} | {diff:^5.0f}s | {b.get('dir'):^7} | {b.get('ans'):^4} | {r:^20} | {str(b.get('tag')):^20} | {b.get('talk'):^4} | {b.get('wait'):^4}")
    else:
        print(f"{i+1:^3} | {cid:^22} | {ct:^19} | {'매칭없음':^19}")

print("\n--- 18건의 CTI 사유 분포 ---")
for r, cnt in reason_counts.items():
    print(f"  • {r}: {cnt}건")
