import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

c.execute("SELECT DISTINCT __source_file, count(1) FROM userchat WHERE week_start_date='2026-10-15' GROUP BY __source_file")
print('W42 source files:', c.fetchall())

c.execute("SELECT DISTINCT __source_file, count(1) FROM userchat WHERE week_start_date='2026-10-08' GROUP BY __source_file")
print('W41 source files:', c.fetchall())

conn.close()
