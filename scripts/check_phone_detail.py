# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')

print("=== Userchat for 2026-10-15 phone calls ===")
df = pd.read_sql("""
    SELECT mediumName, direction, is_after_hours, tag_c, COUNT(1) as cnt
    FROM userchat
    WHERE week_start_date = '2026-10-15' AND mediumName = 'phoneNumber'
    GROUP BY mediumName, direction, is_after_hours, tag_c
""", conn)
print(df)

print("\n=== Aggregate by direction and is_after_hours ===")
df_agg = pd.read_sql("""
    SELECT direction, is_after_hours, COUNT(1) as cnt
    FROM userchat
    WHERE week_start_date = '2026-10-15' AND mediumName = 'phoneNumber'
    GROUP BY direction, is_after_hours
""", conn)
print(df_agg)

print("\n=== Aggregate by direction with valid (tag_c not in test/오발신/부재/인입후끊김) ===")
df_valid = pd.read_sql("""
    SELECT direction, 
           CASE WHEN tag_c IN ('테스트', '오발신', '부재', '인입후끊김') THEN 'invalid' ELSE 'valid' END as validity,
           COUNT(1) as cnt
    FROM userchat
    WHERE week_start_date = '2026-10-15' AND mediumName = 'phoneNumber'
    GROUP BY direction, validity
""", conn)
print(df_valid)
