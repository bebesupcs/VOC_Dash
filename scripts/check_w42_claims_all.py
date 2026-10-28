# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')

df = pd.read_sql("""
    SELECT id, managedAt, week_start_date, week, journey, tag_a, tag_b, tag_c, tags, __source_file
    FROM userchat
    WHERE journey = '사후관리/클레임' AND (week IN ('W42', '2026-W42') OR week_start_date = '2026-10-15')
""", conn)
print("=== userchat journey == '사후관리/클레임' for W42 ===")
print(f"Total: {len(df)}")
for idx, r in df.iterrows():
    print(f"[{idx+1}] ID={r['id']} | Date={r['managedAt']} | WStart={r['week_start_date']} | Week={r['week']} | Tags={r['tags']} | Source={r['__source_file']}")
