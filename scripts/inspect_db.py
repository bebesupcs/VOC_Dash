import sqlite3
import os

db_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
if not os.path.exists(db_path):
    db_path = r"C:\Users\hshwa\OneDrive\문서\VOC점검\channeltalk_voc_claim_test.db"

conn = sqlite3.connect(db_path)
c = conn.cursor()

print("DB Path:", db_path)
for row in c.execute("SELECT type, name, sql FROM sqlite_master WHERE name IN ('fact_voc', 'userchat', 'userchat_description', 'vw_standard_meet', 'tag_master')"):
    print("=" * 60)
    print(f"TYPE: {row[0]}, NAME: {row[1]}")
    print("SQL:")
    print(row[2])
