# -*- coding: utf-8 -*-
import sqlite3, os, sys
import pandas as pd
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.append('scripts')
from import_shipments import excel_file, find_header, clean

cj_path = Path(r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\raw\배송 데이터 원본\CJ대한통운 CS일지_1111.xlsx")
print("=== CJ대한통운 CS일지_1111.xlsx 복호화 및 검사 ===")
if cj_path.exists():
    xls, src, eng = excel_file(cj_path)
    print("Sheets:", xls.sheet_names)
    for s in xls.sheet_names:
        if hasattr(src, 'seek'):
            src.seek(0)
        df_raw = pd.read_excel(src, sheet_name=s, engine=eng, dtype=str, header=None)
        h_idx = find_header(df_raw)
        if hasattr(src, 'seek'):
            src.seek(0)
        df = pd.read_excel(src, sheet_name=s, engine=eng, dtype=str, header=h_idx)
        print(f"Sheet '{s}': shape={df.shape}, header_row={h_idx+1}")
        print("  Columns:", [clean(c) for c in df.columns if clean(c)][:15])
        # 접수일자 컬럼 확인
        date_cols = [c for c in df.columns if '접수' in str(c) or '일자' in str(c) or '날짜' in str(c)]
        print("  Date cols:", date_cols)
        if date_cols:
            dc = date_cols[0]
            dates = df[dc].dropna().unique()
            print(f"  Dates in {dc} (min~max):", sorted(str(d) for d in dates if str(d).strip())[:5], "~", sorted(str(d) for d in dates if str(d).strip())[-5:])
else:
    print("File not found!")

db_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("\n=== shipment_claims 에서 CJ 1111 관련 데이터 확인 ===")
cur.execute("SELECT count(*), min(claim_date), max(claim_date) FROM shipment_claims WHERE __source_file LIKE '%1111%'")
print("From CJ 1111 file in DB:", cur.fetchone())

cur.execute("SELECT week, week_of_month, count(*) FROM shipment_claims WHERE __source_file LIKE '%1111%' GROUP BY week, week_of_month")
print("By week from 1111 file:", cur.fetchall())

print("\n=== shipment_claims 전체에서 11월 데이터 확인 ===")
cur.execute("SELECT week, week_of_month, vendor_type, count(*) FROM shipment_claims WHERE claim_date >= '2026-11-01' GROUP BY week, week_of_month, vendor_type")
for r in cur.fetchall():
    print(r)

print("\n=== shipment_import_log 확인 ===")
cur.execute("SELECT * FROM shipment_import_log ORDER BY rowid DESC LIMIT 10")
for r in cur.fetchall():
    print(r)

conn.close()
