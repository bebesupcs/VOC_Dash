# -*- coding: utf-8 -*-
import sqlite3
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
cur = conn.cursor()

# 1. Update userchat.journey from tag_master where missing or null
cur.execute("""
    UPDATE userchat
    SET journey = (
        SELECT tm.journey 
        FROM tag_master tm 
        WHERE tm.full_tag = userchat.tags
    )
    WHERE tags IN (SELECT full_tag FROM tag_master)
      AND (journey IS NULL OR journey = '' OR journey != (SELECT tm.journey FROM tag_master tm WHERE tm.full_tag = userchat.tags))
""")
print(f"Updated userchat.journey from tag_master: {cur.rowcount} rows")

# 2. Robust parse descriptions for W42
def robust_parse_description(desc):
    if not desc or not isinstance(desc, str):
        return {}
    patterns = {
        'product_name': r'[■□\*\-]?\s*(?:상품명|제품명)\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:제조일자|구매처|출고처|주문번호|송장번호|문의내용|안내|조치|고객주소|특이사항|품질발송)|$)',
        'manufacture_date': r'[■□\*\-]?\s*제조일자\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:구매처|출고처|주문번호|송장번호|문의내용|안내|조치|고객주소|특이사항|품질발송)|$)',
        'order_info': r'[■□\*\-]?\s*(?:구매처/주문번호/출고처|구매처/주문번호|구매처)\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:송장번호|문의내용|안내|조치|고객주소|특이사항|품질발송)|$)',
        'invoice_no': r'[■□\*\-]?\s*송장번호\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:문의내용|안내|조치|고객주소|특이사항|품질발송)|$)',
        'customer_issue': r'[■□\*\-]?\s*(?:문의내용|문의|상담내용|인입내용)\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:안내|안내내용|조치|조치사항|고객주소|특이사항|품질발송)|$)',
        'cs_action': r'[■□◇\*\-]?\s*(?:안내내용|안내|조치내용|조치사항|조치|처리내용)\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:고객주소|특이사항|품질발송)|$)',
        'special_note': r'[■□\*\-]?\s*특이사항\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:품질발송)|$)',
    }
    res = {}
    for k, pat in patterns.items():
        m = re.search(pat, desc, re.DOTALL)
        if m:
            val = re.sub(r'[\r\n]+', ' ', m.group(1)).strip()
            res[k] = val
        else:
            res[k] = ""
    order_info = res.get('order_info', '')
    parts = [p.strip() for p in order_info.split("/")] if order_info else []
    res['mall_name'] = parts[0] if len(parts) >= 1 else ""
    res['order_no'] = parts[1] if len(parts) >= 2 else ""
    res['shipment_type'] = parts[2] if len(parts) >= 3 else ""
    return res

cur.execute("SELECT id, description FROM userchat WHERE week_start_date='2026-10-15'")
w42_rows = cur.fetchall()

updated_desc_count = 0
for cid, desc in w42_rows:
    if desc:
        p = robust_parse_description(desc)
        cur.execute("""
            INSERT INTO userchat_description (
                id, product_name, manufacture_date, mall_name, order_no, shipment_type,
                invoice_no, customer_issue, cs_action, special_note, quality_send_yn
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                product_name = excluded.product_name,
                manufacture_date = excluded.manufacture_date,
                mall_name = excluded.mall_name,
                order_no = excluded.order_no,
                shipment_type = excluded.shipment_type,
                invoice_no = excluded.invoice_no,
                customer_issue = excluded.customer_issue,
                cs_action = excluded.cs_action,
                special_note = excluded.special_note
        """, (
            cid, p['product_name'], p['manufacture_date'], p['mall_name'], p['order_no'],
            p['shipment_type'], p['invoice_no'], p['customer_issue'], p['cs_action'],
            p['special_note'], p['special_note'][:1] if p['special_note'] in ('O', 'X') else ''
        ))
        updated_desc_count += 1

conn.commit()
print(f"Updated userchat_description for W42: {updated_desc_count} rows")
conn.close()
