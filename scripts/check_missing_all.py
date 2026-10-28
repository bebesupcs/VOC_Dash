import sys
import pyxlsb
import sqlite3

sys.stdout.reconfigure(encoding='utf-8')
excel_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\voc 파일\CX팀_26년_10월2주차_VOC현황.xlsb"
db_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get all IDs in SQLite for 10W2
cur.execute("SELECT id FROM fact_voc WHERE year = 2026 AND month LIKE '%10%' AND week_of_month LIKE '%2%'")
db_ids = set(r[0] for r in cur.fetchall())
print(f"Total IDs in fact_voc 10W2: {len(db_ids)}")

with pyxlsb.open_workbook(excel_path) as wb:
    with wb.get_sheet('UserChat data') as s:
        excel_10w2_rows = []
        for r_idx, row in enumerate(s.rows()):
            if r_idx == 0:
                continue
            vals = [c.v for c in row]
            if len(vals) > 108 and vals[108] == 2026.0:
                m = str(vals[100]).strip()
                w = str(vals[101]).strip()
                if '10' in m and '2' in w:
                    excel_10w2_rows.append(vals)

print(f"Total rows in Excel UserChat data 10W2: {len(excel_10w2_rows)}")
missing_in_db = [r for r in excel_10w2_rows if r[0] not in db_ids]
print(f"Excel rows missing in SQLite fact_voc: {len(missing_in_db)}")
for r in missing_in_db:
    print(f"  ID={r[0]} | claim={r[104]} | tag={r[5]} | channel={r[105]} | gubun={r[107]} | closedAt={r[52]}")
