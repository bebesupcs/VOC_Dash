import os, json, sqlite3, re

user_raw = """10월	3주	물티슈	원단면	보푸라기(원단면)	김지훈	오세빈	2026년 10월 15일	(시그니처위드레드) 70매 캡 20팩**박스
10월	3주	물티슈	원단면	보푸라기(원단면)	김동욱	오세빈	2026년 10월 15일	(센시) 80매 캡 10팩
10월	3주	물티슈	원단면	보푸라기(가장자리)	김동욱	오세빈	2026년 10월 15일	(센시) 80매 캡 10팩
10월	3주	물티슈	원단(공정)이물	기타이물	이혜림	한윤서	2026년 10월 15일	(시그니처위드레드) 70매 캡 20팩**박스
10월	3주	물티슈	원단면	보푸라기(가장자리)	김지훈	오세빈	2026년 10월 15일	(시그니처위드레드) 70매 캡 20팩**박스
10월	3주	클레임(공통)	휴먼에러	세팅오류	김정도	오세빈	2026년 10월 15일	(Z-홈 섬유유연제) 코튼앤크림향x1개**리뉴얼
10월	3주	물티슈	용액	수분부족	이은영	한윤서	2026년 10월 16일	(트러스트프리미엄) 80매 캡 20팩**박스
10월	3주	물티슈	원단면	부정형절단	이혜림	한윤서	2026년 10월 16일	(시그니처위드레드) 70매 캡 20팩**박스
10월	3주	물티슈	이취	화학-약품냄새	곽아름	한윤서	2026년 10월 16일	(시그니처블루 에코) 70매 캡 20팩**박스
10월	3주	물티슈	포장공정	접지물림	안주희	한윤서	2026년 10월 19일	(센시) 80매 캡 10팩
10월	3주	물티슈	용액	거품과다	소비자	AI	2026년 10월 19일	(손세정티슈) 20매 휴대 12팩
10월	3주	물티슈	포장공정	찢김	이동희	한윤서	2026년 10월 19일	(시그니처레드) 70매 캡 20팩**박스
10월	3주	물티슈	원단(공정)이물	원사찌꺼기	정소영	한윤서	2026년 10월 19일	(시그니처블루) 70매 캡 20팩**박스
10월	3주	물티슈	포장공정	찢김	김은주	오세빈	2026년 10월 19일	(시그니처위드레드) 70매 캡 20팩**박스
10월	3주	클레임(공통)	휴먼에러	세팅오류	이소현	박주희	2026년 10월 19일	(Z-SK 수딩앤모이스춰로션) 300mlx1개
10월	3주	물티슈	원단면	원사뭉침	정은주	한윤서	2026년 10월 20일	(시그니처블루 에코) 70매 캡 20팩**박스
10월	3주	물티슈	포장공정	캡떨어짐	심필규	오세빈	2026년 10월 20일	(시그니처블랙 헤리티지에디션) 66매 캡 20팩**박스
10월	3주	물티슈	포장공정	캡부착불량	최윤영	한윤서	2026년 10월 20일	(시그니처블루) 32매 슬림 (캡) 12팩
10월	3주	물티슈	원단(공정)이물	탄화물	김하윤	오세빈	2026년 10월 20일	(클린비데) 80매 캡 8팩
10월	3주	물티슈	이취	화학-약품냄새	이혜림	한윤서	2026년 10월 20일	(시그니처블루 에코) 70매 캡 10팩
10월	3주	클레임(공통)	제품	리뉴얼불만	소비자	한윤서	2026년 10월 20일	(시그니처위드블루) 70매 캡 20팩**박스
10월	3주	물티슈	포장공정	찢김	채진	오세빈	2026년 10월 20일	(시그니처위드블루) 70매 캡 20팩**박스
10월	3주	패밀리	포장	실링불량	노아	박주희	2026년 10월 20일	(Z-베베숲 일회용 수건)x10개**인박스1개
10월	3주	물티슈	포장공정	찢김	전광석	한윤서	2026년 10월 21일	(시그니처위드레드) 70매 캡 20팩**박스
10월	3주	패밀리	포장	누액	김한나	오세빈	2026년 10월 21일	(Z-홈 섬유유연제) 브리즈가든향x1개[R2-OT]
10월	3주	물티슈	포장공정	캡안떨어짐	소비자	한윤서	2026년 10월 21일	(시그니처블루 에코) 70매 캡 20팩**박스
10월	3주	클레임(공통)	제품	리뉴얼불만	김경미	오세빈	2026년 10월 21일	(시그니처블루) 32매 슬림 (캡) 12팩"""

user_rows = [l.split('\t') for l in user_raw.strip().split('\n')]
print(f"Total user rows: {len(user_rows)}")

# Check SQLite DB
db_path = os.path.join(os.environ['TEMP'], 'channeltalk_voc_local.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print("Tables in DB:", tables)

# Check userchats or user_chats
chat_table = 'userchat'
print(f"Querying chat table: {chat_table}")

c.execute(f"PRAGMA table_info({chat_table})")
cols = [r['name'] for r in c.fetchall()]
print(f"Cols: {cols}")

found_count = 0
missing = []
for row in user_rows:
    cust = row[5].strip()
    sub = row[4].strip()
    date_str = row[7].strip()
    m = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', date_str)
    iso_date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""
    
    # search by customer name in userchat
    c.execute(f"SELECT id, name, description, tags, tag_a, tag_b, tag_c, managedAt, report_date FROM {chat_table} WHERE (report_date = ? OR managedAt LIKE ?) AND (name LIKE ? OR description LIKE ?)", 
              (iso_date, f"{iso_date}%", f"%{cust}%", f"%{cust}%"))
    results = c.fetchall()
    if results:
        found_count += 1
        r0 = results[0]
        print(f"MATCH: {cust} ({iso_date}) -> ID: {r0['id']}, tags: {r0['tags']}, tag_a: {r0['tag_a']}, tag_b: {r0['tag_b']}, tag_c: {r0['tag_c']}")
    else:
        # try searching just by name in that week
        c.execute(f"SELECT id, name, description, tags, tag_a, tag_b, tag_c, report_date FROM {chat_table} WHERE name LIKE ? AND report_date BETWEEN '2026-10-15' AND '2026-10-21'", (f"%{cust}%",))
        res2 = c.fetchall()
        if res2:
            found_count += 1
            r0 = res2[0]
            print(f"MATCH (approx date): {cust} ({r0['report_date']}) -> ID: {r0['id']}, tags: {r0['tags']}, tag_a: {r0['tag_a']}, tag_b: {r0['tag_b']}")
        else:
            missing.append((cust, iso_date, row[2], row[3], sub, row[8]))

print(f"\nSummary: Found {found_count} / {len(user_rows)} in {chat_table}")
print(f"Missing count: {len(missing)}")
for m in missing:
    print(f"  MISSING: {m[0]} ({m[1]}) {m[2]} > {m[3]} > {m[4]} | {m[5]}")
