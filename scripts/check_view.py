import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8')

local_db = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'channeltalk_voc_local.db')
conn = sqlite3.connect(local_db)
cur = conn.cursor()
cur.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name='fact_voc'")
row = cur.fetchone()
if row:
    print(row[0])
else:
    print("No fact_voc view found")
