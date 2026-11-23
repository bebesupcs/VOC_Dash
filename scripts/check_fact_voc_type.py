import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

c.execute("SELECT type, sql FROM sqlite_master WHERE name='fact_voc'")
row = c.fetchone()
print('fact_voc type:', row[0] if row else 'None')
if row and row[1]:
    print('SQL Definition:', row[1][:1000])

conn.close()
