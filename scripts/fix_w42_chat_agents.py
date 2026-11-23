import json, sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8')

local_db = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'channeltalk_voc_local.db')
conn = sqlite3.connect(local_db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get manager map
cur.execute("SELECT id, name FROM manager")
mgr_map = {str(r['id']).strip(): r['name'] for r in cur.fetchall()}
print('Managers in DB:', mgr_map)

# Get all userchats for 2026-W42 and all weeks
cur.execute("""
    SELECT 
        u.id,
        u.assigneeId,
        u.alfTriggered,
        u.is_ai_completed,
        u.is_ai_inflow,
        u.is_ai_handled,
        u.handle_type
    FROM userchat u
    WHERE u.week = '2026-W42'
""")
w42_userchats = cur.fetchall()
print(f'Total w42 userchats in DB: {len(w42_userchats)}')

# Map each id to manager
chat_mgr_map = {}
for u in w42_userchats:
    cid = str(u['id']).strip()
    raw_aid = u['assigneeId']
    if raw_aid is not None:
        aid_str = str(raw_aid).strip()
        if aid_str.endswith('.0'):
            aid_str = aid_str[:-2]
        if aid_str in mgr_map:
            chat_mgr_map[cid] = mgr_map[aid_str]
        else:
            # Maybe pure AI or unassigned
            pass

print(f'Counselor mapped chats: {len(chat_mgr_map)}')
counts = {}
for m in chat_mgr_map.values():
    counts[m] = counts.get(m, 0) + 1
print('Breakdown of counselor chats in DB:', counts)
