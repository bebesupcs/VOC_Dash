# -*- coding: utf-8 -*-
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

LOCAL_DB = r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db'
conn = sqlite3.connect(LOCAL_DB)
c = conn.cursor()

c.execute("SELECT DISTINCT tags FROM userchat WHERE tags IS NOT NULL AND tags != ''")
chat_tags = [r[0] for r in c.fetchall()]

c.execute("SELECT full_tag FROM tag_master")
master_tags = set(r[0] for r in c.fetchall())

unmapped = [t for t in chat_tags if t not in master_tags]
print(f"Total distinct chat tags: {len(chat_tags)}")
print(f"Total master tags: {len(master_tags)}")
print(f"Unmapped tags count: {len(unmapped)}")

unmapped_counts = []
for t in unmapped:
    c.execute("SELECT COUNT(*) FROM userchat WHERE tags = ?", (t,))
    cnt = c.fetchone()[0]
    unmapped_counts.append((t, cnt))

unmapped_counts.sort(key=lambda x: x[1], reverse=True)
print("\n=== Unmapped Tags in DB ===")
for t, cnt in unmapped_counts:
    print(f"- {t} ({cnt}건)")

conn.close()
