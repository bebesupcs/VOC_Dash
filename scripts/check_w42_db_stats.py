# -*- coding: utf-8 -*-
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

import os
LOCAL_DB = r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db'
DB_PATH = LOCAL_DB if os.path.exists(LOCAL_DB) else r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN u.description IS NOT NULL AND LENGTH(u.description) > 5 THEN 1 ELSE 0 END) as has_raw_desc,
        SUM(CASE WHEN d.customer_issue IS NOT NULL AND LENGTH(d.customer_issue) > 0 THEN 1 ELSE 0 END) as has_parsed_issue,
        SUM(CASE WHEN d.product_name IS NOT NULL AND LENGTH(d.product_name) > 0 THEN 1 ELSE 0 END) as has_prod,
        SUM(CASE WHEN d.manufacture_date IS NOT NULL AND LENGTH(d.manufacture_date) > 0 THEN 1 ELSE 0 END) as has_mfg
    FROM userchat u
    LEFT JOIN userchat_description d ON u.id = d.id
    WHERE u.week_num = 42 AND (u.__schema_year = '2026' OR u.week = 'W42')
""")
row = c.fetchone()
print(f"Total W42 in userchat: {row[0]}")
print(f"Has raw description: {row[1]}")
print(f"Has parsed customer_issue: {row[2]}")
print(f"Has product_name: {row[3]}")
print(f"Has manufacture_date: {row[4]}")

# Check the quality chats specifically in W42
c.execute("""
    SELECT u.id, u.name, u.tags, u.journey, u.description, d.customer_issue, d.product_name, d.manufacture_date
    FROM userchat u
    LEFT JOIN userchat_description d ON u.id = d.id
    WHERE u.week_num = 42 AND (u.__schema_year = '2026' OR u.week = 'W42') AND (u.journey = '제품사용' OR u.journey = '품질')
""")
q_rows = c.fetchall()
print(f"\nW42 Quality chats count in userchat: {len(q_rows)}")
for r in q_rows[:5]:
    print(f"ID: {r[0]} | Name: {r[1]} | Tag: {r[2]} | Issue: {repr(r[5])} | Prod: {repr(r[6])} | RawDesc len: {len(r[4]) if r[4] else 0}")

conn.close()
