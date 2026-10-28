# -*- coding: utf-8 -*-
import sqlite3, json, sys, os
sys.stdout.reconfigure(encoding='utf-8')

LOCAL_DB = r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db'
cid = '6a570058b7a9e5ffb5ab'

conn = sqlite3.connect(LOCAL_DB)
c = conn.cursor()

# Check in userchat
c.execute('SELECT * FROM userchat WHERE id = ?', (cid,))
r = c.fetchone()
if r:
    cols = [d[0] for d in c.description]
    d = dict(zip(cols, r))
    print(f"=== Found in userchat: {cid} ===")
    for k in ['id', 'managedAt', 'report_date', 'date', 'name', 'tags', 'journey', 'week', 'month', '__schema_year', '__source_file']:
        print(f"  {k}: {d.get(k)}")
else:
    print(f"{cid} NOT in userchat!")

# Check in userchat_description
c.execute('SELECT * FROM userchat_description WHERE id = ?', (cid,))
r_desc = c.fetchone()
if r_desc:
    cols = [d[0] for d in c.description]
    print('Found in userchat_description:', dict(zip(cols, r_desc)))
else:
    print('NOT in userchat_description')

# Check in data.json
with open('dashboard/data.json', 'r', encoding='utf-8') as f:
    djson = json.load(f)

found_json = False
for wk, clist in djson.get('CHATS_BY_WEEK', {}).items():
    for chat in clist:
        if chat.get('id') == cid:
            print(f"Found in data.json under {wk}: journey={chat.get('journey')}, date={chat.get('date')}, time={chat.get('time')}")
            found_json = True
            break
    if found_json: break

if not found_json:
    print(f"{cid} NOT in data.json CHATS_BY_WEEK")

# Check in QUALITY_RAW
q_raw = djson.get('QUALITY_RAW', [])
found_q = [q for q in q_raw if q.get('id') == cid]
if found_q:
    print("Found in QUALITY_RAW:", found_q[0])
else:
    print(f"{cid} NOT in QUALITY_RAW")

conn.close()
