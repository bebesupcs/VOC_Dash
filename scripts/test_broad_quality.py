# -*- coding: utf-8 -*-
import sqlite3
import os
import tempfile

db_path = os.path.join(tempfile.gettempdir(), 'channeltalk_voc_local.db')
con = sqlite3.connect(db_path)
cur = con.cursor()

# Query with broadened quality logic
cur.execute("""
    SELECT 
        u.id, u.name, u.managedAt, u.tag_a, u.tag_b, u.tag_c,
        d.product_name, d.customer_issue, d.quality_send_yn, u.journey
    FROM userchat u
    LEFT JOIN userchat_description d ON u.id = d.id
    WHERE date(u.managedAt) BETWEEN '2026-10-15' AND '2026-10-21'
      AND (
        -- Standard tag-based quality
        (
            (u.tag_a IN ('물티슈', '스킨케어', '패밀리', '헬로', '홈') AND u.tag_b NOT IN ('배송', '시스템'))
            OR (u.tag_a IN ('클레임(공통)', '공통') AND u.tag_b = '제품')
            OR (u.tag_a LIKE '%단순%' AND u.tag_b IN ('품질불만', '이취', '용액', '피부이상', '원단면', '원단(공정)이물', '포장공정'))
        )
        OR
        -- Issue text / quality compensation based (for phone CTI or un-tagged chats)
        (
            u.tag_b NOT IN ('배송', '시스템')
            AND (
                d.quality_send_yn IN ('O', 'X')
                OR d.customer_issue LIKE '%이물%'
                OR d.customer_issue LIKE '%수분%'
                OR d.customer_issue LIKE '%원사%'
                OR d.customer_issue LIKE '%보풀%'
                OR d.customer_issue LIKE '%캡%'
                OR d.customer_issue LIKE '%누액%'
                OR d.customer_issue LIKE '%찢김%'
                OR d.customer_issue LIKE '%절단%'
                OR d.customer_issue LIKE '%냄새%'
                OR d.customer_issue LIKE '%거품%'
            )
        )
      )
      AND NOT (u.tag_a LIKE '%클레임(공통)%' AND u.tag_b LIKE '%휴먼에러%') -- exclude service claims
    ORDER BY u.managedAt ASC
""")

rows = cur.fetchall()
print(f"Total Quality Claims found: {len(rows)}")
for i, r in enumerate(rows, 1):
    print(f"{i:2d}. {r[1]} | {r[2][:10]} | {r[3]}/{r[4]}/{r[5]} | {(r[7] or '')[:30]}")
