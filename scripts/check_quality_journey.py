# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')

df = pd.read_sql("""
    SELECT u.id, u.tags, u.journey as u_j, tm.journey as tm_j, u.tag_a, u.tag_b, u.tag_c
    FROM userchat u
    LEFT JOIN tag_master tm ON u.tags = tm.full_tag
    WHERE u.week_start_date = '2026-10-15'
      AND (u.journey = '제품사용' OR tm.journey = '제품사용')
""", conn)
print(f"Total in DB: {len(df)}")
print("\nu_j vs tm_j counts:")
print(pd.crosstab(df['u_j'].fillna('NULL'), df['tm_j'].fillna('NULL')))

print("\nAll 23 rows:")
for idx, r in df.iterrows():
    print(f"[{idx+1}] ID={r['id']} | u_j={r['u_j']} | tm_j={r['tm_j']} | Tag={r['tags']}")
