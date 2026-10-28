import sqlite3, os

paths = [
    os.path.join(os.environ['TEMP'], 'channeltalk_voc_local.db'),
    r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db'
]

for p in paths:
    if os.path.exists(p):
        conn = sqlite3.connect(p)
        c = conn.cursor()
        r = c.execute("DELETE FROM board_daily_counts WHERE mall_name IN ('전체합계', '합계') OR mall_name LIKE '%합계%'").rowcount
        conn.commit()
        conn.close()
        print(f"Deleted {r} duplicate total rows from: {p}")
