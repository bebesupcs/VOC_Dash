# -*- coding: utf-8 -*-
"""
ingest_all_latest.py
10월 4주차 및 11월 최신 원본 엑셀(채널톡, 게시판, 풀필먼트) 일괄 DB 적재 및 대시보드 갱신
"""

import os
import sys
import sqlite3
import re
from datetime import datetime, timedelta
import pandas as pd

# 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DB_PATH = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
RAW_DIR = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\raw"

def get_operational_week(dt):
    """목 17:00 ~ 차주 수 17:00 기준 운영 주차 계산"""
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
    
    if tag_a in ['물티슈', '패밀리', '스킨케어', '헬로', '홈'] and tag_b not in ['배송', '시스템']:
        return tag_a, tag_b, tag_c, '품질 클레임', tag_a
    if tag_a in ['클레임(공통)', '공통'] and tag_b in ['제품']:
        return tag_a, tag_b, tag_c, '품질 클레임', '공통'
    if ('클레임' in tag_a and '휴먼에러' in tag_b) or ('서비스' in tag_a or '서비스' in tag_b):
        return tag_a, tag_b, tag_c, '서비스 클레임', '서비스'
    if '클레임' in tag_a and ('배송' in tag_b or '물류' in tag_b):
        return tag_a, tag_b, tag_c, '배송 클레임', '배송'
    return tag_a, tag_b, tag_c, '단순 문의', '단순'

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
        "product_name": prod, "manufacture_date": mfg, "mall_name": mall,
        "order_no": order_no, "shipment_type": ship_type, "invoice_no": inv,
        "customer_issue": issue, "cs_action": action, "special_note": sp_note,
        "quality_send_yn": q_send
    }

