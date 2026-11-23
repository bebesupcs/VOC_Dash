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
c = conn.cursor()

print("Hyphen rows:")
c.execute("SELECT claim_date, claim_text, action_text, original_invoice_no, __source_file FROM shipment_claims WHERE claim_type = '-' LIMIT 10")
for r in c.fetchall():
    print(r)

print("\nNan rows:")
c.execute("SELECT claim_date, claim_text, action_text, original_invoice_no, __source_file FROM shipment_claims WHERE claim_type = 'nan'")
for r in c.fetchall():
    print(r)
