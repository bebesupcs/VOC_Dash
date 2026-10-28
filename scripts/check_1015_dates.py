# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')

df = pd.read_sql("""
    SELECT MIN(managedAt) as min_date, MAX(managedAt) as max_date, COUNT(1) as total_rows
    FROM userchat
    WHERE __source_file LIKE '%2026-10-15%'
""", conn)
print("=== 10-15 file date range ===")
print(df)

df_med = pd.read_sql("""
    SELECT mediumName, direction, COUNT(1) as cnt
    FROM userchat
    WHERE __source_file LIKE '%2026-10-15%'
    GROUP BY mediumName, direction
""", conn)
print("\nMedium breakdown in 10-15 file:")
print(df_med)
