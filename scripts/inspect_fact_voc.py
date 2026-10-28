# -*- coding: utf-8 -*-
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
cur = conn.cursor()

print("=== 8월 is_ai_completed = 1인 채팅 샘플 10건 ===")
cur.execute("""
SELECT id, managedAt, channel_type, medium_type, assignee_id, manager_name, full_tag, customer_issue, cs_action, __source_file
FROM fact_voc
WHERE managedAt LIKE '2026-08%' AND is_ai_completed = 1
LIMIT 10
""")
for r in cur.fetchall():
    print(r)

conn.close()
