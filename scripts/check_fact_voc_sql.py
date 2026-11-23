import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

c.execute("SELECT sql FROM sqlite_master WHERE name='fact_voc'")
row = c.fetchone()
print(row[0])

conn.close()
