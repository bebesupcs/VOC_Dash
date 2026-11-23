# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('dashboard/data.json', encoding='utf-8'))
w43 = d['CTI_BY_WEEK']['2026-W43']

days = {}
for c in w43:
    dt = c['time'][:10]
    if dt not in days:
        days[dt] = {'in_ans': 0, 'in_miss': 0, 'out_ans': 0, 'out_miss': 0, 'total': 0, 'in_op_miss': 0, 'in_off_miss': 0}
    days[dt]['total'] += 1
    if c['dir'] in ('inbound', 'missed'):
        if c['ans'] == 1:
            days[dt]['in_ans'] += 1
        else:
            days[dt]['in_miss'] += 1
            if c.get('is_in_hours'):
                days[dt]['in_op_miss'] += 1
            else:
                days[dt]['in_off_miss'] += 1
    elif c['dir'] == 'outbound':
        if c['ans'] == 1:
            days[dt]['out_ans'] += 1
        else:
            days[dt]['out_miss'] += 1

print(f"{'날짜':^12} | {'전체':^6} | {'수신':^6} | {'부재중':^8} (운영/외) | {'발신':^6} | {'발신미연결':^10} | {'수신+발신':^10}")
print("-" * 80)
total_in_ans = 0
total_in_miss = 0
total_out_ans = 0
total_out_miss = 0

for dt, s in sorted(days.items()):
    total_in_ans += s['in_ans']
    total_in_miss += s['in_miss']
    total_out_ans += s['out_ans']
    total_out_miss += s['out_miss']
    print(f"{dt:^12} | {s['total']:^6} | {s['in_ans']:^6} | {s['in_miss']:^4} ({s['in_op_miss']}/{s['in_off_miss']}) | {s['out_ans']:^6} | {s['out_miss']:^10} | {s['in_ans']+s['out_ans']:^10}")

print("-" * 80)
print(f"합계: 수신={total_in_ans}, 부재중={total_in_miss}, 발신={total_out_ans}, 발신미연결={total_out_miss}")
print(f"전체 합계: {total_in_ans + total_in_miss + total_out_ans + total_out_miss}")
print(f"ChannelTalk 137과의 비교:")
print(f"  • 수신 + 발신 (통화 성공) = {total_in_ans + total_out_ans}")
print(f"  • 수신 + 발신 + 발신미연결 = {total_in_ans + total_out_ans + total_out_miss}")
print(f"  • 수신 + 부재중(운영내만) + 발신 + 발신미연결 = ?")
