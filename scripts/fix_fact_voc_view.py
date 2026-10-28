# -*- coding: utf-8 -*-
import sqlite3
import os
import tempfile

for db_path in [os.path.join(tempfile.gettempdir(), 'channeltalk_voc_local.db')]:
    if not os.path.exists(db_path):
        continue
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT sql FROM sqlite_master WHERE name = 'fact_voc'")
    row = cur.fetchone()
    if not row:
        continue
    sql = row[0]
    
    # Replace period_week logic to respect userchat.week_start_date first
    old_target = """    period_week AS (
        SELECT
            base.*,
            DATE(
                __basis_date,
                '-' || ((CAST(STRFTIME('%w', __basis_date) AS INTEGER) + 3) % 7) || ' days'
            ) AS __week_start_date
        FROM base
    ),"""
    
    new_target = """    period_week AS (
        SELECT
            base.*,
            COALESCE(
                NULLIF(base.week_start_date, ''),
                DATE(
                    __basis_date,
                    '-' || ((CAST(STRFTIME('%w', __basis_date) AS INTEGER) + 3) % 7) || ' days'
                )
            ) AS __week_start_date
        FROM base
    ),"""

    if old_target in sql:
        updated_sql = sql.replace(old_target, new_target)
        cur.execute("DROP VIEW IF EXISTS fact_voc")
        cur.execute(updated_sql)
        con.commit()
        print(f"Updated fact_voc in {db_path}")
    else:
        print(f"Target not found in {db_path}")
    con.close()
