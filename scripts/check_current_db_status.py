# -*- coding: utf-8 -*-
import sqlite3
import os
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

db_path = r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=== USERCHAT INFO ===")
cur.execute("SELECT max(managedAt), min(managedAt), count(*) FROM userchat")
print("Userchat max/min/cnt:", cur.fetchone())

cur.execute("SELECT count(*) FROM userchat WHERE managedAt >= '2026-11-05'")
print("Userchat >= 2026-11-05 count:", cur.fetchone()[0])

cur.execute("SELECT max(date), min(date), count(*) FROM fact_voc")
print("fact_voc max/min/cnt:", cur.fetchone())

cur.execute("SELECT count(*) FROM fact_voc WHERE date >= '2026-11-05'")
print("fact_voc >= 2026-11-05 count:", cur.fetchone()[0])

print("\n=== RECENT IMPORT LOGS ===")
for tbl in ['import_log', 'shipment_import_log', 'board_import_log']:
    try:
        cur.execute(f"SELECT * FROM {tbl} ORDER BY rowid DESC LIMIT 5")
        rows = cur.fetchall()
        print(f"--- {tbl} (last 5) ---")
        for r in rows:
            print(r)
    except Exception as e:
        print(f"Error reading {tbl}: {e}")

conn.close()
