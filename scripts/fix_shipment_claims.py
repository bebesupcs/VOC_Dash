# -*- coding: utf-8 -*-
import sqlite3
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

db_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("1. Deleting zombie duplicate rows (vendor_type = '풀필먼트')...")
cur.execute("DELETE FROM shipment_claims WHERE vendor_type = '풀필먼트'")
deleted_cnt = cur.rowcount
print(f"   Deleted {deleted_cnt} zombie rows.")

print("2. Normalizing '저단가 반송' and '운임비불만' to '운임비 불만'...")
cur.execute("""
    UPDATE shipment_claims
    SET claim_type = '운임비 불만'
    WHERE claim_type IN ('저단가반송', '저단가 반송', '저단가', '운임비불만', '운임비 불만')
""")
updated_cnt = cur.rowcount
print(f"   Updated {updated_cnt} rows to '운임비 불만'.")

conn.commit()

print("\n=== Current Claim Types in shipment_claims ===")
cur.execute("""
    SELECT vendor_type, claim_type, count(*)
    FROM shipment_claims
    GROUP BY vendor_type, claim_type
    ORDER BY vendor_type, count(*) DESC
""")
for r in cur.fetchall():
    print(r)

conn.close()
