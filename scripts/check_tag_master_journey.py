# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')

df = pd.read_sql("""
    SELECT journey, tag_a, COUNT(1) as cnt
    FROM tag_master
    GROUP BY journey, tag_a
""", conn)
print("=== tag_master journey vs tag_a ===")
print(df.to_string())
