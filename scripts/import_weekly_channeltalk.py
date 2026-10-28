# -*- coding: utf-8 -*-
"""
import_weekly_channeltalk.py
채널톡 다운로드 주간 VOC 원본 엑셀을
1. 목 17:00 ~ 차주 수 17:00 기준 주차 산정
2. 전화(phoneNumber: IN 192 / OUT 76) / 채팅(빈칸+appNaverTalk: IN 142 / OUT 78) 채널 분류
3. 품질/서비스 클레임 및 단순 분류
4. DB(userchat, userchat_description) 증분 동기화
"""

import os
import glob
import re
import sqlite3
import tempfile
from datetime import datetime, timedelta
import pandas as pd

def extract_block(text, label, all_labels):
    if not isinstance(text, str) or label not in text:
        return ""
    start = text.find(label) + len(label)
    sub = text[start:]
    min_end = len(sub)
    for l in all_labels:
        if l == label:
            continue
        idx = sub.find(l)
        if idx != -1 and idx < min_end:
            min_end = idx
    return sub[:min_end].strip()

def parse_description(description):
    if not isinstance(description, str) or not description.strip():
        return {}
    labels = [
        "■ 상품명 :", "■ 제품명 :", "■ 제조일자 :", "■ 구매처/주문번호/출고처 :",
        "■ 구매처/주문번호 :", "■ 송장번호 :", "■ 문의내용 :", "■ 안내내용 :",
        "■ 고객주소 :", "■ 특이사항 :", "■ 품질발송 :"
    ]
    prod = extract_block(description, "■ 상품명 :", labels) or extract_block(description, "■ 제품명 :", labels)
    mfg = extract_block(description, "■ 제조일자 :", labels)
    
    order_info = extract_block(description, "■ 구매처/주문번호/출고처 :", labels) or extract_block(description, "■ 구매처/주문번호 :", labels)
    parts = [p.strip() for p in order_info.split("/")] if order_info else []
    mall = parts[0] if len(parts) >= 1 else ""
    order_no = parts[1] if len(parts) >= 2 else ""
    ship_type = parts[2] if len(parts) >= 3 else ""
    
    inv = extract_block(description, "■ 송장번호 :", labels)
    issue = extract_block(description, "■ 문의내용 :", labels)
    action = extract_block(description, "■ 안내내용 :", labels)
    sp_note = extract_block(description, "■ 특이사항 :", labels)
    q_send = extract_block(description, "■ 품질발송 :", labels)
    if not q_send and sp_note:
        c = sp_note.strip().upper()[:1]
        if c in ("O", "X"):
            q_send = c
            
    return {
        "product_name": prod,
        "manufacture_date": mfg,
        "mall_name": mall,
        "order_no": order_no,
        "shipment_type": ship_type,
        "invoice_no": inv,
        "customer_issue": issue,
        "cs_action": action,
        "special_note": sp_note,
        "quality_send_yn": q_send
    }

