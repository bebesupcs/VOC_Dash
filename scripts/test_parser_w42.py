# -*- coding: utf-8 -*-
import sqlite3, re, sys
sys.stdout.reconfigure(encoding='utf-8')

LOCAL_DB = r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db'
conn = sqlite3.connect(LOCAL_DB)
c = conn.cursor()

def parse_desc(desc):
    if not desc or not isinstance(desc, str):
        return {}
    
    # Normalize brackets/bullets
    clean = desc.replace('□', '\n[항목] ').replace('◇', '\n[항목] ').replace('■', '\n[항목] ')
    
    res = {
        'product_name': '',
        'manufacture_date': '',
        'mall_name': '',
        'order_no': '',
        'shipment_type': '',
        'invoice_no': '',
        'customer_issue': '',
        'cs_action': '',
        'special_note': '',
        'quality_send_yn': ''
    }
    
    # Extract fields with regex
    m_prod = re.search(r'(?:제품명|상품명)\s*[:：]\s*(.*?)(?=\n\[항목\]|\n[□◇■]|$)', clean, re.DOTALL)
    if m_prod: res['product_name'] = re.sub(r'\s+', ' ', m_prod.group(1)).strip()
    
    m_mfg = re.search(r'(?:제조일자|제조일)\s*[:：]\s*(.*?)(?=\n\[항목\]|\n[□◇■]|$)', clean, re.DOTALL)
    if m_mfg: res['manufacture_date'] = re.sub(r'\s+', ' ', m_mfg.group(1)).strip()
    
    m_order = re.search(r'(?:구매처/주문번호/출고처|구매처/주문번호|구매처)\s*[:：]\s*(.*?)(?=\n\[항목\]|\n[□◇■]|$)', clean, re.DOTALL)
    if m_order:
        val = re.sub(r'\s+', ' ', m_order.group(1)).strip()
        parts = [p.strip() for p in val.split('/')]
        if len(parts) >= 1: res['mall_name'] = parts[0]
        if len(parts) >= 2: res['order_no'] = parts[1]
        if len(parts) >= 3: res['shipment_type'] = parts[2]
        
    m_inv = re.search(r'(?:송장번호|운송장번호)\s*[:：]\s*(.*?)(?=\n\[항목\]|\n[□◇■]|$)', clean, re.DOTALL)
    if m_inv: res['invoice_no'] = re.sub(r'\s+', ' ', m_inv.group(1)).strip()
    
    m_issue = re.search(r'(?:문의내용|불만내용|인입내용|고객문의)\s*[:：]\s*(.*?)(?=\n\[항목\]|\n[□◇■]|$)', clean, re.DOTALL)
    if m_issue: res['customer_issue'] = re.sub(r'\s+', ' ', m_issue.group(1)).strip()
    
    m_act = re.search(r'(?:안내내용|안내사항|조치내용|조치사항|안내|조치|처리내용)\s*[:：]\s*(.*?)(?=\n\[항목\]|\n[□◇■]|$)', clean, re.DOTALL)
    if m_act: res['cs_action'] = re.sub(r'\s+', ' ', m_act.group(1)).strip()
    
    m_note = re.search(r'(?:특이사항)\s*[:：]\s*(.*?)(?=\n\[항목\]|\n[□◇■]|$)', clean, re.DOTALL)
    if m_note:
        res['special_note'] = re.sub(r'\s+', ' ', m_note.group(1)).strip()
        if 'O' in res['special_note'].upper(): res['quality_send_yn'] = 'O'
        elif 'X' in res['special_note'].upper(): res['quality_send_yn'] = 'X'
        
    return res

# Test on 전광석, 정은주, 김하윤
c.execute("SELECT id, name, description FROM userchat WHERE id IN ('6ad80f5c4a2b3ad755a2', '6ad6bf9ee0de5e900620', '6ad6c9a2465debbbfa88')")
for cid, name, desc in c.fetchall():
    p = parse_desc(desc)
    print(f"\n[{name}] {cid}")
    print("  Prod:", p['product_name'])
    print("  Mfg:", p['manufacture_date'])
    print("  Mall:", p['mall_name'])
    print("  Issue:", p['customer_issue'][:60])
    print("  Action:", p['cs_action'][:60])
    print("  SendYN:", p['quality_send_yn'])

conn.close()
