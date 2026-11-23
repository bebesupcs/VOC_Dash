import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

c.execute("""
    SELECT id, assigneeId, alfTriggered, is_ai_inflow, is_ai_completed
    FROM userchat
    WHERE week = '2026-W42'
""")
rows = c.fetchall()
print(f"Total rows in W42: {len(rows)}")

mgr_map = {
    '499401': 'CX_박주희',
    '538858': 'CX_오세빈',
    '573501': 'CX_한윤서'
}

chat_agent_map = {}
for r in rows:
    cid = r[0]
    raw_aid = str(r[1]).replace('.0', '').strip()
    if raw_aid in mgr_map:
        chat_agent_map[cid] = mgr_map[raw_aid]

print(f"Chats mapped to real counselors in W42: {len(chat_agent_map)}")
from collections import Counter
counts = Counter(chat_agent_map.values())
print("Counselor counts in W42:", counts)

conn.close()