def get_operational_week(dt):
    """목 17:00 ~ 수 17:00 기준 운영 주차 계산"""
    if pd.isna(dt):
        return None, None, None, None, None
    if isinstance(dt, str):
        try:
            dt = pd.to_datetime(dt)
        except Exception:
            return None, None, None, None, None
            
    dt_adj = dt - timedelta(hours=17)
    days_since_thu = (dt_adj.weekday() - 3) % 7
    week_start = (dt_adj - timedelta(days=days_since_thu)).date()
    week_end = week_start + timedelta(days=6)
    
    iso_year, iso_week, _ = week_start.isocalendar()
    week_key = f"{iso_year}-W{iso_week:02d}"
    
    thu = week_start
    fri = thu + timedelta(days=1)
    mon = thu + timedelta(days=4)
    tue = thu + timedelta(days=5)
    wed = thu + timedelta(days=6)
    weekdays_m = [d.month for d in [thu, fri, mon, tue, wed]]
    rep_month = max(set(weekdays_m), key=weekdays_m.count)
    rep_year = thu.year if rep_month >= thu.month else thu.year + 1
    
    first_day_of_m = datetime(rep_year, rep_month, 1).date()
    first_thu_offset = (3 - first_day_of_m.weekday()) % 7
    first_thu = first_day_of_m + timedelta(days=first_thu_offset)
    if week_start < first_thu:
        week_num = 1
    else:
        week_num = ((week_start - first_thu).days // 7) + 1
        
    wom = f"{rep_month}월 {week_num}주"
    quarter = f"{(rep_month - 1) // 3 + 1}분기"
    
    return str(week_start), str(week_end), week_key, wom, quarter

def classify_tag(tag_str):
    if not isinstance(tag_str, str) or not tag_str.strip():
        return '미분류', '', '', '단순 문의', '미분류'
    parts = [p.strip() for p in tag_str.split('/')]
    tag_a = parts[0] if len(parts) > 0 else ''
    tag_b = parts[1] if len(parts) > 1 else ''
    tag_c = parts[2] if len(parts) > 2 else ''
    
    # 1. 품질 클레임
    if tag_a in ['물티슈', '패밀리', '스킨케어', '헬로', '홈'] and tag_b not in ['배송', '시스템']:
        return tag_a, tag_b, tag_c, '품질 클레임', tag_a
    if tag_a in ['클레임(공통)', '공통'] and tag_b in ['제품']:
        return tag_a, tag_b, tag_c, '품질 클레임', '공통'
        
    # 2. 서비스 클레임
    if ('클레임' in tag_a and '휴먼에러' in tag_b) or ('서비스' in tag_a or '서비스' in tag_b):
        return tag_a, tag_b, tag_c, '서비스 클레임', '서비스'
        
    # 3. 배송 클레임
    if '클레임' in tag_a and ('배송' in tag_b or '물류' in tag_b):
        return tag_a, tag_b, tag_c, '배송 클레임', '배송'
        
    # 4. 단순 문의
    return tag_a, tag_b, tag_c, '단순 문의', '단순'

def sync_to_db(df, fpath, db_path):
    if not os.path.exists(db_path):
        print(f"DB not found: {db_path}")
        return 0, 0
        
    fname = os.path.basename(fpath)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    tbl = cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='userchat'").fetchone()
    if not tbl:
        conn.close()
        return 0, 0
        
    inserted = 0
    updated = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for _, row in df.iterrows():
        cid = str(row['id'])
        m_dt = row['managedAt_dt']
        m_str = str(row['managedAt'])
        name = str(row.get('name') or '')
        desc = str(row.get('description') or '')
        tags = str(row.get('tags') or '')
        direction = str(row.get('direction') or '')
        assignee_id = str(row.get('assigneeId') or '')
        medium_name = str(row.get('mediumName') or '')
        
        tag_a = row['tag_a']
        tag_b = row['tag_b']
        tag_c = row['tag_c']
        w_start = row['week_start_date']
        w_end = row['week_end_date']
        w_key = row['week_key']
        wom = row['week_of_month']
        qtr = row['quarter']
        year = str(w_start)[:4] if w_start else '2026'
        month = str(w_start)[:7] if w_start else '2026-10'
        rep_date = m_str[:10] if m_str else w_start
        
        # 1. userchat Upsert
        cur.execute("SELECT id FROM userchat WHERE id = ?", (cid,))
        exists = cur.fetchone()
        
        if exists:
            cur.execute("""
                UPDATE userchat SET
                    managedAt = ?, name = ?, description = ?, tags = ?,
                    tag_a = ?, tag_b = ?, tag_c = ?, direction = ?, assigneeId = ?,
                    mediumName = ?, week = ?, week_start_date = ?, week_end_date = ?,
                    week_of_month = ?, quarter = ?, month = ?, report_date = ?,
                    __source_file = ?, __imported_at = ?
                WHERE id = ?
            """, (m_str, name, desc, tags, tag_a, tag_b, tag_c, direction, assignee_id,
                  medium_name, w_key, w_start, w_end, wom, qtr, month, rep_date,
                  fname, now_str, cid))
            updated += 1
        else:
            cur.execute("""
                INSERT INTO userchat (
                    id, managedAt, name, description, tags,
                    tag_a, tag_b, tag_c, direction, assigneeId,
                    mediumName, week, week_start_date, week_end_date,
                    week_of_month, quarter, month, report_date,
                    __source_file, __imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cid, m_str, name, desc, tags, tag_a, tag_b, tag_c, direction, assignee_id,
                  medium_name, w_key, w_start, w_end, wom, qtr, month, rep_date,
                  fname, now_str))
            inserted += 1
            
        # 2. userchat_description Upsert
        desc_info = parse_description(desc)
        if desc_info:
            cur.execute("SELECT id FROM userchat_description WHERE id = ?", (cid,))
            d_exists = cur.fetchone()
            if d_exists:
                cur.execute("""
                    UPDATE userchat_description SET
                        product_name = ?, manufacture_date = ?, mall_name = ?,
                        order_no = ?, shipment_type = ?, invoice_no = ?,
                        customer_issue = ?, cs_action = ?, special_note = ?,
                        quality_send_yn = ?, __source_file = ?, __imported_at = ?
                    WHERE id = ?
                """, (desc_info['product_name'], desc_info['manufacture_date'], desc_info['mall_name'],
                      desc_info['order_no'], desc_info['shipment_type'], desc_info['invoice_no'],
                      desc_info['customer_issue'], desc_info['cs_action'], desc_info['special_note'],
                      desc_info['quality_send_yn'], fname, now_str, cid))
            else:
                cur.execute("""
                    INSERT INTO userchat_description (
                        id, product_name, manufacture_date, mall_name,
                        order_no, shipment_type, invoice_no,
                        customer_issue, cs_action, special_note,
                        quality_send_yn, __source_file, __imported_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (cid, desc_info['product_name'], desc_info['manufacture_date'], desc_info['mall_name'],
                      desc_info['order_no'], desc_info['shipment_type'], desc_info['invoice_no'],
                      desc_info['customer_issue'], desc_info['cs_action'], desc_info['special_note'],
                      desc_info['quality_send_yn'], fname, now_str))
                      
    conn.commit()
    conn.close()
    return inserted, updated

def run():
    files = glob.glob(r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\**\*2026-10-22*.xlsx", recursive=True)
    if not files:
        print("10-22 파일을 찾을 수 없습니다.")
        return
        
    fpath = files[0]
    print(f"Loading {fpath}...")
    df = pd.read_excel(fpath)
    
    parsed = df['tags'].apply(classify_tag)
    df['tag_a'] = [p[0] for p in parsed]
    df['tag_b'] = [p[1] for p in parsed]
    df['tag_c'] = [p[2] for p in parsed]
    df['voc_type'] = [p[3] for p in parsed]
    df['brand'] = [p[4] for p in parsed]
    
    df['managedAt_dt'] = pd.to_datetime(df['managedAt'])
    weeks_info = df['managedAt_dt'].apply(get_operational_week)
    df['week_start_date'] = [w[0] for w in weeks_info]
    df['week_end_date'] = [w[1] for w in weeks_info]
    df['week_key'] = [w[2] for w in weeks_info]
    df['week_of_month'] = [w[3] for w in weeks_info]
    df['quarter'] = [w[4] for w in weeks_info]
    
    local_db = os.path.join(tempfile.gettempdir(), 'channeltalk_voc_local.db')
    ins_l, upd_l = sync_to_db(df, fpath, local_db)
    print(f"Local DB sync: inserted {ins_l}, updated {upd_l}")
    
    x_db = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
    if os.path.exists(x_db):
        try:
            ins_x, upd_x = sync_to_db(df, fpath, x_db)
            print(f"X drive DB sync: inserted {ins_x}, updated {upd_x}")
        except Exception as e:
            print(f"X drive DB sync failed (locked?): {e}")

if __name__ == "__main__":
    run()
