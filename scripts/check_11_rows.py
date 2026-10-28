import os, sqlite3

missing_names = [
    ("김정도", "2026-10-15", "휴먼에러", "세팅오류"),
    ("이은영", "2026-10-16", "용액", "수분부족"),
    ("소비자", "2026-10-19", "용액", "거품과다"),
    ("정소영", "2026-10-19", "원단(공정)이물", "원사찌꺼기"),
    ("이소현", "2026-10-19", "휴먼에러", "세팅오류"),
    ("정은주", "2026-10-20", "원단면", "원사뭉침"),
    ("최윤영", "2026-10-20", "포장공정", "캡부착불량"),
    ("노아", "2026-10-20", "포장", "실링불량"),
    ("전광석", "2026-10-21", "포장공정", "찢김"),
    ("김한나", "2026-10-21", "포장", "누액")
]

db_path = os.path.join(os.environ['TEMP'], 'channeltalk_voc_local.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

for name, date, b, sub in missing_names:
    print(f"\nSearching for {name} ({date}) [{b} > {sub}]:")
    c.execute("SELECT id, name, tags, tag_a, tag_b, tag_c, managedAt, description FROM userchat WHERE name LIKE ? AND managedAt LIKE ?", 
              (f"%{name}%", f"{date}%"))
    rows = c.fetchall()
    if rows:
        for r in rows:
            print(f"  ID: {r['id']} | tags: {r['tags']} | tag_a: {r['tag_a']} | desc: {str(r['description'])[:60]}...")
    else:
        print("  NO MATCH IN USERCHAT ON THAT DATE!")
