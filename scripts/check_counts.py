# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open('dashboard/data.json', encoding='utf-8'))

reports = {
    '2026-W40': {'report_call': 148, 'report_chat': 225, 'report_board': 192, 'report_total': 565},
    '2026-W41': {'report_call': 174, 'report_chat': 226, 'report_board': 240, 'report_total': 640},
    '2026-W42': {'report_call': 192, 'report_chat': 221, 'report_board': 190, 'report_total': 603},
    '2026-W43': {'report_call': 133, 'report_chat': 149, 'report_board': 159, 'report_total': 441},
    '2026-W44': {'report_call': 137, 'report_chat': 176, 'report_board': 225, 'report_total': 538},
}

print(f"{'주차':^10} | {'공식보고서(콜)':^14} | {'대시보드 실통화':^14} | {'인바운드 수신':^12} | {'아웃바운드 발신':^16} | {'인바운드 총인입':^14} | {'전체 원장(콜)':^12}")
print("-" * 95)
for w in ['2026-W40', '2026-W41', '2026-W42', '2026-W43', '2026-W44']:
    calls = d.get('CTI_BY_WEEK', {}).get(w, [])
    raw_s = d.get('RAW_SUMMARY', {}).get(w, {})
    rep = reports.get(w, {})
    
    in_calls = [c for c in calls if c.get('dir') in ('inbound', 'missed')]
    in_ans = [c for c in in_calls if c.get('ans') == 1]
    out_calls = [c for c in calls if c.get('dir') == 'outbound']
    out_ans = [c for c in out_calls if c.get('ans') == 1 and '부재' not in (c.get('tag') or '') and '부재' not in (c.get('reason') or '')]
    out_talk = [c for c in out_calls if c.get('talk', 0) > 0]
    
    rep_c = rep.get('report_call', '-')
    real_calls = raw_s.get('raw_call', len(in_ans) + len(out_ans))
    
    print(f"{w:^10} | {str(rep_c)+'건':^14} | {str(real_calls)+'건':^14} | {str(len(in_ans))+'건':^12} | {str(len(out_ans))+'건 (대화: '+str(len(out_talk))+')':^16} | {str(len(in_calls))+'건':^14} | {str(len(calls))+'건':^12}")
