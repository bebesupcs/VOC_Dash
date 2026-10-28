# -*- coding: utf-8 -*-
import sqlite3
import os
import tempfile

db_path = os.path.join(tempfile.gettempdir(), 'channeltalk_voc_local.db')
con = sqlite3.connect(db_path)
cur = con.cursor()

keywords = ['인쇄', '스티커', '전광석', '김선희']
for kw in keywords:
    cur.execute("""
        SELECT u.id, u.name, u.managedAt, u.tag_a, u.tag_b, u.tag_c, d.customer_issue, d.product_name
        FROM userchat u
        LEFT JOIN userchat_description d ON u.id = d.id
        WHERE (d.customer_issue LIKE ? OR u.description LIKE ? OR u.name LIKE ?)
          AND u.managedAt BETWEEN '2026-10-15' AND '2026-10-22'
    """, (f'%{kw}%', f'%{kw}%', f'%{kw}%'))
    rows = cur.fetchall()
    print(f"Keyword: {kw}, rows: {len(rows)}")
    for r in rows:
        print(" ", r[0], r[1], r[2], r[3], r[4], r[5], (r[6] or '')[:30], (r[7] or '')[:30])
