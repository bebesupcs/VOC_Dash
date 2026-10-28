# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()
c.execute("""
    SELECT channel_type, medium_type, COUNT(*),
           SUM(CASE WHEN is_ai_inflow=1 OR alf_triggered='true' THEN 1 ELSE 0 END),
           SUM(CASE WHEN full_tag LIKE '콜%' THEN 1 ELSE 0 END)
    FROM fact_voc
    WHERE year=2026
    GROUP BY channel_type, medium_type
""")
for r in c.fetchall():
    print(r)

print("\n--- 2026-W42 (10월 3주) 데이터 세부 확인 ---")
c.execute("""
    SELECT is_ai_inflow, alf_triggered, is_ai_completed, is_ai_handled, is_ai_transferred, COUNT(*)
    FROM fact_voc
    WHERE week_start_date='2026-10-15'
    GROUP BY is_ai_inflow, alf_triggered, is_ai_completed, is_ai_handled, is_ai_transferred
""")
for r in c.fetchall():
    print(r)
