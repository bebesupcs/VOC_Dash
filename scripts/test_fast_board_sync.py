# -*- coding: utf-8 -*-
import sys
import sqlite3
import time
from pathlib import Path
from datetime import datetime

# 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.append(r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\scripts")
from import_boards import (
    read_board, date_parts, day_name_from_date,
    mall_columns, norm_date, clean, clean_num, mtime, now, rhash
)

board_file = Path(r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\raw\게시판 데이터 원본\게시판_통합운영.xlsx")
db_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"

t0 = time.time()
print(f"▶ 게시판 엑셀 로드 시작: {board_file.name}")
df, sheet = read_board(board_file)
print(f"  ✓ 엑셀 로드 완료 ({time.time() - t0:.2f}초), Shape: {df.shape}")

date_col = "일자"
first = df.columns[0]
df = df[df["일자"].notna()].copy()
df["__date"] = df[date_col].apply(norm_date)
df = df[df["__date"] != ""].copy()
malls = mall_columns(df)
print(f"  ✓ 유효 행: {len(df)}행, 판매몰: {len(malls)}개")

# 행 데이터 준비
batch_rows = []
seen_keys = []
mod_time = mtime(board_file)
now_time = now()
source_file = board_file.name
source_path = str(board_file)

for _, row in df.iterrows():
    d = row["__date"]
    parts = date_parts(d)
    day_name = day_name_from_date(d)

    for mall_col in malls:
        mall = clean(mall_col)
        count = clean_num(row.get(mall_col, 0))
        bkey = f"{d}_{mall}"
        seen_keys.append(bkey)

        base_dict = {
            "board_key": bkey,
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
        row_hash = rhash(base_dict)

        batch_rows.append((
            bkey, d, str(parts["year"] or ""), parts["month"] or "",
            parts["week_num"], parts["week"] or "", parts["week_of_month"] or "",
            parts["week_start_date"] or "", parts["week_end_date"] or "",
            parts["quarter"] or "", day_name or "", mall, count,
            source_file, source_path, sheet, mod_time, now_time, row_hash
        ))

print(f"  ✓ 데이터 변환 완료: 총 {len(batch_rows)}건 생성 ({time.time() - t0:.2f}초)")

conn = sqlite3.connect(db_path, timeout=60)
cur = conn.cursor()

# SQLite PRAGMA 속도 향상
cur.execute("PRAGMA journal_mode=WAL")
cur.execute("PRAGMA synchronous=NORMAL")

t_sql = time.time()
cur.executemany("""
    INSERT OR REPLACE INTO board_daily_counts (
        board_key, date, year, month, week_num, week, week_of_month,
        week_start_date, week_end_date, quarter, day_name, mall_name,
        board_count, __source_file, __source_path, __source_sheet,
        __file_modified_time, __imported_at, __row_hash
    ) VALUES (
        ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?
    )
""", batch_rows)

conn.commit()
print(f"  ✓ DB 반영 완료 ({time.time() - t_sql:.2f}초)!")

# 로그 기록
cur.execute("""
    INSERT INTO board_import_log (
        source_file, source_path, source_sheet, inserted_count,
        updated_count, skipped_count, file_modified_time, imported_at,
        status, message
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    source_file, source_path, sheet, len(batch_rows), 0, 0,
    mod_time, now_time, "OK", f"fast_batch_upsert: rows={len(batch_rows)}"
))
conn.commit()
conn.close()

print(f"✨ [성공] 총 소요시간: {time.time() - t0:.2f}초")
