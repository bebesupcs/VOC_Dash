# -*- coding: utf-8 -*-
import sys, json

with open('parsed_user_rows.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

v_count = d['v_count']
ex_count = d['ex_count']
total = v_count + ex_count

output_lines = []
output_lines.append(f"=== 사용자 제공 9월 보상내역서 검증 ===")
output_lines.append(f"총 {total}건: V(포함)={v_count}건, 제외={ex_count}건\n")

output_lines.append("="*80)
output_lines.append(f"■ [제외] 처리된 17건 상세 내역 및 제외 사유 분석")
output_lines.append("="*80)

for idx, r in enumerate(d['ex_rows']):
    cat_large, cat_mid, cat_small, cust, mgr, date, prod, mfg_date, content, report_m, status = r[:11]
    content_clean = content.replace('\n', ' ').strip()
    output_lines.append(f"\n[{idx+1:2d}] {date} | 고객: {cust} (담당: {mgr})")
    output_lines.append(f"     분류: {cat_large} > {cat_mid} > {cat_small}")
    output_lines.append(f"     제품: {prod}")
    output_lines.append(f"     내용: {content_clean}")

output_lines.append("\n" + "="*80)
output_lines.append(f"■ [V 포함] 처리된 {v_count}건 패턴 요약")
output_lines.append("="*80)

# Check sample V rows
for idx, r in enumerate(d['v_rows'][:10]):
    cat_large, cat_mid, cat_small, cust, mgr, date, prod, mfg_date, content, report_m, status = r[:11]
    content_clean = content.replace('\n', ' ').strip()
    output_lines.append(f"[{idx+1:2d}] {date} | 고객: {cust} ({mgr}) | {cat_mid}>{cat_small} | {content_clean[:80]}")

with open('user_table_analysis.txt', 'w', encoding='utf-8') as out:
    out.write("\n".join(output_lines))

print("Saved to user_table_analysis.txt")
