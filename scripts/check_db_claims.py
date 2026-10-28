import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

db_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
con = sqlite3.connect(db_path)
cur = con.cursor()

print("=== ALL records in 10월 2주 where tag_a == '물티슈' ===")
cur.execute("""
    SELECT id, date, journey, tag_a, tag_b, tag_c, product_name
    FROM fact_voc
    WHERE year = 2026 AND month LIKE '%10%' AND week_of_month LIKE '%2%'
      AND tag_a = '물티슈'
""")
rows = cur.fetchall()
print(f"Total rows found: {len(rows)}")
for r in rows:
    print(f"  id={r[0]} | date={r[1]} | journey={r[2]} | tag_a={r[3]} | tag_b={r[4]} | tag_c={r[5]} | prod={r[6]}")
