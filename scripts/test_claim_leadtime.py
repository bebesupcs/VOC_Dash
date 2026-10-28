# -*- coding: utf-8 -*-
import json, sys
from datetime import datetime, timedelta
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

with open('dashboard/data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

# Flatten all CTI records
all_cti = []
for wk, ctis in d.get('CTI_BY_WEEK', {}).items():
    for c in ctis:
        # copy with week
        item = dict(c)
        item['week'] = wk
        all_cti.append(item)

print(f"Total CTI records loaded: {len(all_cti)}")

# Filter records with time
valid_cti = [c for c in all_cti if c.get('time')]

# Sort by customer identifier and consultation time ascending
# Customer identifier: cust + '_' + phone (or phone if available, or cust)
def get_cust_key(c):
    p = c.get('phone') or ''
    nm = c.get('cust') or ''
    if p and p != 'None' and '***' in p:
        return f"{nm}_{p}"
    elif p and p != 'None':
        return p
    return nm or 'Unknown'

valid_cti.sort(key=lambda x: (get_cust_key(x), x['time']))

# Let's inspect tag patterns
# '클레임' tag vs '재통화' tag
def is_claim_tag(t):
    return '클레임' in t or '불만' in t or '하자' in t or '파손' in t

def is_recall_tag(t):
    return '재통화' in t

# Grouping by customer
cust_records = defaultdict(list)
for c in valid_cti:
    cust_key = get_cust_key(c)
    cust_records[cust_key].append(c)

claims = []
unmatched_recalls = 0

for cust_key, recs in cust_records.items():
    # Sort by time
    recs.sort(key=lambda x: x['time'])
    
    current_claim = None
    
    for r in recs:
        t = r.get('tag') or ''
        r_time = datetime.strptime(r['time'][:19], '%Y-%m-%d %H:%M:%S')
        talk_sec = r.get('talk', 0) or 0
        
        if is_claim_tag(t):
            # If there was a previous claim, it's finished or this is a new claim
            current_claim = {
                'claim_id': f"CLM_{r['id']}",
                'cust': r.get('cust', ''),
                'phone': r.get('phone', ''),
                'cust_key': cust_key,
                'first_tag': t,
                'first_time': r['time'],
                'first_dt': r_time,
                'last_time': r['time'],
                'last_dt': r_time,
                'week': r.get('week', ''),
                'calls': [r],
                'call_count': 1,
                'total_talk_sec': talk_sec,
                'issue': r.get('issue', ''),
                'act': r.get('act', ''),
                'agent': r.get('agent', '')
            }
            claims.append(current_claim)
        elif is_recall_tag(t):
            if current_claim:
                diff_days = (r_time - current_claim['first_dt']).total_seconds() / 86400.0
                if 0 <= diff_days <= 14.0:
                    # Belong to this claim!
                    current_claim['calls'].append(r)
                    current_claim['call_count'] += 1
                    current_claim['total_talk_sec'] += talk_sec
                    current_claim['last_time'] = r['time']
                    current_claim['last_dt'] = r_time
                else:
                    # > 14 days, exclude or separate
                    unmatched_recalls += 1
            else:
                unmatched_recalls += 1

print(f"Total grouped claim cases: {len(claims)}")
print(f"Unmatched/Excluded re-calls (>14 days or without claim): {unmatched_recalls}")

# Compute summary metrics on claims
lead_times_hours = []
call_counts = []
durations_min = []

for c in claims:
    dur_min = c['total_talk_sec'] / 60.0
    c['total_call_duration_min'] = round(dur_min, 1)
    
    lead_hrs = (c['last_dt'] - c['first_dt']).total_seconds() / 3600.0
    lead_days = lead_hrs / 24.0
    c['lead_time_hours'] = round(lead_hrs, 2)
    c['lead_time_days'] = round(lead_days, 2)
    
    lead_times_hours.append(lead_hrs)
    call_counts.append(c['call_count'])
    durations_min.append(dur_min)

if claims:
    avg_calls = sum(call_counts) / len(call_counts)
    avg_dur = sum(durations_min) / len(durations_min)
    avg_lead_hrs = sum(lead_times_hours) / len(lead_times_hours)
    avg_lead_days = avg_lead_hrs / 24.0
    
    print(f"\n=== 전체 누적 집계 지표 ===")
    print(f"1) 평균 통화 횟수: {avg_calls:.2f}회 (최대 {max(call_counts)}회)")
    print(f"2) 평균 총 통화 시간: {avg_dur:.1f}분 ({avg_dur*60:.0f}초)")
    print(f"3) 평균 리드타임: {avg_lead_hrs:.1f}시간 ({avg_lead_days:.1f}일)")
    
    # Call count distribution
    cnt_1 = sum(1 for x in call_counts if x == 1)
    cnt_2_3 = sum(1 for x in call_counts if 2 <= x <= 3)
    cnt_4_plus = sum(1 for x in call_counts if x >= 4)
    print(f"\n통화 횟수별 분포:")
    print(f"  - 1회 해결: {cnt_1}건 ({cnt_1/len(claims)*100:.1f}%)")
    print(f"  - 2~3회 재통화: {cnt_2_3}건 ({cnt_2_3/len(claims)*100:.1f}%)")
    print(f"  - 4회 이상 다회 통화: {cnt_4_plus}건 ({cnt_4_plus/len(claims)*100:.1f}%)")
    
    # Lead time distribution
    lt_same_day = sum(1 for x in lead_times_hours if x <= 24.0)
    lt_1_3 = sum(1 for x in lead_times_hours if 24.0 < x <= 72.0)
    lt_4_7 = sum(1 for x in lead_times_hours if 72.0 < x <= 168.0)
    lt_gt_7 = sum(1 for x in lead_times_hours if x > 168.0)
    print(f"\n해결 기간(리드타임) 분포:")
    print(f"  - 당일 해결(24시간 이내): {lt_same_day}건 ({lt_same_day/len(claims)*100:.1f}%)")
    print(f"  - 1~3일(72시간 이내): {lt_1_3}건 ({lt_1_3/len(claims)*100:.1f}%)")
    print(f"  - 4~7일: {lt_4_7}건 ({lt_4_7/len(claims)*100:.1f}%)")
    print(f"  - 7일 초과 (최대 14일): {lt_gt_7}건 ({lt_gt_7/len(claims)*100:.1f}%)")
