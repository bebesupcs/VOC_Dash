# -*- coding: utf-8 -*-
import sqlite3

for path in [
    r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db',
    r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db'
]:
    try:
        conn = sqlite3.connect(path, timeout=5)
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN is_ai_completed=1 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN is_ai_transferred=1 THEN 1 ELSE 0 END)
            FROM userchat
            WHERE week_start_date='2026-10-15'
        """)
        row = c.fetchone()
        print(f"Path: {path}\n  W42 total: {row[0]}, completed: {row[1]}, transferred: {row[2]}")
        conn.close()
    except Exception as e:
        print(f"Error {path}: {e}")
