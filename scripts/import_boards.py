# -*- coding: utf-8 -*-
"""
import_boards.py

게시판 엑셀 → SQLite 적재 안정 버전

핵심 기준
- 운영주차: 목요일 ~ 다음주 수요일
- month / week_of_month / quarter:
  해당 운영주 안에서 평일(월~금)이 더 많이 포함된 월 기준
- 게시판 엑셀의 주(가공1), 주(가공2)는 DB 기간값 산정에 사용하지 않음
- 일자 컬럼 기준으로 week_start_date / week_end_date / week_of_month 계산
"""

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

PREFERRED_SHEETS = ["게시판_DB", "board_db", "DB", "db"]

DATE_COLS = [
    "년", "연도", "year",
    "주(가공1)", "주가공1", "주_가공1", "주차가공1",
    "월", "month",
    "주(가공2)", "주가공2", "주_가공2", "주차가공2",
    "요일(가공)", "요일가공", "요일",
    "일자", "날짜", "date",
    "합계",
    "__date",
]

EXCLUDE_ROWS = ["전체합계", "연도별합계"]


# =========================================================
# 공통 유틸
# =========================================================

def clean(v):
    if v is None or pd.isna(v):
        return ""
    t = str(v).strip()
    return "" if t.lower() == "nan" else t


def norm_col(c):
    return re.sub(r"[\s_\.\n\r]+", "", str(c).strip())


def find_col(cols, names):
    col_map = {norm_col(c): c for c in cols}

    for name in names:
        key = norm_col(name)
        if key in col_map:
            return col_map[key]

    for name in names:
        key = norm_col(name)
        for k, original in col_map.items():
            if key and key in k:
                return original

    return None


def rowval(row, names):
    c = find_col(row.index, names)
    return row.get(c, "") if c is not None else ""


def clean_num(v):
    t = clean(v).replace(",", "")
    if not t:
        return 0

    try:
        return int(float(t))
    except Exception:
        return 0


def to_datetime_safe(value):
    if value is None or pd.isna(value):
        return None

    dt = pd.to_datetime(value, errors="coerce")

    if pd.isna(dt):
        return None

    return dt.to_pydatetime()


def norm_date(v):
    dt = to_datetime_safe(v)

    if dt is None:
        return ""

    return dt.strftime("%Y-%m-%d")


def mtime(path):
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


def now():
    return datetime.now().isoformat(timespec="seconds")


def rhash(data):
    s = "||".join(f"{k}={'' if data[k] is None else str(data[k])}" for k in sorted(data))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def excel_engine(path):
    suffix = path.suffix.lower()

    if suffix == ".xlsb":
        return "pyxlsb"

    if suffix == ".xls":
        return "xlrd"

    return "openpyxl"


def load_excel(path):
    try:
        pd.ExcelFile(path, engine=excel_engine(path))
        return path, excel_engine(path)

    except Exception as e:
        msg = str(e)

        if path.suffix.lower() == ".xlsx":
            try:
                pd.ExcelFile(path, engine="xlrd")
                return path, "xlrd"
            except Exception:
                pass

        encrypted = (
            "File is not a zip file" in msg
            or "encrypted" in msg.lower()
            or "password" in msg.lower()
        )

        if not encrypted:
            raise

    if msoffcrypto is None:
        raise RuntimeError("암호화 엑셀 읽기 필요: pip install msoffcrypto-tool")

    last_error = None

    for password in EXCEL_PASSWORDS:
        try:
            bio = io.BytesIO()

            with open(path, "rb") as f:
                office = msoffcrypto.OfficeFile(f)
                office.load_key(password=password)
                office.decrypt(bio)

            bio.seek(0)

            try:
                pd.ExcelFile(bio, engine="openpyxl")
                bio.seek(0)
                return bio, "openpyxl"
            except Exception:
                bio.seek(0)
                return bio, "xlrd"

        except Exception as e:
            last_error = e

    raise RuntimeError(f"엑셀 비밀번호 해제 실패: {path} / {last_error}")


