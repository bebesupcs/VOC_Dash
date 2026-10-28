# -*- coding: utf-8 -*-
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("""
    SELECT u.tags, COUNT(*) as cnt
    FROM userchat u
    LEFT JOIN tag_master tm ON u.tags = tm.full_tag
    WHERE tm.full_tag IS NULL AND u.tags IS NOT NULL AND u.tags != ''
    GROUP BY u.tags
    ORDER BY cnt DESC
""")
rows = c.fetchall()

print(f"Total unmapped tags in DB: {len(rows)}")
for tag, cnt in rows:
    print(f"  - {tag} ({cnt}건)")

conn.close()
