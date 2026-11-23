# -*- coding: utf-8 -*-
import sqlite3
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

db_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("--- 10월 fact_voc 채팅 상세 ---")
cur.execute("""
    SELECT count(*)
    FROM fact_voc
    WHERE date >= '2026-10-01' AND date <= '2026-10-31'
      AND channel_type = '채팅'
      AND (customer_name NOT LIKE '%홍길동%' AND (description IS NULL OR description NOT LIKE '%테스트건%'))
""")
print("10월 채널톡 channel_type = '채팅' 총건수:", cur.fetchone()[0])

cur.execute("""
    SELECT 
        is_ai_completed,
        is_ai_transferred,
        is_ai_inflow,
        count(*)
    FROM fact_voc
    WHERE date >= '2026-10-01' AND date <= '2026-10-31'
      AND channel_type = '채팅'
      AND (customer_name NOT LIKE '%홍길동%' AND (description IS NULL OR description NOT LIKE '%테스트건%'))
    GROUP BY is_ai_completed, is_ai_transferred, is_ai_inflow
""")
print("\n[AI 상태별 채팅 건수]")
for r in cur.fetchall():
    print(f"is_ai_completed={r[0]}, is_ai_transferred={r[1]}, is_ai_inflow={r[2]} -> {r[3]}건")

cur.execute("""
    SELECT 
        CASE 
            WHEN is_ai_completed = 1 THEN '챗봇_셀프처리(완결)'
            WHEN is_ai_transferred = 1 THEN '챗봇_상담사이관'
            ELSE '상담사_직접인입'
        END as chat_category,
        count(*)
    FROM fact_voc
    WHERE date >= '2026-10-01' AND date <= '2026-10-31'
      AND channel_type = '채팅'
      AND (customer_name NOT LIKE '%홍길동%' AND (description IS NULL OR description NOT LIKE '%테스트건%'))
    GROUP BY chat_category
""")
print("\n[채팅 세부 구분]")
for r in cur.fetchall():
    print(f"{r[0]}: {r[1]}건")

cur.execute("""
    SELECT 
        manager_name,
        count(*)
    FROM fact_voc
    WHERE date >= '2026-10-01' AND date <= '2026-10-31'
      AND channel_type = '채팅'
      AND (customer_name NOT LIKE '%홍길동%' AND (description IS NULL OR description NOT LIKE '%테스트건%'))
    GROUP BY manager_name
    ORDER BY count(*) DESC
""")
print("\n[담당자별 건수 (상위 10)]")
for r in cur.fetchall()[:10]:
    print(f"{r[0]}: {r[1]}건")

conn.close()
