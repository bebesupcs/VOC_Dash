# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')

df = pd.read_sql("""
    SELECT u.id, u.tags, tm.journey, u.description
    FROM userchat u
    LEFT JOIN tag_master tm ON u.tags = tm.full_tag
    WHERE u.week_start_date = '2026-10-15'
      AND (u.journey = '제품사용' OR tm.journey = '제품사용')
      AND u.tag_c != '재통화'
""", conn)
print(f"Total pure quality claims in W42: {len(df)}")
for idx, r in df.iterrows():
    print(f"[{idx+1}] ID={r['id']} | Tag={r['tags']} | Desc={str(r['description'])[:120]}")
