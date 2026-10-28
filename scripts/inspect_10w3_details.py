# -*- coding: utf-8 -*-
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

names = ['전광석', '김관나', '정은주', '심원규', '최윤명', '김하윤']

print("=== Checking customers in userchat ===")
for name in names:
    c.execute("""
        SELECT u.id, u.managedAt, u.name, u.tags, u.journey, u.description,
               d.product_name, d.manufacture_date, d.mall_name, d.customer_issue, d.cs_action
        FROM userchat u
        LEFT JOIN userchat_description d ON u.id = d.id
        WHERE u.name = ?
        ORDER BY u.managedAt DESC LIMIT 1
    """, (name,))
    row = c.fetchone()
    if row:
        cols = [col[0] for col in c.description]
        d = dict(zip(cols, row))
        print(f"\nID: {d['id']} | Cust: {d['name']} | Date: {d['managedAt']}")
        print(f"  Tag: {d['tags']} | Journey: {d['journey']}")
        print(f"  Prod: {d['product_name']}")
        print(f"  Mfg: {d['manufacture_date']}")
        print(f"  Mall: {d['mall_name']}")
        print(f"  Issue: {d['customer_issue']}")
        print(f"  Action: {d['cs_action']}")
        print(f"  Raw description field: {repr(d['description'])}")
    else:
        print(f"\nCustomer {name}: NOT FOUND in userchat!")

conn.close()
