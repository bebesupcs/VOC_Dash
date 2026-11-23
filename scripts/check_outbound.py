# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('dashboard/data.json', encoding='utf-8'))
for w in ['2026-W41', '2026-W42', '2026-W43', '2026-W44']:
    calls = d['CTI_BY_WEEK'].get(w, [])
    out_calls = [c for c in calls if c.get('dir') == 'outbound']
    
    ans1 = [c for c in out_calls if c.get('ans') == 1]
    talk_gt0 = [c for c in out_calls if (c.get('talk') or 0) > 0]
    talk_gte5 = [c for c in out_calls if (c.get('talk') or 0) >= 5]
    talk_gte10 = [c for c in out_calls if (c.get('talk') or 0) >= 10]
    talk_gte15 = [c for c in out_calls if (c.get('talk') or 0) >= 15]
    
    # current logic: ans==1 and "부재" not in tag and "부재" not in reason
    curr_counted = [c for c in out_calls if c.get('ans') == 1 and '부재' not in (c.get('tag') or '') and '부재' not in (c.get('reason') or '')]
    
    print(f"[{w}] Total Outbound: {len(out_calls)}")
    print(f"  • ans == 1: {len(ans1)}")
    print(f"  • talk > 0s: {len(talk_gt0)}")
    print(f"  • talk >= 5s: {len(talk_gte5)}")
    print(f"  • talk >= 10s: {len(talk_gte10)}")
    print(f"  • talk >= 15s: {len(talk_gte15)}")
    print(f"  • Current Dashboard Count (ans=1 & no 부재 tag/reason): {len(curr_counted)}")

print("\n--- Detailed look at W43 Outbound calls with ans==1 ---")
w43_out = [c for c in d['CTI_BY_WEEK']['2026-W43'] if c.get('dir') == 'outbound']
for c in w43_out:
    tag = c.get('tag') or ''
    reason = c.get('reason') or ''
    talk = c.get('talk') or 0
    ans = c.get('ans')
    if ans == 1 and ('부재' in tag or '부재' in reason or talk == 0):
        print(f"Excluded: talk={talk}s, ans={ans}, reason='{reason}', tag='{tag}'")
    elif ans == 0 and talk > 0:
        print(f"ans=0 but talk>0: talk={talk}s, ans={ans}, reason='{reason}', tag='{tag}'")
