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

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("All tables in DB:", tables)

print("\n--- Exploring standard_meet columns and filters for 670, 709, 651, 638 ---")
cur.execute("PRAGMA table_info(standard_meet)")
print("standard_meet cols:", [r[1] for r in cur.fetchall()])

for m, target in [('2026-07', 638), ('2026-08', 651), ('2026-09', 709), ('2026-10', 670)]:
    print(f"\n[{m} (Target: {target})]")
    cur.execute(f"SELECT direction, count(*) FROM standard_meet WHERE substr(started_at, 1, 7) = '{m}' GROUP BY direction")
    print("  Direction:", cur.fetchall())
    
    cur.execute(f"SELECT is_inbound, count(*) FROM standard_meet WHERE substr(started_at, 1, 7) = '{m}' GROUP BY is_inbound")
    print("  is_inbound:", cur.fetchall())

    cur.execute(f"SELECT is_answered, count(*) FROM standard_meet WHERE substr(started_at, 1, 7) = '{m}' GROUP BY is_answered")
    print("  is_answered:", cur.fetchall())

    cur.execute(f"SELECT is_missed, count(*) FROM standard_meet WHERE substr(started_at, 1, 7) = '{m}' GROUP BY is_missed")
    print("  is_missed:", cur.fetchall())

    cur.execute(f"SELECT is_response_target, count(*) FROM standard_meet WHERE substr(started_at, 1, 7) = '{m}' GROUP BY is_response_target")
    print("  is_response_target:", cur.fetchall())

    # Try duration_sec > 0
    cur.execute(f"SELECT count(*) FROM standard_meet WHERE substr(started_at, 1, 7) = '{m}' AND duration_sec > 0")
    print("  duration > 0:", cur.fetchone()[0])

    # Try fact_voc 콜 channel
    cur.execute(f"SELECT count(*) FROM fact_voc WHERE substr(date, 1, 7) = '{m}' AND (channel_type = '콜' OR channel_type = '전화')")
    print("  fact_voc 콜/전화:", cur.fetchone()[0])

conn.close()
