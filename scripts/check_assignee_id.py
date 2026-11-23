import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

c.execute("SELECT DISTINCT assigneeId, count(1) FROM userchat WHERE week = '2026-W42' GROUP BY assigneeId")
print('assigneeId in 2026-W42:', c.fetchall())

c.execute("SELECT DISTINCT assigneeId, count(1) FROM userchat WHERE week = '2026-W41' GROUP BY assigneeId")
print('assigneeId in 2026-W41:', c.fetchall())

conn.close()
