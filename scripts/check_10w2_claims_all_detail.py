# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')

print("=== All rows for 10월 2주차 (managedAt 2026-10-08 17:00 ~ 2026-10-15 17:00) where journey == '사후관리/클레임' ===")
df = pd.read_sql("""
    SELECT id, managedAt, mediumName, direction, journey, tag_a, tag_b, tag_c, tags, __source_file
    FROM userchat
    WHERE managedAt >= '2026-10-08 17:00:00' AND managedAt < '2026-10-15 17:00:00'
      AND journey = '사후관리/클레임'
    ORDER BY managedAt
""", conn)
print(f"Total: {len(df)}")
for idx, r in df.iterrows():
    print(f"[{idx+1}] ID={r['id']} | Date={r['managedAt']} | Medium={r['mediumName']} | Tag={r['tags']} | Source={r['__source_file']}")

print("\n=== And what if managedAt is between 2026-10-08 00:00 and 2026-10-15 17:00? ===")
df_all = pd.read_sql("""
    SELECT id, managedAt, mediumName, direction, journey, tag_a, tag_b, tag_c, tags, __source_file
    FROM userchat
    WHERE managedAt >= '2026-10-08 00:00:00' AND managedAt < '2026-10-15 17:00:00'
      AND journey = '사후관리/클레임'
    ORDER BY managedAt
""", conn)
print(f"Total: {len(df_all)}")
for idx, r in df_all.iterrows():
    print(f"[{idx+1}] ID={r['id']} | Date={r['managedAt']} | Medium={r['mediumName']} | Tag={r['tags']} | Source={r['__source_file']}")
