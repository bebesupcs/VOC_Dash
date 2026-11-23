# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

ids = [
    '6ad960ddcc38aa812c02',
    '6ad96eb99f8f5c8602d8',
    '6adab675bb17cb5c2f5e',
    '6adab6c0c5801f58adcf',
    '6adac3e96866aa0d3f46',
    '6adac63bad715eebbd90',
    '6adae4ffcfd53fa4f4c0',
    '6adafd98409070fe85e7',
    '6adea98bb3ef87387978',
    '6adeab620319cce2a025',
    '6adeb733334ff561d354',
    '6adedafe2c35d72ad841',
    '6adf046d1accfdb6e3db',
    '6ae01189004f95939596',
    '6ae019106d552ede2c55',
    '6ae037a55192063d56a4',
    '6ae057d6b9f1a4bcd63b',
    '6ae194fb65d6b3a828b2'
]

d = json.load(open('dashboard/data.json', encoding='utf-8'))
chats_w43 = d['CHATS_BY_WEEK'].get('2026-W43', [])
cti_w43 = d['CTI_BY_WEEK'].get('2026-W43', [])

chats_by_id = {c.get('id'): c for c in chats_w43 if c.get('id')}
cti_by_id = {c.get('id'): c for c in cti_w43 if c.get('id')}

print(f"Total given IDs: {len(ids)}")
print(f"Found in CHATS_BY_WEEK: {sum(1 for i in ids if i in chats_by_id)}")
print(f"Found in CTI_BY_WEEK: {sum(1 for i in ids if i in cti_by_id)}")

print("\n--- Detailed inspection of the 18 records in CHATS_BY_WEEK ---")
for i, cid in enumerate(ids):
    c = chats_by_id.get(cid)
    if not c:
        print(f"[{i+1}] {cid} NOT FOUND in CHATS_BY_WEEK")
        continue
    
    print(f"[{i+1}] ID: {cid}")
    print(f"    시간: {c.get('time')} | 채널: {c.get('channel')} | 방향: {c.get('direction')} | 상태: {c.get('state')} | 담당자: {c.get('agent')}")
    print(f"    태그: {c.get('tags')} | 문의: {c.get('inquiry_category')} > {c.get('inquiry_detail')}")
    print(f"    고객: {c.get('customer_name')} | 전화: {c.get('customer_phone')}")
    print(f"    ALF 유입: {c.get('alfInflow')} | ALF 해결: {c.get('alfResolved')}")
    print(f"    내용 요약: {repr(c.get('content'))[:100]}")
    # Also check if this customer or phone called CTI
    phone = c.get('customer_phone')
    if phone:
        matched_cti = [call for call in cti_w43 if call.get('phone') == phone]
        if matched_cti:
            print(f"    -> CTI 매칭 건수: {len(matched_cti)}건 (시간: {[m.get('time') for m in matched_cti]})")
        else:
            print(f"    -> CTI 매칭 건수: 0건")
    print("-" * 70)
