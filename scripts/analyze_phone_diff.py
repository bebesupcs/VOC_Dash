# -*- coding: utf-8 -*-
import sqlite3, os, tempfile
from collections import Counter

db_path = os.path.join(tempfile.gettempdir(), 'channeltalk_voc_local.db')
con = sqlite3.connect(db_path)
cur = con.cursor()

cur.execute("""
    SELECT u.id, u.tags, u.tag_a, u.tag_b, u.tag_c, u.managedAt, u.name,
           s.meet_key, s.is_answered
    FROM userchat u
    LEFT JOIN standard_meet s ON u.id = s.user_chat_id
    WHERE u.week_start_date = '2026-10-15'
      AND u.mediumName = 'phoneNumber'
      AND u.direction = 'INBOUND'
""")
rows = cur.fetchall()

matched = [r for r in rows if r[7] is not None]
not_matched = [r for r in rows if r[7] is None]

with open('phone_diff_analysis.txt', 'w', encoding='utf-8') as f:
    f.write(f"1. 채널톡 엑셀 전화 인바운드 전체: {len(rows)}건\n")
    f.write(f"2. CTI 교환기 통화 원장(standard_meet) 매칭: {len(matched)}건\n")
    f.write(f"3. CTI에 없는 차이 건수: {len(not_matched)}건\n\n")
    
    f.write("=== CTI에 없는 105건의 태그별 상세 분류 ===\n")
    tag_counts = Counter(r[1] for r in not_matched)
    for tag, cnt in tag_counts.most_common():
        f.write(f" - {tag}: {cnt}건\n")
        
    f.write("\n=== CTI에 매칭된 88건의 태그별 상세 분류 ===\n")
    m_counts = Counter(r[1] for r in matched)
    for tag, cnt in m_counts.most_common():
        f.write(f" - {tag}: {cnt}건\n")

print("Analysis written to phone_diff_analysis.txt")
