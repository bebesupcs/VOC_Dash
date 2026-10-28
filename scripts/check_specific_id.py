import os, sqlite3

db_path = os.path.join(os.environ['TEMP'], 'channeltalk_voc_local.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT id, name, tags, week_of_month, week_start_date, report_date FROM userchat WHERE id = '6ad05da6c9e2d13a2fef'")
row = c.fetchone()
print("Found in DB:", dict(row) if row else "NOT FOUND IN DB!")
