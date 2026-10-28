import os, sqlite3

db_path = os.path.join(os.environ['TEMP'], 'channeltalk_voc_local.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

ids = [
    '6ad05c8d9dc37c2ff0b8', # 이혜림
    '6ad193f038eadf327d0a', # 이은영
    '6ad56b8468ed0edb9c43', # 정소영
    '6ad6be748f7f2a4debe0', # 정은주
    '6ad6cafc5154045527fb', # 최윤영
    '6ad829192171ec52ff3f', # 김한나
    '6ad717fdd9bc6d04e922', # 노아
]

for cid in ids:
    c.execute("SELECT * FROM userchat_description WHERE id = ?", (cid,))
    r = c.fetchone()
    print(cid, dict(r) if r else "NO DESCRIPTION ROW")
