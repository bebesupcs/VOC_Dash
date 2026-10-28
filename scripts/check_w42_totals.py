# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

c.execute("""
    SELECT count(*),
           SUM(CASE WHEN mediumType IN ('phone', 'phoneNumber') THEN 1 ELSE 0 END) as phone_cnt,
           SUM(CASE WHEN mediumType NOT IN ('phone', 'phoneNumber') THEN 1 ELSE 0 END) as non_phone_cnt,
           SUM(CASE WHEN alfTriggered='true' THEN 1 ELSE 0 END) as alf_trig,
           SUM(CASE WHEN is_ai_completed=1 THEN 1 ELSE 0 END) as ai_comp,
           SUM(CASE WHEN is_ai_transferred=1 THEN 1 ELSE 0 END) as ai_trans
    FROM userchat
    WHERE week_start_date='2026-10-15'
""")
print(c.fetchone())

# tags가 비어있는 건이 있는지?
c.execute("""
    SELECT count(*)
    FROM userchat
    WHERE week_start_date='2026-10-15' AND (tags IS NULL OR tags='')
""")
print("빈 태그 건수:", c.fetchone()[0])
