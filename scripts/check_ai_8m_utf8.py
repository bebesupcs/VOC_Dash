# -*- coding: utf-8 -*-
import sqlite3
import sys

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

print("=== 8월 완료 건들의 cs_action ===")
c.execute("""
    SELECT cs_action, COUNT(*)
    FROM fact_voc
    WHERE month='2026-08' AND channel_type='채팅' AND is_ai_completed=1
    GROUP BY cs_action
    ORDER BY COUNT(*) DESC
    LIMIT 10
""")
for r in c.fetchall():
    print(repr(r[0]), r[1])

print("\n=== 10월 W42 데이터의 cs_action / description 현황 ===")
c.execute("""
    SELECT cs_action, COUNT(*)
    FROM fact_voc
    WHERE week_start_date='2026-10-15' AND channel_type='채팅'
    GROUP BY cs_action
    ORDER BY COUNT(*) DESC
    LIMIT 15
""")
for r in c.fetchall():
    print(repr(r[0]), r[1])
