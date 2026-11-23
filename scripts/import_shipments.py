# -*- coding: utf-8 -*-
import argparse
from collections import Counter
import hashlib
import io
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

try:
    import msoffcrypto
except ImportError:
    msoffcrypto = None

EXCEL_PASSWORDS = ["1111", "qpqptnv1"]

HEADER_KEYWORDS = [
    "접수날짜", "접수일자", "CS접수일자", "원송장", "원송장번호", "송장번호",
    "주문일", "주문번호", "클레임분류", "사고분류", "클레임내용",
    "처리결과", "요청사항", "상품명", "품목명", "제품명"
]

def clean(v):
    if v is None or pd.isna(v):
        return ""
    t = str(v).strip()
    return "" if t.lower() == "nan" else t

def norm_col(c):
    return re.sub(r"\s+", "", str(c).strip()).replace("\n", "").replace("\r", "")

def clean_id(v):
    t = clean(v)
    if not t:
        return ""
    if re.fullmatch(r"\d+\.0", t):
        t = t[:-2]
    return t.replace("-", "").replace(" ", "")

def clean_num(v):
    t = clean(v).replace(",", "")
    if not t:
        return None
    try:
        return float(t)
    except Exception:
        return None

def norm_date(v):
    t = clean(v)
    if not t:
        return ""
    try:
        dt = pd.to_datetime(v, errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return t

def first_col(df, names):
    m = {norm_col(c): c for c in df.columns}
    for n in names:
        k = norm_col(n)
        if k in m:
            return m[k]
    return None

def val(row, col):
    return "" if not col or col not in row.index else row[col]

def mtime(path):
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")

def now():
    return datetime.now().isoformat(timespec="seconds")

def row_hash(d):
    s = "||".join(f"{k}={'' if d[k] is None else str(d[k])}" for k in sorted(d))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def engine(path):
    if path.suffix.lower() == ".xlsb":
        return "pyxlsb"
    if path.suffix.lower() == ".xls":
        return "xlrd"
    return "openpyxl"

def load_excel(path):
    try:
        pd.ExcelFile(path, engine=engine(path))
        return path, engine(path)
    except Exception as e:
        msg = str(e)

        if path.suffix.lower() == ".xlsx":
            try:
                pd.ExcelFile(path, engine="xlrd")
                return path, "xlrd"
            except Exception:
                pass

        encrypted = "File is not a zip file" in msg or "encrypted" in msg.lower() or "password" in msg.lower()
        if not encrypted:
            raise

    if msoffcrypto is None:
        raise RuntimeError("암호화 엑셀 읽기 필요 패키지: pip install msoffcrypto-tool")

    last = None
    for pwd in EXCEL_PASSWORDS:
        try:
            bio = io.BytesIO()
            with open(path, "rb") as f:
                of = msoffcrypto.OfficeFile(f)
                of.load_key(password=pwd)
                of.decrypt(bio)
            bio.seek(0)

            try:
                pd.ExcelFile(bio, engine="openpyxl")
                bio.seek(0)
                return bio, "openpyxl"
            except Exception:
                bio.seek(0)
                return bio, "xlrd"
        except Exception as e:
            last = e

    raise RuntimeError(f"엑셀 비밀번호 해제 실패: {path} / {last}")

def excel_file(path):
    src, eng = load_excel(path)
    return pd.ExcelFile(src, engine=eng), src, eng

def find_header(raw):
    best_i, best_score = 0, 0
    for i in range(min(40, len(raw))):
        row_text = norm_col(" ".join(clean(x) for x in raw.iloc[i].tolist()))
        score = sum(1 for k in HEADER_KEYWORDS if norm_col(k) in row_text)
        if score > best_score:
            best_i, best_score = i, score
        if score >= 2:
            return i
    return best_i if best_score else 0

def read_sheet(path):
    xls, src, eng = excel_file(path)
    for sheet in xls.sheet_names:
        try:
            if hasattr(src, "seek"):
                src.seek(0)
            raw = pd.read_excel(src, sheet_name=sheet, engine=eng, dtype=str, header=None)
            if raw.empty:
                continue

            header = find_header(raw)

            if hasattr(src, "seek"):
                src.seek(0)
            df = pd.read_excel(src, sheet_name=sheet, engine=eng, dtype=str, header=header)
            if df.empty:
                continue

            df.columns = [clean(c) for c in df.columns]
            useful = [c for c in df.columns if c and not str(c).startswith("Unnamed")]

            if len(useful) < 2:
                continue

            print(f"  - sheet='{sheet}', header_row={header + 1}")
            return df, sheet

        except Exception as e:
            print(f"  - 시트 읽기 실패: {sheet} / {e}")

    return None, None

def find_files(base):
    files = []
    for folder in [p for p in base.rglob("배송 데이터 원본") if p.is_dir()]:
        for ext in ("*.xlsx", "*.xlsm", "*.xlsb", "*.xls"):
            files += list(folder.rglob(ext))
    return sorted({f for f in files if not f.name.startswith("~$")})

from collections import Counter
from datetime import timedelta


def to_datetime_safe(value):
    if value is None or pd.isna(value):
        return None
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return None
    return dt.to_pydatetime()


def operational_week_range(value):
    """
    운영주차: 목요일 시작 ~ 다음주 수요일 종료
    """
    dt = to_datetime_safe(value)
    if dt is None:
        return None, None
    days_since_thursday = (dt.weekday() - 3) % 7
    week_start = dt - timedelta(days=days_since_thursday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def report_month_by_weekdays(week_start, week_end):
    """
    운영주차 내 평일(월~금)이 더 많이 포함된 월을 리포트 월로 선택.
    동률이면 운영주 종료일이 속한 월을 우선한다.
    """
    if week_start is None or week_end is None:
        return None, None

    counts = Counter()
    d = week_start
    while d.date() <= week_end.date():
        if d.weekday() < 5:
            counts[(d.year, d.month)] += 1
        d += timedelta(days=1)

    if not counts:
        return week_end.year, week_end.month

    max_count = max(counts.values())
    candidates = [ym for ym, cnt in counts.items() if cnt == max_count]
    if len(candidates) == 1:
        return candidates[0]

    end_ym = (week_end.year, week_end.month)
    return end_ym if end_ym in candidates else sorted(candidates)[-1]


def week_of_month_by_weekday_majority(week_start, week_end):
    """
    평일 다수 월 기준으로 n월 n주 계산.
    """
    report_year, report_month = report_month_by_weekdays(week_start, week_end)
    if report_year is None or report_month is None:
        return None, None, None

    first_day = datetime(report_year, report_month, 1)
    first_week_start, _ = operational_week_range(first_day)

    week_no = 0
    cursor = first_week_start
    for _ in range(8):
        cursor_end = cursor + timedelta(days=6)
        ry, rm = report_month_by_weekdays(cursor, cursor_end)
        if ry == report_year and rm == report_month:
            week_no += 1
            if cursor.date() == week_start.date():
                return report_year, report_month, week_no
        cursor += timedelta(days=7)

    fallback_week_no = ((week_start.day - 1) // 7) + 1
    return report_year, report_month, fallback_week_no


def date_parts(v):
    d = norm_date(v)
    dt = to_datetime_safe(d)
    if dt is None:
        return {
            "claim_year": "",
            "month": "",
            "week_num": None,
            "week": "",
            "week_of_month": "",
            "week_start_date": "",
            "week_end_date": "",
            "quarter": "",
        }

    week_start, week_end = operational_week_range(dt)
    report_year, report_month, week_no = week_of_month_by_weekday_majority(week_start, week_end)
    quarter = ((report_month - 1) // 3) + 1
    week_num = int(week_start.isocalendar().week)

    return {
        "claim_year": str(report_year),
        "month": f"{report_year}-{report_month:02d}",
        "week_num": week_num,
        "week": f"{report_year}-W{week_num:02d}",
        "week_of_month": f"{report_month}월 {week_no}주",
        "week_start_date": week_start.strftime("%Y-%m-%d"),
        "week_end_date": week_end.strftime("%Y-%m-%d"),
        "quarter": f"{quarter}분기",
    }

def claim_key(date, invoice, fallback):
    year = date_parts(date)["claim_year"] or "UNKNOWN_YEAR"
    inv = clean_id(invoice)
    return f"{year}_{inv}" if inv else f"{year}_NO_INVOICE_{fallback}"

def detect_vendor_type(path, df):
    name = path.name.lower().replace(" ", "")

    if "풀필" in name or "fulfillment" in name:
        return "fulfillment"

    if "cj(" in name or "cj" in name or "오발송" in name or "사고" in name:
        return "coldchain"

    # 파일명으로 못 잡을 때만 컬럼 기준 fallback
    cols = {norm_col(c) for c in df.columns}

    if norm_col("접수날짜") in cols and (norm_col("원송장") in cols or norm_col("원송장번호") in cols):
        return "coldchain"

    if norm_col("CS접수일자") in cols and norm_col("원송장번호") in cols:
        return "fulfillment"

    return "unknown"

def create_tables(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS shipment_claims (
        claim_key TEXT PRIMARY KEY,
        claim_date TEXT, claim_year TEXT, month TEXT, week_num INTEGER, week TEXT, week_of_month TEXT,
        week_start_date TEXT, week_end_date TEXT, quarter TEXT,
        vendor_type TEXT, vendor_file_type TEXT, claim_type TEXT, customer_name TEXT,
        order_date TEXT, order_no TEXT,
        original_invoice_no TEXT, resend_invoice_no TEXT, return_invoice_no TEXT,
        product_name TEXT, wrong_product_name TEXT, resend_product_name TEXT, damaged_qty REAL,
        claim_text TEXT, request_text TEXT, action_text TEXT,
        coldchain_note TEXT, cs_note TEXT,
        original_charge_yn TEXT, resend_order_date TEXT, resend_charge_yn TEXT, inbound_date TEXT,
        __source_file TEXT, __source_path TEXT, __source_sheet TEXT, __source_row INTEGER,
        __file_modified_time TEXT, __imported_at TEXT, __row_hash TEXT
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS shipment_import_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_file TEXT, source_path TEXT, source_sheet TEXT,
        inserted_count INTEGER, updated_count INTEGER, skipped_count INTEGER,
        file_modified_time TEXT, imported_at TEXT, status TEXT, message TEXT
    )
    """)

def ensure_columns(conn):
    existing = {r[1] for r in conn.execute("PRAGMA table_info(shipment_claims)").fetchall()}
    req = {
        "request_text":"TEXT",
        "original_charge_yn":"TEXT",
        "resend_order_date":"TEXT",
        "resend_charge_yn":"TEXT",
        "inbound_date":"TEXT",
        "vendor_file_type":"TEXT",
        "week_start_date":"TEXT",
        "week_end_date":"TEXT"
    }
    for c, t in req.items():
        if c not in existing:
            conn.execute(f'ALTER TABLE shipment_claims ADD COLUMN "{c}" {t}')

def processed(conn, path):
    r = conn.execute("""
        SELECT COUNT(*) FROM shipment_import_log
        WHERE source_path=? AND file_modified_time=? AND status='OK'
    """, (str(path), mtime(path))).fetchone()
    return r[0] > 0

def common_date_col(df):
    return first_col(df, ["날짜", "접수날짜", "CS접수일자", "접수일자", "일자", "CS일자", "주문일", "주문일자"])

def common_inv_col(df):
    return first_col(df, ["원송장", "원송장번호", "송장번호"])

def common_claim_type_col(df):
    return first_col(df, ["클레임분류", "사고분류"])

def common_customer_col(df):
    return first_col(df, ["고객명", "받는사람명", "수취인", "수령인"])

def common_product_col(df):
    return first_col(df, ["상품명", "품목명", "제품명"])

def map_row(row, df, path, sheet, row_no, vendor_type):
    c = lambda names: first_col(df, names)

    claim_date = norm_date(val(row, common_date_col(df)))
    invoice = clean_id(val(row, common_inv_col(df)))
    parts = date_parts(claim_date)
    fb = hashlib.md5(f"{path}-{sheet}-{row_no}".encode("utf-8")).hexdigest()[:10]

    is_fulfillment = vendor_type == "fulfillment"

    if vendor_type == "coldchain":
        vendor_file_type = "accident"
    elif vendor_type == "fulfillment":
        vendor_file_type = "claim"
    else:
        vendor_file_type = "unknown"

    return {
        "claim_key": claim_key(claim_date, invoice, fb),
        "claim_date": claim_date,
        "claim_year": parts["claim_year"],
        "month": parts["month"],
        "week_num": parts["week_num"],
        "week": parts["week"],
        "week_of_month": parts["week_of_month"],
        "week_start_date": parts["week_start_date"],
        "week_end_date": parts["week_end_date"],
        "quarter": parts["quarter"],

        "vendor_type": vendor_type,
        "vendor_file_type": vendor_file_type,
        "claim_type": clean(val(row, common_claim_type_col(df))),
        "customer_name": clean(val(row, common_customer_col(df))),

        "order_date": norm_date(val(row, c(["주문일"]))),
        "order_no": clean(val(row, c(["주문번호"]))),

        "original_invoice_no": invoice,
        "resend_invoice_no": clean_id(val(row, c(["재출고송장"]))),
        "return_invoice_no": clean_id(val(row, c(["반송장", "반송장번호"]))),

        "product_name": clean(val(row, common_product_col(df))),
        "wrong_product_name": "" if is_fulfillment else clean(val(row, c(["오발송상품명"]))),
        "resend_product_name": "" if is_fulfillment else clean(val(row, c(["재출고상품명"]))),
        "damaged_qty": None if is_fulfillment else clean_num(val(row, c(["파손수량"]))),

        "claim_text": clean(val(row, c(["클레임내용"]))),
        "request_text": clean(val(row, c(["요청사항"]))),
        "action_text": clean(val(row, c(["처리결과"]))),

        "coldchain_note": clean(val(row, c(["한국초저온 특이사항", "한국초저온특이사항"]))),
        "cs_note": clean(val(row, c(["고객만족팀 특이사항", "고객만족팀특이사항"]))),

        "original_charge_yn": clean(val(row, c(["원송장 청구여부", "원송장청구여부"]))),
        "resend_order_date": norm_date(val(row, c(["주문일(재출고)", "주문일재출고"]))),
        "resend_charge_yn": clean(val(row, c(["재출고 청구여부", "재출고청구여부"]))),
        "inbound_date": norm_date(val(row, c(["반입일(평택)", "반입일평택"]))),
    }

def with_meta(data, path, sheet, row_no):
    out = dict(data)
    out["__source_file"] = path.name
    out["__source_path"] = str(path)
    out["__source_sheet"] = sheet
    out["__source_row"] = int(row_no)
    out["__file_modified_time"] = mtime(path)
    out["__imported_at"] = now()
    out["__row_hash"] = row_hash(data)
    return out

def upsert(conn, data):
    old = conn.execute(
        "SELECT __file_modified_time, __row_hash FROM shipment_claims WHERE claim_key=?",
        (data["claim_key"],)
    ).fetchone()
    cols = list(data.keys())

    if old is None:
        conn.execute(
            f'INSERT INTO shipment_claims ({", ".join(chr(34)+c+chr(34) for c in cols)}) VALUES ({", ".join(["?"]*len(cols))})',
            [data[c] for c in cols]
        )
        return "insert"

    if (data.get("__file_modified_time") or "") >= (old[0] or "") and data.get("__row_hash") != old[1]:
        set_sql = ", ".join(f'"{c}"=?' for c in cols if c != "claim_key")
        conn.execute(
            f'UPDATE shipment_claims SET {set_sql} WHERE claim_key=?',
            [data[c] for c in cols if c != "claim_key"] + [data["claim_key"]]
        )
        return "update"

    return "skip"

def log(conn, path, sheet, i, u, s, status="OK", msg=""):
    conn.execute("""
    INSERT INTO shipment_import_log (
        source_file, source_path, source_sheet,
        inserted_count, updated_count, skipped_count,
        file_modified_time, imported_at, status, message
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (path.name, str(path), sheet, i, u, s, mtime(path), now(), status, msg))

def process_file(conn, path):
    if not path.exists() or path.stat().st_size <= 1024:
        log(conn, path, "", 0, 0, 0, "EMPTY_FILE", "0바이트 또는 손상된 파일")
        print(f"  - 0바이트 또는 빈 파일 건너뜀: {path.name}")
        return 0, 0, 0

    try:
        df, sheet = read_sheet(path)
    except Exception as e:
        log(conn, path, "", 0, 0, 0, "READ_ERROR", str(e))
        print(f"  - 파일 읽기 실패 건너뜀: {path.name} ({e})")
        return 0, 0, 0

    if df is None:
        log(conn, path, "", 0, 0, 0, "READ_FAIL", "읽을 수 있는 시트 없음")
        print("  - 읽을 수 있는 시트 없음")
        return 0, 0, 0

    vendor_type = detect_vendor_type(path, df)

    if vendor_type == "unknown":
        log(conn, path, sheet, 0, 0, 0, "NO_VENDOR", f"vendor_type 인식 실패: {list(df.columns)}")
        print("  - vendor_type 인식 실패")
        print(f"    columns={list(df.columns)}")
        return 0, 0, 0

    inserted = updated = skipped = 0

    for idx, row in df.iterrows():
        row_no = idx + 2
        data = map_row(row, df, path, sheet, row_no, vendor_type)

        if not clean(data["claim_date"]) and not clean(data["original_invoice_no"]):
            skipped += 1
            continue

        result = upsert(conn, with_meta(data, path, sheet, row_no))

        if result == "insert":
            inserted += 1
        elif result == "update":
            updated += 1
        else:
            skipped += 1

    log(conn, path, sheet, inserted, updated, skipped, "OK", vendor_type)
    print(f"  - {vendor_type} → shipment_claims / insert {inserted}, update {updated}, skip {skipped}")
    return inserted, updated, skipped

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--force", action="store_true", help="shipment_import_log 무시하고 강제 재적재")
    args = parser.parse_args()

    base = Path(args.base)
    db_path = Path(args.db)
    files = find_files(base)

    print(f"[INFO] 기준 폴더: {base}")
    print(f"[INFO] 배송 엑셀 파일 수: {len(files)}")
    print(f"[INFO] DB 경로: {db_path}")
    print(f"[INFO] FORCE: {args.force}")

    conn = sqlite3.connect(
        db_path,  
        timeout=60
    )   
    create_tables(conn)
    ensure_columns(conn)

    ti = tu = ts = fs = 0

    try:
        for path in files:
            print(f"\n[FILE] {path}")

            if not args.force and processed(conn, path):
                print("  - 이미 처리된 파일입니다. FILE SKIP")
                fs += 1
                continue

            i, u, s = process_file(conn, path)
            ti += i
            tu += u
            ts += s
            conn.commit()

        print("\n[DONE]")
        print(f"전체 INSERT: {ti}")
        print(f"전체 UPDATE: {tu}")
        print(f"전체 ROW SKIP: {ts}")
        print(f"전체 FILE SKIP: {fs}")

    finally:
        conn.commit()
        conn.close()

if __name__ == "__main__":
    main()

