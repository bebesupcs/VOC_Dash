# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')

print("=== standard_meet for W41 and W42 ===")
df = pd.read_sql("""
    SELECT week, week_start_date, direction, COUNT(1) as cnt
    FROM standard_meet
    WHERE week IN ('W41', 'W42', '2026-W41', '2026-W42') OR week_start_date IN ('2026-10-08', '2026-10-15')
    GROUP BY week, week_start_date, direction
""", conn)
print(df)
