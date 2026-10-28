import sqlite3

conn = sqlite3.connect(r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db")
c = conn.cursor()
c.execute("SELECT date(managedAt) as d, count(*) FROM userchat WHERE managedAt >= '2026-09-01' GROUP BY d ORDER BY d")
for r in c.fetchall():
    print(r)
conn.close()
