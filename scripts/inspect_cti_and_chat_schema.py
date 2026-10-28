# -*- coding: utf-8 -*-
import sqlite3, json, sys, os
sys.stdout.reconfigure(encoding='utf-8')

db_path = r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db'
if not os.path.exists(db_path):
    print("DB does not exist at", db_path)
    sys.exit()

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print('Tables:', tables)

for tbl in tables:
    cur.execute(f"PRAGMA table_info({tbl})")
    cols = [c[1] for c in cur.fetchall()]
    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
    cnt = cur.fetchone()[0]
    print(f"\n[{tbl}] ({cnt} rows):")
    print("  Columns:", cols)

# Check sample data in CHATS_BY_WEEK and CTI_BY_WEEK
with open('dashboard/data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

for wk in reversed(list(d.get('CHATS_BY_WEEK', {}).keys())):
    chats = d['CHATS_BY_WEEK'][wk]
    if chats:
        print(f"\nCHATS_BY_WEEK sample ({wk}, {len(chats)} chats):")
        print("Chat keys:", list(chats[0].keys()))
        print("Sample chat:", {k: chats[0][k] for k in ['id', 'channel', 'time', 'date', 'personName', 'tags', 'tagCount', 'duration'] if k in chats[0]})
        break

for wk in reversed(list(d.get('CTI_BY_WEEK', {}).keys())):
    ctis = d['CTI_BY_WEEK'][wk]
    if ctis:
        print(f"\nCTI_BY_WEEK sample ({wk}, {len(ctis)} ctis):")
        print("Cti keys:", list(ctis[0].keys()))
        print("Sample cti:", ctis[0])
        break