def ingest_channeltalk_file(fpath, conn):
    print(f"▶ 채널톡 엑셀 파싱 및 적재: {os.path.basename(fpath)}")
    cur = conn.cursor()
    fname = os.path.basename(fpath)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Manager data
    try:
        df_mgr = pd.read_excel(fpath, sheet_name='Manager data')
        for _, row in df_mgr.iterrows():
            mid = str(row['id'])
            mname = str(row.get('name') or '')
            cur.execute("""
                INSERT INTO manager (id, name, __source_file, __imported_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name, __imported_at=excluded.__imported_at
            """, (mid, mname, fname, now_str))
    except Exception as e:
        print(f"  Manager data load warning: {e}")

    # UserChat
    df = pd.read_excel(fpath, sheet_name='UserChat')
    parsed = df['tags'].apply(classify_tag) if 'tags' in df.columns else [('미분류','','','단순 문의','미분류')]*len(df)
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

    inserted, updated = 0, 0
    for _, row in df.iterrows():
        cid = str(row['id'])
        m_str = str(row['managedAt'])
        name = str(row.get('name') or '')
        desc = str(row.get('description') or '')
        tags = str(row.get('tags') or '')
        direction = str(row.get('direction') or '')
        assignee_id = str(row.get('assigneeId') or '')
        medium_name = str(row.get('mediumName') or '')
        medium_type = str(row.get('mediumType') or '')
        closed_at = str(row.get('closedAt') or '')
        
        tag_a = row['tag_a']
        tag_b = row['tag_b']
        tag_c = row['tag_c']
        w_start = row['week_start_date']
        w_end = row['week_end_date']
        w_key = row['week_key']
        wom = row['week_of_month']
        qtr = row['quarter']
        month = str(w_start)[:7] if w_start else '2026-10'
        rep_date = m_str[:10] if m_str else w_start

        # userchat Upsert
        cur.execute("SELECT id FROM userchat WHERE id = ?", (cid,))
        exists = cur.fetchone()
        if exists:
            cur.execute("""
                UPDATE userchat SET
                    managedAt = ?, name = ?, description = ?, tags = ?,
                    tag_a = ?, tag_b = ?, tag_c = ?, direction = ?, assigneeId = ?,
                    mediumName = ?, mediumType = ?, closedAt = ?, week = ?, week_start_date = ?, week_end_date = ?,
                    week_of_month = ?, quarter = ?, month = ?, report_date = ?,
                    __source_file = ?, __imported_at = ?
                WHERE id = ?
            """, (m_str, name, desc, tags, tag_a, tag_b, tag_c, direction, assignee_id,
                  medium_name, medium_type, closed_at, w_key, w_start, w_end, wom, qtr, month, rep_date,
                  fname, now_str, cid))
            updated += 1
        else:
            cur.execute("""
                INSERT INTO userchat (
                    id, managedAt, name, description, tags,
                    tag_a, tag_b, tag_c, direction, assigneeId,
                    mediumName, mediumType, closedAt, week, week_start_date, week_end_date,
                    week_of_month, quarter, month, report_date,
                    __source_file, __imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cid, m_str, name, desc, tags, tag_a, tag_b, tag_c, direction, assignee_id,
                  medium_name, medium_type, closed_at, w_key, w_start, w_end, wom, qtr, month, rep_date,
                  fname, now_str))
            inserted += 1

        # userchat_description Upsert
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
    print(f"  ✓ {fname}: 신규 삽입 {inserted:,}건, 갱신 {updated:,}건")

def ingest_board_file(conn):
    bpath = os.path.join(RAW_DIR, "게시판 데이터 원본", "게시판_통합운영.xlsx")
    if not os.path.exists(bpath):
        print("게시판 파일이 없습니다.")
        return
    print(f"▶ 게시판 엑셀 파싱 및 적재: {os.path.basename(bpath)}")
    df = pd.read_excel(bpath, sheet_name='게시판 25~', header=1)
    # 첫번째 컬럼(일자) 확인
    date_col = df.columns[0]
    df = df[df[date_col].notna()].copy()
    
    # 몰 컬럼 추출 (일자, 합계 등 제외)
    mall_cols = [c for c in df.columns[2:] if not str(c).startswith("Unnamed") and "합계" not in str(c)]
    
    cur = conn.cursor()
    fname = os.path.basename(bpath)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count_ins = 0

    for _, row in df.iterrows():
        raw_d = str(row[date_col]).strip().replace(". ", "-").replace(".", "-")
        # 2025-01-01 형식 맞춤
        try:
            dt = pd.to_datetime(raw_d)
            d_str = dt.strftime("%Y-%m-%d")
        except Exception:
            continue
            
        w_start, w_end, w_key, wom, qtr = get_operational_week(dt)
        year_str = str(dt.year)
        month_str = dt.strftime("%Y-%m")
        day_name = dt.strftime("%a")

        for mall in mall_cols:
            val = row[mall]
            try:
                cnt = int(float(val)) if pd.notna(val) else 0
            except Exception:
                cnt = 0
            if cnt <= 0:
                continue
            bkey = f"{d_str}_{mall}"
            cur.execute("""
                INSERT INTO board_daily_counts (
                    board_key, date, year, month, week, week_of_month,
                    week_start_date, week_end_date, quarter, day_name,
                    mall_name, board_count, __source_file, __imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(board_key) DO UPDATE SET
                    board_count = excluded.board_count,
                    __imported_at = excluded.__imported_at
            """, (bkey, d_str, year_str, month_str, w_key, wom,
                  w_start, w_end, qtr, day_name, mall, cnt, fname, now_str))
            count_ins += 1
            
    conn.commit()
    print(f"  ✓ 게시판 일별 집계 반영: {count_ins:,}건 처리 완료")

def ingest_fulfillment_file(conn):
    fpath = os.path.join(RAW_DIR, "배송 데이터 원본", "풀필먼트20261104.xlsx")
    if not os.path.exists(fpath):
        return
    print(f"▶ 풀필먼트 배송 클레임 파싱: {os.path.basename(fpath)}")
    df = pd.read_excel(fpath, sheet_name=0)
    cur = conn.cursor()
    fname = os.path.basename(fpath)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count_ins = 0

    for _, row in df.iterrows():
        # CS접수일자 우선
        raw_cs = row.get('CS접수일자') or row.get('CS일자') or row.get('주문일')
        try:
            dt = pd.to_datetime(raw_cs)
            d_str = dt.strftime("%Y-%m-%d")
        except Exception:
            continue
            
        w_start, w_end, w_key, wom, qtr = get_operational_week(dt)
        order_no = str(row.get('주문번호') or '')
        inv_no = str(row.get('원송장번호') or row.get('송장번호') or '')
        ckey = f"FULFILL_{order_no}_{inv_no}_{d_str}" if (order_no or inv_no) else f"FULFILL_{d_str}_{cust_name}_{_}"
        raw_type = str(row.get('사고분류') or row.get('대분류') or '').strip()
        c_clean = raw_type.replace(" ", "")
        if c_clean in ["저단가반송", "저단가", "운임비불만", "운임비", "운임불만"]:
            claim_type = "운임비 불만"
        else:
            claim_type = raw_type or "기타"
        prod_name = str(row.get('품목명') or row.get('상품명') or '')
        c_text = str(row.get('클레임내용') or '')
        r_text = str(row.get('요청사항') or '')
        cust_name = str(row.get('받는사람명') or row.get('받는사람') or '')

        cur.execute("""
            INSERT INTO shipment_claims (
                claim_key, claim_date, claim_year, month, week, week_of_month,
                week_start_date, week_end_date, quarter, vendor_type, vendor_file_type,
                claim_type, customer_name, order_no, original_invoice_no,
                product_name, claim_text, request_text, __source_file, __imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'fulfillment', '네이버풀필먼트', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(claim_key) DO UPDATE SET
                claim_type = excluded.claim_type,
                claim_text = excluded.claim_text,
                original_invoice_no = excluded.original_invoice_no,
                __imported_at = excluded.__imported_at
        """, (ckey, d_str, str(dt.year), dt.strftime("%Y-%m"), w_key, wom,
              w_start, w_end, qtr, claim_type, cust_name, order_no, inv_no,
              prod_name, c_text, r_text, fname, now_str))
        count_ins += 1

    conn.commit()
    print(f"  ✓ 풀필먼트 배송 클레임 반영: {count_ins:,}건 처리 완료")

def main():
    conn = sqlite3.connect(DB_PATH)
    
    # 1. 채널톡 엑셀 202610.xlsx & 1104.xlsx
    for fn in ["202610.xlsx", "1104.xlsx"]:
        fp = os.path.join(RAW_DIR, "채널톡 데이터 원본", fn)
        if os.path.exists(fp):
            ingest_channeltalk_file(fp, conn)
            
    # 2. 게시판 데이터
    ingest_board_file(conn)
    
    # 3. 풀필먼트 배송
    ingest_fulfillment_file(conn)
    
    conn.close()
    print("✨ 모든 최신 원본 엑셀 DB 적재 완료!")

if __name__ == "__main__":
    main()
