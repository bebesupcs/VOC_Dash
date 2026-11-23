import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

c.execute("SELECT DISTINCT __source_path, __source_file FROM userchat WHERE __source_file LIKE '%user_chat_list%'")
print(c.fetchall())

conn.close()
