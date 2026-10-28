# -*- coding: utf-8 -*-
import sqlite3, json, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
cur = conn.cursor()

# Search tags containing '클레임' or '재통화' in userchat
cur.execute("SELECT tags, COUNT(*) FROM userchat WHERE tags LIKE '%클레임%' OR tags LIKE '%재통화%' GROUP BY tags ORDER BY COUNT(*) DESC LIMIT 30")
rows = cur.fetchall()
print("=== userchat tags with '클레임' or '재통화' ===")
for r in rows:
    print(f"  {r[1]:4d}건: {r[0]}")

# Also check tag_master
cur.execute("SELECT full_tag, journey, tag_a, tag_b, tag_c FROM tag_master WHERE full_tag LIKE '%클레임%' OR full_tag LIKE '%재통화%'")
print("\n=== tag_master matching ===")
for r in cur.fetchall():
    print(" ", r)

# Also check CTI records in data.json
with open('dashboard/data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

cti_tags = {}
for wk, ctis in d.get('CTI_BY_WEEK', {}).items():
    for c in ctis:
        t = c.get('tag') or ''
        if '클레임' in t or '재통화' in t or '재상담' in t:
            cti_tags[t] = cti_tags.get(t, 0) + 1

print("\n=== CTI tags with 클레임/재통화/재상담 in data.json ===")
for t, cnt in sorted(cti_tags.items(), key=lambda x: -x[1]):
    print(f"  {cnt:4d}건: {t}")
