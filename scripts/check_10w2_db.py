# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')

df = pd.read_sql("""
    SELECT id, managedAt, week_start_date, week, mediumName, direction, journey, tag_a, tag_b, tag_c, tags
    FROM userchat
    WHERE __source_file LIKE '%10%2%'
""", conn)
print(f"Total rows from 10월2주 xlsb: {len(df)}")
print("\nDate range:", df['managedAt'].min(), "~", df['managedAt'].max())
print("\nWeek start dates in this file:")
print(df['week_start_date'].value_counts(dropna=False))
print("\nMedium breakdown:")
print(df['mediumName'].value_counts(dropna=False))

print("\nJourney breakdown:")
print(df['journey'].value_counts(dropna=False))

print("\nRows where journey == '사후관리/클레임' or journey contains '클레임':")
df_claim = df[df['journey'].astype(str).str.contains('사후관리|클레임')]
print(f"Total journey claim rows: {len(df_claim)}")
for idx, r in df_claim.iterrows():
    print(f"ID={r['id']} | Date={r['managedAt']} | WStart={r['week_start_date']} | Medium={r['mediumName']} | Journey={r['journey']} | Tags={r['tags']}")
