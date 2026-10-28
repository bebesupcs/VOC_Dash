# -*- coding: utf-8 -*-
import sqlite3
import os
import tempfile

db_path = os.path.join(tempfile.gettempdir(), 'channeltalk_voc_local.db')
con = sqlite3.connect(db_path)
cur = con.cursor()
cur.execute("""
    SELECT COALESCE(__source_file, 'API/NULL'), COUNT(*)
    FROM userchat
    WHERE date(managedAt) BETWEEN '2026-10-15' AND '2026-10-21'
    GROUP BY __source_file
""")
for r in cur.fetchall():
    print(r)
