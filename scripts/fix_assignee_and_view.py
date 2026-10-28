import sqlite3
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

db_paths = [
    r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db",
    r"C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db"
]

for db_path in db_paths:
    if not os.path.exists(db_path):
        print(f"File not found: {db_path}")
        continue
    print(f"\nProcessing: {db_path}")
    conn = sqlite3.connect(db_path, timeout=120)
    cur = conn.cursor()

    # 1. Clean up userchat assigneeId if it ends with .0
    cur.execute("UPDATE userchat SET assigneeId = SUBSTR(assigneeId, 1, LENGTH(assigneeId)-2) WHERE assigneeId LIKE '%.0'")
    updated_rows = cur.rowcount
    print(f"Cleaned up {updated_rows} assigneeId rows ending with .0 in userchat")

    # 2. Update fact_voc view to use robust integer casting on join
    cur.execute("SELECT sql FROM sqlite_master WHERE name = 'fact_voc'")
    row = cur.fetchone()
    if row and row[0]:
        sql = row[0]
        old_join = "ON CAST(p.assigneeId AS TEXT) = CAST(mgr.id AS TEXT)"
        robust_join = "ON CAST(CAST(p.assigneeId AS REAL) AS INTEGER) = CAST(CAST(mgr.id AS REAL) AS INTEGER)"
        if old_join in sql:
            new_sql = sql.replace(old_join, robust_join)
            cur.execute("DROP VIEW IF EXISTS fact_voc")
            cur.execute(new_sql)
            print("Successfully updated fact_voc view with robust join!")
        else:
            print("old_join not found in view SQL (may already be updated)")

    conn.commit()

    # 3. Test query on W42
    cur.execute("""
        SELECT manager_name, count(1) 
        FROM fact_voc 
        WHERE week_start_date='2026-10-15' 
        GROUP BY manager_name
    """)
    print("W42 (2026-10-15) manager_name counts after fix:")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}건")

    conn.close()

print("\nDone!")
