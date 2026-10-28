import json, sqlite3, os, gzip, sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. Connect to DB
local_db = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'channeltalk_voc_local.db')
conn = sqlite3.connect(local_db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get manager map
cur.execute("SELECT id, name FROM manager")
mgr_map = {str(r['id']).strip(): r['name'] for r in cur.fetchall()}

# Get all userchats
cur.execute("SELECT id, assigneeId, alfTriggered, is_ai_completed, mediumType FROM userchat")
userchats = {}
for r in cur.fetchall():
    cid = str(r['id']).strip()
    raw_aid = r['assigneeId']
    mgr_name = None
    if raw_aid is not None:
        aid_str = str(raw_aid).strip()
        if aid_str.endswith('.0'):
            aid_str = aid_str[:-2]
        mgr_name = mgr_map.get(aid_str)
    userchats[cid] = {
        'mgr_name': mgr_name,
        'mediumType': r['mediumType']
    }

print(f"Loaded {len(userchats)} userchats from SQLite DB")

# 2. Read data.json
with open('dashboard/data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Track stats for 2026-W42 before and after
def get_w42_stats(chats):
    c_only = [c for c in chats if c.get('channel') == '채팅']
    agents = {}
    for c in c_only:
        a = c.get('agent') or 'None'
        agents[a] = agents.get(a, 0) + 1
    return len(c_only), agents

w42_before = data.get('CHATS_BY_WEEK', {}).get('2026-W42', [])
before_len, before_agents = get_w42_stats(w42_before)
print(f"Before fix W42 chats: {before_len}, agents: {before_agents}")

# 3. Apply fix
fixed_count = 0
for w_key, chats in data.get('CHATS_BY_WEEK', {}).items():
    for c in chats:
        cid = str(c.get('id', '')).strip()
        if cid in userchats:
            info = userchats[cid]
            real_mgr = info['mgr_name']
            if real_mgr:
                if c.get('agent') != real_mgr:
                    c['agent'] = real_mgr
                    fixed_count += 1
                if c.get('channel') == '채팅':
                    c['alfResolved'] = False
                    if c.get('alfInflow'):
                        c['alfTransferred'] = True
            else:
                # If no counselor assigned
                if c.get('channel') == '채팅':
                    if c.get('agent') not in ['ALF (AI 상담)', '미배정']:
                        c['agent'] = 'ALF (AI 상담)'
                        fixed_count += 1
                elif c.get('channel') == '전화':
                    if c.get('agent') == 'ALF (AI 상담)':
                        c['agent'] = '미배정'
                        fixed_count += 1

print(f"Total chat objects updated: {fixed_count}")

after_len, after_agents = get_w42_stats(data.get('CHATS_BY_WEEK', {}).get('2026-W42', []))
print(f"After fix W42 chats: {after_len}, agents:")
for k, v in sorted(after_agents.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}건")

# 4. Save to data.json
with open('dashboard/data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("✓ Saved to dashboard/data.json")

# 5. Save to data.js
js_content = f"window.VOC_DATA = {json.dumps(data, ensure_ascii=False)};\n"
with open('dashboard/data.js', 'w', encoding='utf-8') as f:
    f.write(js_content)
print("✓ Saved to dashboard/data.js")

# 6. Compress to data.js.gz
with open('dashboard/data.js', 'rb') as f_in:
    with gzip.open('dashboard/data.js.gz', 'wb') as f_out:
        f_out.writelines(f_in)
print("✓ Compressed to dashboard/data.js.gz")
