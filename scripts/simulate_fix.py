import json, sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. Load DB manager mapping
local_db = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'channeltalk_voc_local.db')
conn = sqlite3.connect(local_db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT id, name FROM manager")
mgr_map = {str(r['id']).strip(): r['name'] for r in cur.fetchall()}

cur.execute("SELECT id, assigneeId, alfTriggered, is_ai_completed FROM userchat WHERE week = '2026-W42'")
db_userchats = {}
for r in cur.fetchall():
    cid = str(r['id']).strip()
    raw_aid = r['assigneeId']
    mgr_name = None
    if raw_aid is not None:
        aid_str = str(raw_aid).strip()
        if aid_str.endswith('.0'):
            aid_str = aid_str[:-2]
        mgr_name = mgr_map.get(aid_str)
    db_userchats[cid] = {
        'mgr_name': mgr_name,
        'alfTriggered': r['alfTriggered'],
        'is_ai_completed': r['is_ai_completed']
    }

# 2. Check data.json
with open('dashboard/data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

w42_chats = d.get('CHATS_BY_WEEK', {}).get('2026-W42', [])
print(f'Total w42 chats in data.json: {len(w42_chats)}')

counselor_chats = []
alf_chats = []

for c in w42_chats:
    cid = str(c.get('id')).strip()
    if cid in db_userchats:
        info = db_userchats[cid]
        real_mgr = info['mgr_name']
        if real_mgr:
            c['agent'] = real_mgr
            # If handled by counselor, alfResolved should be false so counselor is credited
            c['alfResolved'] = False
        else:
            c['agent'] = 'ALF (AI 상담)'
            c['alfInflow'] = True

# Now test what renderAgentPerformanceMatrix and renderChatDetail see!
chat_only = [c for c in w42_chats if c.get('channel') == '채팅']
print(f'\nTotal chat_only: {len(chat_only)}')
counselor_only = [c for c in chat_only if c.get('agent') and c.get('agent') != 'ALF (AI 상담)' and c.get('agent') != '미배정']
print(f'Counselor direct response: {len(counselor_only)}건 ({len(counselor_only)/len(chat_only)*100:.1f}%)')

agent_counts = {}
for c in chat_only:
    ag = c.get('agent') or '미배정'
    agent_counts[ag] = agent_counts.get(ag, 0) + 1

print('\nChat agent breakdown (chatAgentChart):')
for k, v in sorted(agent_counts.items(), key=lambda x: -x[1]):
    print(f'  {k}: {v}건')

# Phone CTI breakdown from CTI stats
cti_stats = d.get('CTI_BY_WEEK', {}).get('2026-W42', {}).get('agentStats', [])
print('\nCTI agent stats in data.json:')
for st in cti_stats:
    print(f"  {st.get('agent')}: In={st.get('inAns')} Out={st.get('outAns')} Total={st.get('totalAns')}")

print('\nCombined Agent Performance Matrix:')
combined = {}
for st in cti_stats:
    ag = st.get('agent') or '미배정'
    combined.setdefault(ag, {'call': 0, 'chat': 0})
    combined[ag]['call'] += st.get('totalAns', 0)

for c in counselor_only:
    ag = c.get('agent') or '미배정'
    combined.setdefault(ag, {'call': 0, 'chat': 0})
    combined[ag]['chat'] += 1

for k, v in sorted(combined.items(), key=lambda x: -(x[1]['call'] + x[1]['chat'])):
    print(f"  {k}: 전화 {v['call']}건 + 채팅 {v['chat']}건 = 총 {v['call'] + v['chat']}건")
