# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')

print("=== W41 (10월 2주차, 2026-10-08) journey == '사후관리/클레임' ===")
df_w41 = pd.read_sql("""
    SELECT id, managedAt, medium_type, direction, journey, tag_a, tag_b, tag_c, full_tag, customer_issue, cs_action
    FROM fact_voc
    WHERE week_start_date = '2026-10-08' AND journey = '사후관리/클레임'
""", conn)
print(f"Total: {len(df_w41)}")
print(df_w41[['id', 'medium_type', 'tag_a', 'tag_b', 'tag_c', 'full_tag']])

print("\n=== W42 (10월 3주차, 2026-10-15) journey == '사후관리/클레임' ===")
df_w42 = pd.read_sql("""
    SELECT id, managedAt, medium_type, direction, journey, tag_a, tag_b, tag_c, full_tag, customer_issue, cs_action
    FROM fact_voc
    WHERE week_start_date = '2026-10-15' AND journey = '사후관리/클레임'
""", conn)
print(f"Total: {len(df_w42)}")
print(df_w42[['id', 'medium_type', 'tag_a', 'tag_b', 'tag_c', 'full_tag']])
