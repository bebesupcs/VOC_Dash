import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

c.execute("""
    SELECT 
        mgr.name,
        count(1)
    FROM userchat p
    LEFT JOIN manager mgr 
        ON CAST(CAST(p.assigneeId AS REAL) AS INTEGER) = CAST(CAST(mgr.id AS REAL) AS INTEGER)
    WHERE p.week = '2026-W42'
    GROUP BY mgr.name
""")
print('2026-W42 Manager with CAST fix:')
for row in c.fetchall():
    print(row)

conn.close()