# =========================================================
# 운영 주차 계산
# =========================================================

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
    동률이면 운영주 종료일이 속한 월 우선.
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
    평일 다수 월 기준 n월 n주 계산.
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


def date_parts(value):
    dt = to_datetime_safe(value)

    if dt is None:
        return {
            "year": "",
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
        "year": str(report_year),
        "month": f"{report_year}-{report_month:02d}",
        "week_num": week_num,
        "week": f"W{week_num:02d}",
        "week_of_month": f"{report_month}월 {week_no}주",
        "week_start_date": week_start.strftime("%Y-%m-%d"),
        "week_end_date": week_end.strftime("%Y-%m-%d"),
        "quarter": f"Q{quarter}",
    }


def day_name_from_date(date_text):
    dt = to_datetime_safe(date_text)

    if dt is None:
        return ""

    return {
        0: "월",
        1: "화",
        2: "수",
        3: "목",
        4: "금",
        5: "토",
        6: "일",
    }.get(dt.weekday(), "")


# =========================================================
# 파일/시트 탐색
# =========================================================

def find_files(base):
    """
    1순위: raw 하위 '게시판 데이터 원본' 폴더
    2순위: raw 하위 파일명에 '게시판' 포함
    3순위: base 하위 파일명에 '게시판' 포함
    """
    files = []

    board_dirs = [p for p in base.rglob("게시판 데이터 원본") if p.is_dir()]

    for folder in board_dirs:
        for ext in ("*.xlsx", "*.xlsm", "*.xlsb", "*.xls"):
            files += list(folder.rglob(ext))

    if not files:
        for raw_dir in [p for p in base.rglob("raw") if p.is_dir()]:
            for ext in ("*.xlsx", "*.xlsm", "*.xlsb", "*.xls"):
                files += [p for p in raw_dir.rglob(ext) if "게시판" in p.name]

    if not files:
        for ext in ("*.xlsx", "*.xlsm", "*.xlsb", "*.xls"):
            files += [p for p in base.rglob(ext) if "게시판" in p.name]

    files = sorted({f for f in files if not f.name.startswith("~$")})

    print(f"[DEBUG] 게시판 후보 파일 수: {len(files)}")
    for f in files:
        print(f"        - {f}")

    return files


def find_header(raw):
    best_i, best_score = 0, 0

    for i in range(min(40, len(raw))):
        vals = [norm_col(clean(x)) for x in raw.iloc[i].tolist()]
        text = "|".join(vals)

        score = 0

        for key in ["년", "월", "일자", "날짜", "합계"]:
            if norm_col(key) in vals:
                score += 2

        for keyword in ["쿠팡", "네이버", "자사몰", "SSG", "롯데", "G마켓", "옥션", "카카오", "올리브영", "11번가"]:
            if keyword in text:
                score += 1

        if score > best_score:
            best_i, best_score = i, score

        if score >= 7:
            return i

    return best_i


def read_sheet_with_header(src, eng, sheet):
    if hasattr(src, "seek"):
        src.seek(0)

    raw = pd.read_excel(src, sheet_name=sheet, engine=eng, dtype=str, header=None)

    if raw.empty:
        return None, None

    header = find_header(raw)

    if hasattr(src, "seek"):
        src.seek(0)

    df = pd.read_excel(src, sheet_name=sheet, engine=eng, dtype=str, header=header)

    if df.empty:
        return None, None

    df.columns = [clean(c) for c in df.columns]

    return df, header


def read_board(path):
    src, eng = load_excel(path)
    xls = pd.ExcelFile(src, engine=eng)

    preferred_keys = [norm_col(x) for x in PREFERRED_SHEETS]
    preferred = [s for s in xls.sheet_names if norm_col(s) in preferred_keys]
    sheet_order = preferred + [s for s in xls.sheet_names if s not in preferred]

    print(f"  - sheet candidates={xls.sheet_names}")

    for sheet in sheet_order:
        try:
            df, header = read_sheet_with_header(src, eng, sheet)

            if df is None:
                continue

            date_col = find_col(df.columns, ["일자", "날짜", "date"])

            if not date_col:
                print(f"  - 시트 제외: {sheet} / 일자 컬럼 없음 / columns={list(df.columns)}")
                continue

            print(f"  - sheet='{sheet}', header_row={header + 1}")
            print(f"  - columns={list(df.columns)}")

            return df, sheet

        except Exception as e:
            print(f"  - 시트 읽기 실패: {sheet} / {e}")

    return None, None


