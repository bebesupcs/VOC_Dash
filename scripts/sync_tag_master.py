# -*- coding: utf-8 -*-
"""
sync_tag_master.py
구글 스프레드시트 태그 마스터 초고속 동기화 모듈
URL: https://docs.google.com/spreadsheets/d/1l-eDWHv_RJsE1Y36ggyrd3lurbbqaEUSDiEnbCSfV1o/edit?gid=345810278
CSV: https://docs.google.com/spreadsheets/d/1l-eDWHv_RJsE1Y36ggyrd3lurbbqaEUSDiEnbCSfV1o/export?format=csv&gid=345810278

구글 시트에서 태그 마스터(대/중/소/고객여정) 변경 시 SQLite DB 및 대시보드(data.js, data.json) 자동 최신화
"""

import csv
import io
import os
import sys
import time
import sqlite3
import urllib.request
from datetime import datetime
from pathlib import Path

# 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1l-eDWHv_RJsE1Y36ggyrd3lurbbqaEUSDiEnbCSfV1o/export?format=csv&gid=345810278"
BASE_DIR = Path(__file__).resolve().parent.parent
X_BASE = Path(r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황")
DB_PATH = X_BASE / "db" / "channeltalk_voc.db"
LOCAL_CACHE_CSV = BASE_DIR / "dashboard" / "google_tag_master_cache.csv"


def fetch_google_sheet_tag_master():
    """구글 시트에서 최신 태그 마스터 CSV 다운로드"""
    req = urllib.request.Request(
        SHEET_CSV_URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read().decode("utf-8")
    return content


def sync_tag_master_to_db(log_func=print):
    """
    구글 시트 태그 마스터를 SQLite DB에 반영하고 변경 여부를 반환
    """
    t0 = time.time()
    log_func("▶ [Google Sheets] 태그 마스터 최신 동기화 점검...")

    try:
        csv_text = fetch_google_sheet_tag_master()
    except Exception as e:
        log_func(f"  ⚠️ 구글 시트 다운로드 실패 (인터넷 연결 또는 권한 확인 필요): {e}")
        return False, 0

    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    if not rows or len(rows) < 2:
        log_func("  ⚠️ 구글 시트 데이터가 비어 있습니다.")
        return False, 0

    # Header parsing: 태그 ID, 전체태그, 고객 여정 5단계, 대, 중, 소
    id_idx, full_idx, journey_idx, a_idx, b_idx, c_idx = 0, 1, 2, 3, 4, 5

    parsed_items = []
    for r in rows[1:]:
        if not r or not any(r):
            continue
        c_id = r[id_idx].strip() if len(r) > id_idx else ""
        c_full = r[full_idx].strip() if len(r) > full_idx else ""
        c_journey = r[journey_idx].strip() if len(r) > journey_idx else ""
        c_a = r[a_idx].strip() if len(r) > a_idx else ""
        c_b = r[b_idx].strip() if len(r) > b_idx else ""
        c_c = r[c_idx].strip() if len(r) > c_idx else ""

        if not c_id and not c_full:
            continue
        parsed_items.append((c_id, c_full, c_journey, c_a, c_b, c_c))

    if not parsed_items:
        log_func("  - 유효한 태그 행이 없습니다.")
        return False, 0

    # 로컬 캐시와 비교하여 변경 여부 판별
    prev_csv = ""
    if LOCAL_CACHE_CSV.exists():
        try:
            with open(LOCAL_CACHE_CSV, "r", encoding="utf-8") as f:
                prev_csv = f.read()
        except Exception:
            pass

    has_changed = (csv_text.strip() != prev_csv.strip())

    # 캐시 갱신
    try:
        with open(LOCAL_CACHE_CSV, "w", encoding="utf-8") as f:
            f.write(csv_text)
    except Exception as e:
        pass

    if not DB_PATH.exists():
        log_func(f"  ❌ DB 파일을 찾을 수 없습니다: {DB_PATH}")
        return has_changed, len(parsed_items)

    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tag_master (
        channelId TEXT PRIMARY KEY,
        full_tag TEXT,
        journey TEXT,
        tag_a TEXT,
        tag_b TEXT,
        tag_c TEXT,
        __source_file TEXT,
        __source_path TEXT,
        __source_sheet TEXT,
        __file_modified_time TEXT,
        __imported_at TEXT
    )
    """)

    # tag_master에 초고속 배치 UPSERT
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    upsert_sql = """
    INSERT INTO tag_master (channelId, full_tag, journey, tag_a, tag_b, tag_c, __source_file, __source_path, __source_sheet, __imported_at)
    VALUES (?, ?, ?, ?, ?, ?, 'GoogleSheet_TagMaster', 'GoogleDrive', '345810278', ?)
    ON CONFLICT(channelId) DO UPDATE SET
        full_tag=excluded.full_tag,
        journey=excluded.journey,
        tag_a=excluded.tag_a,
        tag_b=excluded.tag_b,
        tag_c=excluded.tag_c,
        __imported_at=excluded.__imported_at
    """
    batch_params = [(item[0], item[1], item[2], item[3], item[4], item[5], now_str) for item in parsed_items]
    cur.executemany(upsert_sql, batch_params)

    conn.commit()
    conn.close()

    elapsed = time.time() - t0
    if has_changed:
        log_func(f"  ✨ 구글 시트 태그 마스터 {len(parsed_items)}건 DB 동기화 완료! ({elapsed:.1f}초)")
    else:
        log_func(f"  ✓ 구글 시트 태그 마스터 최신 상태 유지 중 ({len(parsed_items)}건, {elapsed:.1f}초)")

    return has_changed, len(parsed_items)


if __name__ == "__main__":
    changed, count = sync_tag_master_to_db(print)
    print(f"동기화 완료: 변경여부={changed}, 태그수={count}")
