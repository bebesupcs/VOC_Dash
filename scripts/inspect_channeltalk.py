# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('dashboard/data.json', encoding='utf-8'))
w43 = d['CTI_BY_WEEK']['2026-W43']

target_reasons = ['상담원 수락 시간 초과', '대기열 제한 시간 초과', '대기열 진입 실패', '상담원 통화중', '수락 대기 중 고객 종료']

days = {}
for c in w43:
    dt = c['time'][:10]
    if dt not in days:
        days[dt] = {'in_ans': 0, 'in_target_miss': 0, 'in_nontarget_miss': 0, 'out_ans': 0, 'out_miss': 0}
    isOp = c.get('is_in_hours')
    reason = (c.get('reason') or '').strip()
    isTarget = (reason in target_reasons) or (reason == '대기열에서 고객 종료' and isOp)
    
    if c['dir'] in ('inbound', 'missed'):
        if c['ans'] == 1:
            days[dt]['in_ans'] += 1
        else:
            if isTarget:
                days[dt]['in_target_miss'] += 1
            else:
                days[dt]['in_nontarget_miss'] += 1
    elif c['dir'] == 'outbound':
        if c['ans'] == 1:
            days[dt]['out_ans'] += 1
        else:
            days[dt]['out_miss'] += 1

print("Day by day with ChannelTalk formula:")
t_in_ans = 0
t_target_miss = 0
t_out_ans = 0
t_out_miss = 0
for dt, s in sorted(days.items()):
    t_in_ans += s['in_ans']
    t_target_miss += s['in_target_miss']
    t_out_ans += s['out_ans']
    t_out_miss += s['out_miss']
    day_ct_sum = s['in_ans'] + s['in_target_miss'] + s['out_ans'] + s['out_miss']
    print(f"{dt}: 수신={s['in_ans']}, 부재중={s['in_target_miss']}, 발신={s['out_ans']}, 발신미연결={s['out_miss']} -> 합={day_ct_sum}")

print("--- WEEK TOTAL ---")
print(f"수신: {t_in_ans}")
print(f"부재중: {t_target_miss}")
print(f"발신: {t_out_ans}")
print(f"발신 미연결: {t_out_miss}")
total_ct = t_in_ans + t_target_miss + t_out_ans + t_out_miss
print(f"ChannelTalk 총 전화 수 (수신 + 부재중 + 발신 + 발신미연결) = {total_ct}")
