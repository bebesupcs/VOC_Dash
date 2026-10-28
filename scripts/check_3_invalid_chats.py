# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')

df = pd.read_sql("""
    SELECT id, managedAt, mediumName, direction, tag_a, tag_b, tag_c, tags
    FROM userchat
    WHERE week_start_date = '2026-10-15'
      AND (mediumName IS NULL OR mediumName != 'phoneNumber')
      AND tag_c IN ('테스트', '오발신', '부재', '인입후끊김')
""", conn)
print("=== 3 invalid chats in W42 ===")
print(df)
