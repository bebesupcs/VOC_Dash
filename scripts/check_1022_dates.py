# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')

df = pd.read_sql("""
    SELECT MIN(managedAt) as min_date, MAX(managedAt) as max_date, COUNT(1) as total_rows
    FROM userchat
    WHERE __source_file LIKE '%2026-10-22%'
""", conn)
print("=== 10-22 file date range ===")
print(df)

df_all = pd.read_sql("""
    SELECT managedAt, mediumName, direction
    FROM userchat
    WHERE __source_file LIKE '%2026-10-22%'
    ORDER BY managedAt
""", conn)
print("\nFirst 5 rows:")
print(df_all.head(5))
print("\nLast 5 rows:")
print(df_all.tail(5))
