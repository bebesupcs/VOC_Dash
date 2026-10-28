# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

# 8월과 10월의 assignee_id 및 기타 필드 비교
print("=== 2026-08 (8월) 수기 엑셀 기반 데이터 ===")
c.execute("""
    SELECT is_ai_completed, is_ai_handled, is_ai_transferred, COUNT(*)
    FROM fact_voc
    WHERE month='2026-08' AND channel_type='채팅'
    GROUP BY is_ai_completed, is_ai_handled, is_ai_transferred
""")
for r in c.fetchall():
    print(r)

print("\n=== 8월 완료 건들의 특징 ===")
c.execute("""
    SELECT cs_action, COUNT(*)
    FROM fact_voc
    WHERE month='2026-08' AND channel_type='채팅' AND is_ai_completed=1
    GROUP BY cs_action
    LIMIT 10
""")
for r in c.fetchall():
    print(r)
