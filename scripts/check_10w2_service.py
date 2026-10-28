# -*- coding: utf-8 -*-
import sqlite3, os, tempfile

db_path = os.path.join(tempfile.gettempdir(), 'channeltalk_voc_local.db')
con = sqlite3.connect(db_path)
cur = con.cursor()

cur.execute("""
    SELECT 
        u.id, u.managedAt, u.name, u.tag_a, u.tag_b, u.tag_c, u.tags, u.journey,
        u.__source_file
    FROM userchat u
    WHERE u.week_start_date = '2026-10-08'
""")
rows = cur.fetchall()

with open('service_10w2_all.txt', 'w', encoding='utf-8') as f:
    f.write(f"Total rows in 10w2: {len(rows)}\n\n")
    
    # 1. 태그 전체 목록
    from collections import Counter
    tag_counts = Counter(r[6] for r in rows)
    f.write("=== 10월 2주차 전체 태그 목록 ===\n")
    for t, cnt in tag_counts.most_common():
        f.write(f"  {cnt:3d}건 | {t}\n")
        
    # 2. 서비스 관련 건 확인
    service_rows = [r for r in rows if any(k in str(r[6]) for k in ['서비스', '휴먼에러', '배송기사', '협력사', '오안내', '세팅오류'])]
    f.write(f"\n=== 서비스/휴먼에러/응대 관련 의심 태그 건 ({len(service_rows)}건) ===\n")
    for r in service_rows:
        f.write(f"  ID={r[0]} | Date={r[1]} | Name={r[2]} | Tags={r[6]} | Source={r[8]}\n")

    # 3. 클레임 전체 확인
    claim_rows = [r for r in rows if '클레임' in str(r[6]) or str(r[3]) in ['물티슈', '패밀리', '스킨케어']]
    f.write(f"\n=== 클레임 전체 ({len(claim_rows)}건) ===\n")
    for r in claim_rows:
        f.write(f"  ID={r[0]} | Tags={r[6]}\n")

print("Written to service_10w2_all.txt")
