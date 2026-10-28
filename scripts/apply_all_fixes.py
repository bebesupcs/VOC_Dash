# -*- coding: utf-8 -*-
import sqlite3, re, sys, os, time
sys.stdout.reconfigure(encoding='utf-8')

LOCAL_DB = r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db'
X_DB = r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db'

def parse_desc(desc):
    if not desc or not isinstance(desc, str):
        return {}
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

for target_db in [LOCAL_DB]:
    if not os.path.exists(target_db):
        continue
    print(f"\nProcessing DB: {target_db}...")
    conn = sqlite3.connect(target_db)
    cur = conn.cursor()
    
    # Create indexes for speed
    cur.execute("CREATE INDEX IF NOT EXISTS idx_userchat_id ON userchat(id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_userchat_desc_id ON userchat_description(id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_userchat_tags ON userchat(tags)")
    conn.commit()

    # 1. Update tag_master and userchat journey
    cur.execute("""
        UPDATE userchat
        SET journey = '제품사용'
        WHERE tags = '패밀리/포장/실링불량'
    """)
    print(f"  Updated userchat journey for 패밀리/포장/실링불량: {cur.rowcount} rows")
    
    # Update tag_master
    cur.execute("""
        INSERT OR REPLACE INTO tag_master (channelId, full_tag, journey, tag_a, tag_b, tag_c, __source_file)
        VALUES ('2626563', '패밀리/포장/실링불량', '제품사용', '패밀리', '포장', '실링불량', 'GoogleSheet_TagMaster')
    """)
    conn.commit()
    print("  Ensured tag_master has 패밀리/포장/실링불량")

    # 2. Get existing parsed IDs
    cur.execute("SELECT id FROM userchat_description WHERE customer_issue IS NOT NULL AND customer_issue != '' AND product_name IS NOT NULL AND product_name != ''")
    already_parsed_ids = set(r[0] for r in cur.fetchall())
    print(f"  Already parsed in userchat_description: {len(already_parsed_ids)}")

    # 3. Find chats with raw description that need parsing
    cur.execute("SELECT id, description FROM userchat WHERE description IS NOT NULL AND LENGTH(description) > 10")
    all_raw = cur.fetchall()
    needs_parsing = [(cid, desc) for cid, desc in all_raw if cid not in already_parsed_ids]
    print(f"  Needs parsing: {len(needs_parsing)} chats")
    
    batch = []
    for cid, desc in needs_parsing:
        p = parse_desc(desc)
        if any(p.values()):
            batch.append((
                cid, p['product_name'], p['manufacture_date'], p['mall_name'], p['order_no'],
                p['shipment_type'], p['invoice_no'], p['customer_issue'], p['cs_action'],
                p['special_note'], p['quality_send_yn']
            ))
            
    cur.executemany("""
        INSERT INTO userchat_description (
            id, product_name, manufacture_date, mall_name, order_no,
            shipment_type, invoice_no, customer_issue, cs_action,
            special_note, quality_send_yn
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
            special_note = excluded.special_note,
            quality_send_yn = excluded.quality_send_yn
    """, batch)
    conn.commit()
    print(f"  Successfully inserted/updated {len(batch)} rows into userchat_description!")
    conn.close()

print("\nAll DB updates complete!")
