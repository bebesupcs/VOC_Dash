# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')

df = pd.read_sql("""
    SELECT id, managedAt, week_start_date, week, journey, full_tag
    FROM fact_voc
    WHERE journey = '사후관리/클레임' AND (week_start_date LIKE '2026-10%' OR managedAt LIKE '2026-10%')
    ORDER BY managedAt
""", conn)
print(df)
