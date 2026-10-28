import sqlite3

conn = sqlite3.connect(r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db")
cur = conn.cursor()

cur.execute("SELECT id, channel_type FROM official_channel_override LIMIT 5")
print("official_channel_override samples:", cur.fetchall())

cur.execute("SELECT id, channel_type FROM fact_voc WHERE week_start_date = '2026-10-08' LIMIT 5")
print("fact_voc samples:", cur.fetchall())

cur.execute("""
    SELECT COUNT(*)
    FROM fact_voc f
    JOIN official_channel_override o ON f.id = o.id
    WHERE f.week_start_date = '2026-10-08'
""")
print("Matched rows for 2026-10-08:", cur.fetchone()[0])
