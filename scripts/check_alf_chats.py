import json, sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('dashboard/data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

w42_chats = d.get('CHATS_BY_WEEK', {}).get('2026-W42', [])
alf_chats = [c for c in w42_chats if c.get('channel') == '채팅' and c.get('agent') == 'ALF (AI 상담)']
print(f'Total ALF chats in W42: {len(alf_chats)}')

local_db = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'channeltalk_voc_local.db')
conn = sqlite3.connect(local_db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

alf_ids = [c['id'] for c in alf_chats]
placeholders = ','.join('?' for _ in alf_ids)
cur.execute(f'''
    SELECT u.id, u.assigneeId, m.name as mgr_name, u.alfTriggered, u.is_ai_completed, u.is_ai_transferred, u.handle_type
    FROM userchat u
    LEFT JOIN manager m ON CAST(CAST(u.assigneeId AS REAL) AS INTEGER) = CAST(CAST(m.id AS REAL) AS INTEGER)
    WHERE u.id IN ({placeholders})
''', alf_ids)

db_rows = cur.fetchall()
print(f'Found {len(db_rows)} matching in SQLite userchat')

real_counselors = {}
for r in db_rows:
    mgr = r['mgr_name'] or 'UNASSIGNED'
    real_counselors[mgr] = real_counselors.get(mgr, 0) + 1

print('Real manager breakdown of those 212 ALF chats:')
for k, v in real_counselors.items():
    print(f'  {k}: {v}')
