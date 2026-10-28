# -*- coding: utf-8 -*-
import sqlite3, json, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
cur = conn.cursor()

cur.execute("SELECT from_number, to_number, user_chat_id, duration_sec, started_at FROM standard_meet LIMIT 10")
for r in cur.fetchall():
    print(r)

# Check userchat matching
cur.execute("SELECT u.name, u.managedAt, u.tags, u.journey, m.from_number, m.duration_sec FROM userchat u JOIN standard_meet m ON u.id = m.user_chat_id LIMIT 10")
print("\nSample join userchat + meet:")
for r in cur.fetchall():
    print(r)
