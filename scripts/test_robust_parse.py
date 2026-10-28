# -*- coding: utf-8 -*-
import sqlite3
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
cur = conn.cursor()

cur.execute("""
    SELECT u.id, u.description
    FROM userchat u
    LEFT JOIN tag_master tm ON u.tags = tm.full_tag
    WHERE u.week_start_date = '2026-10-15'
      AND (u.journey = '제품사용' OR tm.journey = '제품사용')
      AND u.tag_c != '재통화'
""")
rows = cur.fetchall()

def robust_parse_description(desc):
    if not desc:
        return {}
    
    # 정규식 패턴들
    patterns = {
        'prod': r'[■□\*\-]?\s*(?:상품명|제품명)\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:제조일자|구매처|출고처|주문번호|송장번호|문의내용|안내|조치|고객주소|특이사항|품질발송)|$)',
        'mfg': r'[■□\*\-]?\s*제조일자\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:구매처|출고처|주문번호|송장번호|문의내용|안내|조치|고객주소|특이사항|품질발송)|$)',
        'order_info': r'[■□\*\-]?\s*(?:구매처/주문번호/출고처|구매처/주문번호|구매처)\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:송장번호|문의내용|안내|조치|고객주소|특이사항|품질발송)|$)',
        'inv': r'[■□\*\-]?\s*송장번호\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:문의내용|안내|조치|고객주소|특이사항|품질발송)|$)',
        'issue': r'[■□\*\-]?\s*(?:문의내용|문의|상담내용|인입내용)\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:안내|안내내용|조치|조치사항|고객주소|특이사항|품질발송)|$)',
        'act': r'[■□◇\*\-]?\s*(?:안내내용|안내|조치내용|조치사항|조치|처리내용)\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:고객주소|특이사항|품질발송)|$)',
        'note': r'[■□\*\-]?\s*특이사항\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:품질발송)|$)',
    }
    
    res = {}
    for k, pat in patterns.items():
        m = re.search(pat, desc, re.DOTALL)
        if m:
            val = m.group(1).strip()
            # 줄바꿈 정돈
            val = re.sub(r'[\r\n]+', ' ', val).strip()
            res[k] = val
        else:
            res[k] = ""
    return res

print(f"Testing robust parser on {len(rows)} quality rows:")
for idx, (cid, desc) in enumerate(rows):
    p = robust_parse_description(desc)
    print(f"\n[{idx+1}] ID={cid}")
    print(f"  제품명: {p['prod']}")
    print(f"  제조일자: {p['mfg']}")
    print(f"  문의내용: {p['issue'][:60]}")
    print(f"  안내/조치: {p['act'][:60]}")
