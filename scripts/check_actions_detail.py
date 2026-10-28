# -*- coding: utf-8 -*-
import sqlite3
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
cur = conn.cursor()

cur.execute("""
    SELECT u.id, u.tags, d.customer_issue, d.cs_action, u.description
    FROM userchat u
    LEFT JOIN tag_master tm ON u.tags = tm.full_tag
    LEFT JOIN userchat_description d ON u.id = d.id
    WHERE u.week_start_date = '2026-10-15'
      AND (u.journey = '제품사용' OR tm.journey = '제품사용')
      AND u.tag_c != '재통화'
""")
rows = cur.fetchall()

print(f"Total pure quality claims in W42: {len(rows)}")

recall_count = 0
exchange_count = 0
refund_count = 0

for idx, (cid, tag, issue, act, desc) in enumerate(rows):
    full_text = f"{act} {issue} {desc}"
    has_recall = bool(re.search(r'수거|회수|샘플|품질팀|확인 후|이취 샘플|개봉 1팩', full_text))
    has_refund = bool(re.search(r'환불|취소', full_text) and not re.search(r'교환|새상품', full_text))
    has_exchange = not has_refund  # 품질 불만은 환불 건 제외 100% 교환/재출고
    
    if has_recall:
        recall_count += 1
    if has_exchange:
        exchange_count += 1
    if has_refund:
        refund_count += 1
        
    print(f"[{idx+1}] {cid} | Tag={tag} | Recall={has_recall} | Exchange={has_exchange}")

print(f"\nSummary:")
print(f"  총 접수: {len(rows)}건")
print(f"  맞교환/재출고: {exchange_count}건 ({(exchange_count/len(rows))*100:.1f}%)")
print(f"  회수/품질검수: {recall_count}건 ({(recall_count/len(rows))*100:.1f}%)")
