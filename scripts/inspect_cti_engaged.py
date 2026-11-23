# -*- coding: utf-8 -*-
import sqlite3
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

db_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=== Standard meet by year, direction, and has_engaged ===")
cur.execute("""
    SELECT 
        year,
        direction,
        CASE WHEN engaged_at IS NOT NULL AND trim(engaged_at) != '' THEN 1 ELSE 0 END as has_eg,
        count(*)
    FROM standard_meet
    GROUP BY year, direction, has_eg
    ORDER BY year, direction, has_eg
""")
for r in cur.fetchall():
    print(r)

conn.close()
