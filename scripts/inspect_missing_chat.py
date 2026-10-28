import os, sqlite3, json

db_path = os.path.join(os.environ['TEMP'], 'channeltalk_voc_local.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

chat_id = "6ad05c8d9dc37c2ff0b8" # 이혜림
print("=== userchat ===")
c.execute("SELECT * FROM userchat WHERE id = ?", (chat_id,))
r = c.fetchone()
if r:
    for k in r.keys():
        if r[k] is not None and str(r[k]).strip() != "":
            print(f"  {k}: {r[k]}")

print("\n=== userchat_description ===")
c.execute("SELECT * FROM userchat_description WHERE userChatId = ?", (chat_id,))
for row in c.fetchall():
    print(dict(row))

print("\n=== userchat_meet ===")
c.execute("SELECT * FROM userchat_meet WHERE userChatId = ?", (chat_id,))
for row in c.fetchall():
    print(dict(row))
