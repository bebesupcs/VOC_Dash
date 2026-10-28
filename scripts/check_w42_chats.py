# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

c.execute("""
    SELECT u.id, u.tags, u.assigneeId, u.alfTriggered, u.handle_type,
           d.customer_issue, d.cs_action
    FROM userchat u
    LEFT JOIN userchat_description d ON u.id = d.id
    WHERE u.week_start_date='2026-10-15' AND u.mediumType != 'phone' AND u.mediumType != 'phoneNumber'
    LIMIT 20
""")
for r in c.fetchall():
    print(r)
