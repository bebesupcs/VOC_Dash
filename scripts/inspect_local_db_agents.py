import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print('Tables:', tables)

for t in tables:
    tname = t[0]
    c.execute(f'SELECT count(*) FROM {tname}')
    cnt = c.fetchone()[0]
    print(f'Table {tname}: {cnt} rows')

# Check userchat schema and columns
c.execute("PRAGMA table_info(userchat)")
cols = [r[1] for r in c.fetchall()]
print('\nuserchat columns:', cols)

# Check distinct managers/agents in userchat
c.execute("SELECT createdAt, managerId, managerName FROM userchat ORDER BY createdAt DESC LIMIT 20")
rows = c.fetchall()
print('\nRecent 20 userchats:')
for r in rows:
    print(r)

conn.close()
