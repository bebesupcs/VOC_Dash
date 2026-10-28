# -*- coding: utf-8 -*-
import sqlite3
import os
import tempfile

for db_path in [os.path.join(tempfile.gettempdir(), 'channeltalk_voc_local.db'), r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db']:
    if os.path.exists(db_path):
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("""
            UPDATE userchat 
            SET week_start_date = '2026-10-15',
                week_end_date = '2026-10-21',
                week = '2026-W42',
                week_of_month = '10월 3주',
                quarter = '4분기',
                month = '2026-10'
            WHERE __source_file LIKE '%2026-10-22%'
        """)
        con.commit()
        print(f"Updated {cur.rowcount} rows in {db_path}")
        con.close()
