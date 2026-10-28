# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

for w in ['2026-10-01', '2026-10-08', '2026-10-15']:
    print(f"=== {w} ===")
    c.execute("""
        SELECT COUNT(*),
               SUM(CASE WHEN channel_type='채팅' THEN 1 ELSE 0 END) as chat_cnt,
               SUM(CASE WHEN channel_type='채팅' AND is_ai_inflow=1 THEN 1 ELSE 0 END) as ai_inflow,
               SUM(CASE WHEN channel_type='채팅' AND (is_ai_completed=1 OR is_ai_handled=1) THEN 1 ELSE 0 END) as ai_comp,
               SUM(CASE WHEN channel_type='채팅' AND cs_action LIKE '%ALF%' THEN 1 ELSE 0 END) as alf_action,
               SUM(CASE WHEN channel_type='콜' THEN 1 ELSE 0 END) as call_cnt
        FROM fact_voc
        WHERE week_start_date=?
    """, (w,))
    r = c.fetchone()
    print(f"전체: {r[0]}, 채팅: {r[1]}, AI인입: {r[2]}, AI완결: {r[3]}, cs_action에 ALF포함: {r[4]}, 전화: {r[5]}")
