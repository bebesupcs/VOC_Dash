# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')

print("=== Userchat rows with managedAt between 2026-10-08 and 2026-10-15 ===")
df = pd.read_sql("""
    SELECT count(1) as cnt, min(managedAt) as min_dt, max(managedAt) as max_dt, __source_file
    FROM userchat
    WHERE managedAt >= '2026-10-08 00:00:00' AND managedAt < '2026-10-15 17:00:00'
    GROUP BY __source_file
""", conn)
print(df)

print("\n=== Userchat where week_start_date = '2026-10-08' ===")
df2 = pd.read_sql("""
    SELECT count(1) as cnt, min(managedAt) as min_dt, max(managedAt) as max_dt, __source_file
    FROM userchat
    WHERE week_start_date = '2026-10-08'
    GROUP BY __source_file
""", conn)
print(df2)
