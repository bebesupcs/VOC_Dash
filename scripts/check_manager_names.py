import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

c.execute("SELECT id, name FROM manager WHERE id IN ('499401', '538858', '573501')")
print(c.fetchall())

conn.close()