# =========================================================
# DB
# =========================================================

def create_tables(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS board_daily_counts (
        board_key TEXT PRIMARY KEY,
        date TEXT,
        year TEXT,
        month TEXT,
        week_num INTEGER,
        week TEXT,
        week_of_month TEXT,
        week_start_date TEXT,
        week_end_date TEXT,
        quarter TEXT,
        day_name TEXT,
        mall_name TEXT,
        board_count INTEGER,
        __source_file TEXT,
        __source_path TEXT,
        __source_sheet TEXT,
        __file_modified_time TEXT,
        __imported_at TEXT,
        __row_hash TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS board_import_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_file TEXT,
        source_path TEXT,
        source_sheet TEXT,
        inserted_count INTEGER,
        updated_count INTEGER,
        skipped_count INTEGER,
        file_modified_time TEXT,
        imported_at TEXT,
        status TEXT,
        message TEXT
    )
    """)


def ensure_columns(conn):
    existing = {r[1] for r in conn.execute("PRAGMA table_info(board_daily_counts)").fetchall()}

    required = {
        "year": "TEXT",
        "month": "TEXT",
        "week_num": "INTEGER",
        "week": "TEXT",
        "week_of_month": "TEXT",
        "week_start_date": "TEXT",
        "week_end_date": "TEXT",
        "quarter": "TEXT",
        "day_name": "TEXT",
    }

    for col, typ in required.items():
        if col not in existing:
            conn.execute(f'ALTER TABLE board_daily_counts ADD COLUMN "{col}" {typ}')


def processed(conn, path):
    row = conn.execute("""
        SELECT COUNT(*)
        FROM board_import_log
        WHERE source_path = ?
          AND file_modified_time = ?
          AND status = 'OK'
    """, (str(path), mtime(path))).fetchone()

    return row[0] > 0


def upsert(conn, data):
    old = conn.execute(
        "SELECT __file_modified_time, __row_hash FROM board_daily_counts WHERE board_key = ?",
        (data["board_key"],)
    ).fetchone()

    cols = list(data.keys())

    if old is None:
        conn.execute(
            f'INSERT INTO board_daily_counts ({", ".join(chr(34) + c + chr(34) for c in cols)}) VALUES ({", ".join(["?"] * len(cols))})',
            [data[c] for c in cols]
        )
        return "insert"

    if (data.get("__file_modified_time") or "") >= (old[0] or "") and data.get("__row_hash") != old[1]:
        set_sql = ", ".join(f'"{c}" = ?' for c in cols if c != "board_key")
        conn.execute(
            f'UPDATE board_daily_counts SET {set_sql} WHERE board_key = ?',
            [data[c] for c in cols if c != "board_key"] + [data["board_key"]]
        )
        return "update"

    return "skip"


def log_import(conn, path, sheet, inserted, updated, skipped, status="OK", msg=""):
    conn.execute("""
    INSERT INTO board_import_log (
        source_file,
        source_path,
        source_sheet,
        inserted_count,
        updated_count,
        skipped_count,
        file_modified_time,
        imported_at,
        status,
        message
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        path.name,
        str(path),
        sheet,
        inserted,
        updated,
        skipped,
        mtime(path),
        now(),
        status,
        msg
    ))


# =========================================================
# 변환
# =========================================================

def mall_columns(df):
    exclude = {norm_col(c) for c in DATE_COLS}
    out = []

    for c in df.columns:
        cc = clean(c)

        if not cc or cc.startswith("Unnamed"):
            continue

        if norm_col(cc) in exclude:
            continue

        out.append(c)

    return out


