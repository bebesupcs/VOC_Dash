# -*- coding: utf-8 -*-
import sqlite3
import os
import tempfile

db_path = os.path.join(tempfile.gettempdir(), 'channeltalk_voc_local.db')
con = sqlite3.connect(db_path)
cur = con.cursor()
cur.execute("""
    SELECT 
        u.id, u.name, u.managedAt, u.report_date, u.__schema_year, u.__source_file,
        u.tag_a, u.tag_b, u.journey, d.product_name, d.customer_issue, d.quality_send_yn
    FROM userchat u
    LEFT JOIN userchat_description d ON u.id = d.id
    WHERE u.name = '이은영'
""")
for r in cur.fetchall():
    print(r)
