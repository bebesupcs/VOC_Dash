# -*- coding: utf-8 -*-
import sqlite3, os, sys
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.append('scripts')
import import_shipments

db_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=== 이전 잘못 적재된 CJ 레코드 및 import_log 정리 ===")
# claim_date가 비어있거나 CJ대한통운 소스 파일인 레코드 삭제
cur.execute("DELETE FROM shipment_claims WHERE __source_file LIKE 'CJ대한통운%' OR claim_date = ''")
print("Deleted rows from shipment_claims:", cur.rowcount)

cur.execute("DELETE FROM shipment_import_log WHERE source_file LIKE 'CJ대한통운%'")
print("Deleted rows from shipment_import_log:", cur.rowcount)
conn.commit()

# CJ 엑셀 파일들 재적재
x_base = Path(r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\raw\배송 데이터 원본")
cj_files = sorted(x_base.glob("CJ대한통운*.xlsx"))
print(f"Found {len(cj_files)} CJ files to re-import:")
for f in cj_files:
    print(f"▶ Processing {f.name}...")
    i, u, s = import_shipments.process_file(conn, f)
    conn.commit()
    print(f"  ✓ {f.name}: insert {i}, update {u}, skip {s}")

print("\n=== 재적재 후 11월 배송 데이터 확인 ===")
cur.execute("""
    SELECT week, week_of_month, vendor_type, count(*), min(claim_date), max(claim_date)
    FROM shipment_claims
    WHERE claim_date >= '2026-11-01'
    GROUP BY week, week_of_month, vendor_type
""")
for r in cur.fetchall():
    print(r)

print("\n=== 2026-W45 주차 배송 데이터 확인 ===")
cur.execute("""
    SELECT vendor_type, claim_type, count(*)
    FROM shipment_claims
    WHERE week = '2026-W45'
    GROUP BY vendor_type, claim_type
""")
for r in cur.fetchall():
    print(r)

conn.close()