def process_file(conn, path):
    df, sheet = read_board(path)

    if df is None:
        log_import(conn, path, "", 0, 0, 0, "READ_FAIL", "읽을 수 있는 게시판 시트 없음")
        print("  - 읽을 수 있는 게시판 시트 없음")
        return 0, 0, 0

    date_col = find_col(df.columns, ["일자", "날짜", "date"])

    if not date_col:
        log_import(conn, path, sheet, 0, 0, 0, "NO_DATE_COL", "일자 컬럼 없음")
        print("  - 일자 컬럼 없음")
        return 0, 0, 0

    first = df.columns[0]
    df = df[~df[first].astype(str).isin(EXCLUDE_ROWS)].copy()

    df["__date"] = df[date_col].apply(norm_date)
    before_rows = len(df)
    df = df[df["__date"] != ""].copy()
    after_rows = len(df)

    print(f"  - date_col='{date_col}', rows_before_date_filter={before_rows}, rows_after_date_filter={after_rows}")

    malls = mall_columns(df)

    print(f"  - mall_cols={len(malls)}")
    if malls:
        print(f"  - mall_cols_sample={malls[:10]}")

    if not malls:
        log_import(conn, path, sheet, 0, 0, 0, "NO_MALL_COL", "판매몰 컬럼 없음")
        print("  - 판매몰 컬럼 없음")
        return 0, 0, 0

    inserted = updated = skipped = 0

    for _, row in df.iterrows():
        d = row["__date"]
        parts = date_parts(d)
        day_name = day_name_from_date(d)

        for mall_col in malls:
            mall = clean(mall_col)
            count = clean_num(row.get(mall_col, 0))

            base = {
                "board_key": f"{d}_{mall}",
                "date": d,
                "year": parts["year"],
                "month": parts["month"],
                "week_num": parts["week_num"],
                "week": parts["week"],
                "week_of_month": parts["week_of_month"],
                "week_start_date": parts["week_start_date"],
                "week_end_date": parts["week_end_date"],
                "quarter": parts["quarter"],
                "day_name": day_name,
                "mall_name": mall,
                "board_count": count,
            }

            data = dict(base)
            data["__source_file"] = path.name
            data["__source_path"] = str(path)
            data["__source_sheet"] = sheet
            data["__file_modified_time"] = mtime(path)
            data["__imported_at"] = now()
            data["__row_hash"] = rhash(base)

            result = upsert(conn, data)

            if result == "insert":
                inserted += 1
            elif result == "update":
                updated += 1
            else:
                skipped += 1

    log_import(conn, path, sheet, inserted, updated, skipped, "OK", f"mall_cols={len(malls)}")
    print(f"  - board_daily_counts / insert {inserted}, update {updated}, skip {skipped}, mall_cols={len(malls)}")

    return inserted, updated, skipped


# =========================================================
# main
# =========================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--force", action="store_true", help="board_import_log 무시하고 강제 재적재")
    args = parser.parse_args()

    base = Path(args.base)
    db_path = Path(args.db)
    files = find_files(base)

    print(f"[INFO] 기준 폴더: {base}")
    print(f"[INFO] 게시판 엑셀 파일 수: {len(files)}")
    print(f"[INFO] DB 경로: {db_path}")
    print(f"[INFO] FORCE: {args.force}")

    conn = sqlite3.connect(db_path, timeout=60)

    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass

    create_tables(conn)
    ensure_columns(conn)

    total_inserted = total_updated = total_skipped = 0
    file_skipped = 0

    try:
        for path in files:
            print(f"\n[FILE] {path}")

            if not args.force and processed(conn, path):
                print("  - 이미 처리된 파일입니다. FILE SKIP")
                file_skipped += 1
                continue

            i, u, s = process_file(conn, path)

            total_inserted += i
            total_updated += u
            total_skipped += s

            conn.commit()

        print("\n[DONE]")
        print(f"전체 INSERT: {total_inserted}")
        print(f"전체 UPDATE: {total_updated}")
        print(f"전체 ROW SKIP: {total_skipped}")
        print(f"전체 FILE SKIP: {file_skipped}")

    finally:
        conn.commit()
        conn.close()


if __name__ == "__main__":
    main()
