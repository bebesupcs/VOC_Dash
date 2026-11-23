# -*- coding: utf-8 -*-
"""
ingest_shipments_all.py
2026년 배송 클레임 데이터(CJ대한통운 암호화 엑셀 + 풀필먼트 엑셀) 초고속 DB 적재
"""

import io
import os
import sys
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import openpyxl
import msoffcrypto

# 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DB_PATH = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
RAW_DIR = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\raw\배송 데이터 원본"

def get_operational_week(dt):
    """목 17:00 ~ 차주 수 17:00 기준 운영 주차 계산 (날짜만 있는 경우 12:00 기준)"""
    if pd.isna(dt):
        return None, None, None, None, None, None, None
    if isinstance(dt, str):
        try:
            dt = pd.to_datetime(dt)
        except Exception:
            return None, None, None, None, None, None, None
            
    # 배송 데이터는 날짜(YYYY-MM-DD) 단위이므로 목 00:00 ~ 수 23:59가 하나의 운영주차
    days_since_thu = (dt.weekday() - 3) % 7
    week_start = (dt - timedelta(days=days_since_thu)).date()
    week_end = week_start + timedelta(days=6)
    
    iso_year, iso_week, _ = week_start.isocalendar()
    week_key = f"{iso_year}-W{iso_week:02d}"
    
    # 평일 다수결 월 계산 (목, 금, 월, 화, 수)
    thu = week_start
    fri = thu + timedelta(days=1)
    mon = thu + timedelta(days=4)
    tue = thu + timedelta(days=5)
    wed = thu + timedelta(days=6)
    weekdays_m = [d.month for d in [thu, fri, mon, tue, wed]]
    rep_month = max(set(weekdays_m), key=weekdays_m.count)
    rep_year = thu.year if rep_month >= thu.month else thu.year + 1
    
    # 해당 월의 첫 번째 목요일 계산
    first_day_of_m = datetime(rep_year, rep_month, 1).date()
    first_thu_offset = (3 - first_day_of_m.weekday()) % 7
    first_thu = first_day_of_m + timedelta(days=first_thu_offset)
    if week_start < first_thu:
        week_num = 1
    else:
        week_num = ((week_start - first_thu).days // 7) + 1
        
    wom = f"{rep_month}월 {week_num}주"
    quarter = f"Q{(rep_month - 1) // 3 + 1}"
    month_str = f"{rep_year}-{rep_month:02d}"
    
    return str(week_start), str(week_end), week_key, wom, quarter, month_str, str(rep_year)

def normalize_claim_type(raw_val):
    if not raw_val or pd.isna(raw_val):
        return "기타"
    s = str(raw_val).strip()
    s_clean = s.replace(" ", "")
    if s_clean in ["저단가반송", "저단가", "운임비불만", "운임비", "운임불만"]:
        return "운임비 불만"
    return s

def ingest_cj_file(conn, fpath):
    fname = os.path.basename(fpath)
    print(f"\n▶ CJ대한통운 파일 복호화 및 적재: {fname}")
    
    with open(fpath, "rb") as f:
        office_file = msoffcrypto.OfficeFile(f)
        office_file.load_key(password="1111")
        dec = io.BytesIO()
        office_file.decrypt(dec)
        
    wb = openpyxl.load_workbook(dec, read_only=True, data_only=True)
    if "CS일지-cJ" not in wb.sheetnames:
        print(f"  ⚠ 'CS일지-cJ' 시트 없음: {wb.sheetnames}")
        return 0, 0
        
    ws = wb["CS일지-cJ"]
    
    cur = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ins_cnt = 0
    upd_cnt = 0
    
    # 헤더 인덱스 기본값
    idx_date = 0
    idx_claim_type = 3
    idx_cust = 4
    idx_phone = 5
    idx_addr = 6
    idx_inv = 7
    idx_resend_inv = 8
    idx_return_inv = 9
    idx_qty = 10
    idx_prod = 12
    idx_wrong_prod = 13
    idx_resend_prod = 14
    idx_claim_text = 15
    idx_action_text = 16
    idx_coldchain_note = 17
    
    empty_streak = 0
    header_found = False
    
    for row_idx, r in enumerate(ws.iter_rows(values_only=True)):
        if not r or r[0] is None:
            if header_found:
                empty_streak += 1
                if empty_streak > 20:
                    break
            continue
            
        # 헤더 감지
        first_val = str(r[0]).strip()
        if not header_found:
            if "날짜" in [str(c).strip() for c in r if c is not None]:
                header = [str(c).strip() if c is not None else "" for c in r]
                col_map = {name: idx for idx, name in enumerate(header) if name}
                idx_date = col_map.get("날짜", idx_date)
                idx_claim_type = col_map.get("클레임분류", idx_claim_type)
                idx_cust = col_map.get("고객명", idx_cust)
                idx_phone = col_map.get("연락처", idx_phone)
                idx_addr = col_map.get("주소", idx_addr)
                idx_inv = col_map.get("원송장", idx_inv)
                idx_resend_inv = col_map.get("재출고송장", idx_resend_inv)
                idx_return_inv = col_map.get("반송장", idx_return_inv)
                idx_qty = col_map.get("파손수량", idx_qty)
                idx_prod = col_map.get("상품명", idx_prod)
                idx_wrong_prod = col_map.get("오발송상품명", idx_wrong_prod)
                idx_resend_prod = col_map.get("재출고상품명", idx_resend_prod)
                idx_claim_text = col_map.get("클레임내용", idx_claim_text)
                idx_action_text = col_map.get("처리결과", idx_action_text)
                idx_coldchain_note = col_map.get("한국초저온 특이사항", idx_coldchain_note)
                header_found = True
            continue
            
        empty_streak = 0
        raw_date = r[idx_date]
        try:
            dt = pd.to_datetime(raw_date)
            d_str = dt.strftime("%Y-%m-%d")
        except Exception:
            continue
            
        w_start, w_end, w_key, wom, qtr, month_str, year_str = get_operational_week(dt)
        if not w_key:
            continue
            
        inv_no = str(r[idx_inv] or "").strip()
        cust_name = str(r[idx_cust] or "").strip()
        claim_type = normalize_claim_type(r[idx_claim_type])
        
        # 키 생성
        if inv_no:
            ckey = f"2026_{inv_no}"
        else:
            ckey = f"2026_CJ_{d_str}_{cust_name}_{row_idx}"
            
        prod_name = str(r[idx_prod] or "").strip()
        wrong_prod = str(r[idx_wrong_prod] or "").strip()
        resend_prod = str(r[idx_resend_prod] or "").strip()
        resend_inv = str(r[idx_resend_inv] or "").strip()
        return_inv = str(r[idx_return_inv] or "").strip()
        claim_text = str(r[idx_claim_text] or "").strip()
        action_text = str(r[idx_action_text] or "").strip()
        coldchain_note = str(r[idx_coldchain_note] or "").strip()
        phone = str(r[idx_phone] or "").strip()
        
        qty_val = r[idx_qty]
        try:
            qty = float(qty_val) if qty_val is not None and str(qty_val).strip() != "" else 0.0
        except Exception:
            qty = 0.0
            
        cur.execute("""
            INSERT INTO shipment_claims (
                claim_key, claim_date, claim_year, month, week_num, week,
                week_of_month, week_start_date, week_end_date, quarter,
                vendor_type, vendor_file_type, claim_type, customer_name,
                order_date, order_no, original_invoice_no, resend_invoice_no, return_invoice_no,
                product_name, wrong_product_name, resend_product_name, damaged_qty,
                claim_text, request_text, action_text, coldchain_note, cs_note,
                __source_file, __source_path, __source_sheet, __source_row, __imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'coldchain', 'accident', ?, ?, '', '', ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?, ?, 'CS일지-cJ', ?, ?)
            ON CONFLICT(claim_key) DO UPDATE SET
                claim_date = excluded.claim_date,
                week = excluded.week,
                week_of_month = excluded.week_of_month,
                week_start_date = excluded.week_start_date,
                week_end_date = excluded.week_end_date,
                claim_type = excluded.claim_type,
                product_name = excluded.product_name,
                claim_text = excluded.claim_text,
                action_text = excluded.action_text,
                damaged_qty = excluded.damaged_qty,
                __source_file = excluded.__source_file,
                __imported_at = excluded.__imported_at
        """, (
            ckey, d_str, year_str, month_str, int(w_key.split("-W")[1]), w_key,
            wom, w_start, w_end, qtr,
            claim_type, cust_name,
            inv_no, resend_inv, return_inv,
            prod_name, wrong_prod, resend_prod, qty,
            claim_text, action_text, coldchain_note, phone,
            fname, fpath, row_idx, now_str
        ))
        if cur.rowcount == 1:
            ins_cnt += 1
        else:
            upd_cnt += 1
            
    conn.commit()
    print(f"  ✓ {fname}: 신규 {ins_cnt}건, 갱신 {upd_cnt}건 완료")
    return ins_cnt, upd_cnt

def ingest_fulfillment_file(conn, fpath):
    fname = os.path.basename(fpath)
    print(f"\n▶ 풀필먼트 파일 적재: {fname}")
    df = pd.read_excel(fpath, sheet_name=0)
    
    cur = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ins_cnt = 0
    upd_cnt = 0
    
    for row_idx, row in df.iterrows():
        # 접수일자 우선
        raw_cs = row.get("CS접수일자") or row.get("CS일자") or row.get("주문일")
        if pd.isna(raw_cs):
            continue
        try:
            dt = pd.to_datetime(raw_cs)
            d_str = dt.strftime("%Y-%m-%d")
        except Exception:
            continue
            
        w_start, w_end, w_key, wom, qtr, month_str, year_str = get_operational_week(dt)
        if not w_key:
            continue
            
        order_no = str(row.get("주문번호") or "").strip()
        inv_no = str(row.get("원송장번호") or "").strip()
        cust_name = str(row.get("받는사람명") or row.get("받는사람") or "").strip()
        claim_type = normalize_claim_type(row.get("사고분류") or row.get("대분류"))
        prod_name = str(row.get("품목명") or row.get("상품명") or "").strip()
        claim_text = str(row.get("클레임내용") or "").strip()
        req_text = str(row.get("요청사항") or "").strip()
        resend_inv = str(row.get("재출고송장") or "").strip()
        return_inv = str(row.get("반송장번호") or row.get("반송장") or "").strip()
        
        raw_order_d = row.get("주문일")
        try:
            order_d_str = pd.to_datetime(raw_order_d).strftime("%Y-%m-%d") if pd.notna(raw_order_d) else ""
        except Exception:
            order_d_str = ""
            
        ckey = f"FULFILL_{order_no}_{inv_no}_{d_str}" if (order_no or inv_no) else f"FULFILL_{d_str}_{cust_name}_{row_idx}"
        
        cur.execute("""
            INSERT INTO shipment_claims (
                claim_key, claim_date, claim_year, month, week_num, week,
                week_of_month, week_start_date, week_end_date, quarter,
                vendor_type, vendor_file_type, claim_type, customer_name,
                order_date, order_no, original_invoice_no, resend_invoice_no, return_invoice_no,
                product_name, claim_text, request_text, action_text,
                __source_file, __source_path, __source_sheet, __source_row, __imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'fulfillment', 'claim', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '교환/보상 처리', ?, ?, 'Sheet1', ?, ?)
            ON CONFLICT(claim_key) DO UPDATE SET
                claim_date = excluded.claim_date,
                week = excluded.week,
                week_of_month = excluded.week_of_month,
                week_start_date = excluded.week_start_date,
                week_end_date = excluded.week_end_date,
                claim_type = excluded.claim_type,
                customer_name = excluded.customer_name,
                product_name = excluded.product_name,
                claim_text = excluded.claim_text,
                request_text = excluded.request_text,
                __source_file = excluded.__source_file,
                __imported_at = excluded.__imported_at
        """, (
            ckey, d_str, year_str, month_str, int(w_key.split("-W")[1]), w_key,
            wom, w_start, w_end, qtr,
            claim_type, cust_name, order_d_str, order_no, inv_no, resend_inv, return_inv,
            prod_name, claim_text, req_text,
            fname, fpath, row_idx, now_str
        ))
        if cur.rowcount == 1:
            ins_cnt += 1
        else:
            upd_cnt += 1
            
    conn.commit()
    print(f"  ✓ {fname}: 신규 {ins_cnt}건, 갱신 {upd_cnt}건 완료")
    return ins_cnt, upd_cnt

def main():
    conn = sqlite3.connect(DB_PATH)
    
    # 1. CJ 파일들 처리
    cj_files = [
        os.path.join(RAW_DIR, "CJ대한통운 CS일지_0930.xlsx"),
        os.path.join(RAW_DIR, "CJ대한통운 CS일지_1030.xlsx"),
        os.path.join(RAW_DIR, "CJ대한통운 CS일지_1102.xlsx"),
    ]
    for cj_f in cj_files:
        if os.path.exists(cj_f):
            ingest_cj_file(conn, cj_f)
            
    # 2. 풀필먼트 파일 처리
    fulfill_f = os.path.join(RAW_DIR, "풀필먼트20261104.xlsx")
    if os.path.exists(fulfill_f):
        ingest_fulfillment_file(conn, fulfill_f)
        
    conn.close()
    print("\n✨ 모든 배송 클레임 데이터 DB 적재 완료!")

if __name__ == "__main__":
    main()
