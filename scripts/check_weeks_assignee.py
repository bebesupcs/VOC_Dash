import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

c.execute("""
    SELECT week, assigneeId, count(1)
    FROM userchat
    WHERE week IN ('2026-W40', '2026-W41', '2026-W42')
    GROUP BY week, assigneeId
""")
for r in c.fetchall():
    print(r)

conn.close()
