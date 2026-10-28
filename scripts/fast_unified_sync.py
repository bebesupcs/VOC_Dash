# -*- coding: utf-8 -*-
"""
fast_unified_sync.py
베베숲 CX팀 초고속 증분 VOC 데이터 통합 동기화 엔진

3대 데이터(채널톡, 배송, 게시판)를 0.1초 단위로 파일 수정일(mtime)을 스마트 감지하여,
수정된 데이터만 초고속으로 증분 적재하고 대시보드(data.js, data.json)를 자동 갱신합니다.

- 변경사항 없을 시: 1초 미만 완료 (전체 FILE SKIP)
- 신규 데이터 수정 시: 약 15~20초 내 DB 적재 및 대시보드 패치 완료
"""

import os
import sys
import time
import sqlite3
from datetime import datetime
from pathlib import Path

# 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
DASHBOARD_DIR = BASE_DIR / "dashboard"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

X_BASE = Path(r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황")
X_SCRIPTS = X_BASE / "scripts"
DB_PATH = X_BASE / "db" / "channeltalk_voc.db"

# X 드라이브 스크립트 경로 로드
if str(X_SCRIPTS) not in sys.path:
    sys.path.append(str(X_SCRIPTS))


def log(msg, log_file=None):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now_str}] {msg}"
    print(line)
    if log_file:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def sync_shipments_fast(log_func=print):
    """배송 클레임(풀필먼트 / CJ초저온) 엑셀 증분 동기화"""
    t0 = time.time()
    log_func("▶ [1/3] 배송 클레임 엑셀 증분 점검...")

    if not DB_PATH.exists():
        log_func(f"  ❌ DB 파일을 찾을 수 없습니다: {DB_PATH}")
        return False, 0, 0

    try:
        import import_shipments as imp_ship
    except ImportError as e:
        log_func(f"  ❌ import_shipments 모듈 로드 실패: {e}")
        return False, 0, 0

    # 모든 연도(25년, 26년, 27년 등)의 배송 데이터 원본 폴더 동적 탐색 (네트워크 rglob 병목 없이 즉시 탐색)
    target_folders = sorted(
        [p for p in X_BASE.glob("*년/raw/배송 데이터 원본") if p.is_dir()],
        reverse=True
    )
    if not target_folders:
        target_folders = [
            X_BASE / "26년" / "raw" / "배송 데이터 원본",
            X_BASE / "25년" / "raw" / "배송 데이터 원본"
        ]

    files = []
    for folder in target_folders:
        if folder.exists():
            for f in folder.iterdir():
                if f.is_file() and not f.name.startswith("~$") and f.suffix.lower() in [".xlsx", ".xlsm", ".xlsb", ".xls"]:
                    files.append(f)

    if not files:
        log_func("  - 검사 대상 배송 엑셀 파일이 없습니다.")
        return False, 0, 0

    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    cur = conn.cursor()
    tbl_exists = cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='shipment_claims'").fetchone()
    if not tbl_exists:
        imp_ship.create_tables(conn)
        imp_ship.ensure_columns(conn)

    # 1회의 쿼리로 이미 처리된 파일 목록을 메모리로 고속 로드 (네트워크 왕복 병목 제거)
    cur.execute("SELECT source_file, file_modified_time FROM shipment_import_log WHERE status='OK'")
    processed_set = set(cur.fetchall())

    changed_files = 0
    total_inserted = 0
    total_updated = 0

    for path in files:
        m_time = imp_ship.mtime(path)
        if (path.name, m_time) in processed_set:
            continue  # 이미 처리된 파일은 메모리에서 0.0001초 만에 SKIP

        log_func(f"  ▶ 신규/수정 파일 감지: {path.name}")
        i, u, s = imp_ship.process_file(conn, path)
        conn.commit()
        changed_files += 1
        total_inserted += i
        total_updated += u
        log_func(f"    ✓ {path.name}: 신규 {i}건, 갱신 {u}건, 건너뜀 {s}건")

    conn.close()
    elapsed = time.time() - t0

    if changed_files > 0:
        log_func(f"  ✨ 배송 {changed_files}개 파일 변경 반영 완료 (신규 {total_inserted}건, {elapsed:.1f}초)")
        return True, total_inserted, total_updated
    else:
        log_func(f"  ✓ 배송 데이터 최신 상태 유지 중 (변경 없음, {elapsed:.2f}초)")
        return False, 0, 0


def sync_board_fast(log_func=print):
    """게시판 엑셀 일괄 고속 증분 동기화"""
    t0 = time.time()
    log_func("▶ [2/3] 게시판 수기접수 엑셀 증분 점검...")

    # 모든 연도(26년, 27년 등)의 게시판 엑셀 원본 파일 동적 탐색
    board_files = sorted(
        [p for p in X_BASE.glob("*년/raw/게시판 데이터 원본/게시판_*.xlsx") if p.is_file() and not p.name.startswith("~$")],
        reverse=True
    )
    if not board_files:
        single_file = X_BASE / "26년" / "raw" / "게시판 데이터 원본" / "게시판_통합운영.xlsx"
        if single_file.exists():
            board_files = [single_file]

    if not board_files:
        log_func(f"  - 게시판 원본 파일 없음: {X_BASE / '26년' / 'raw' / '게시판 데이터 원본'}")
        return False, 0

    try:
        from import_boards import (
            read_board, date_parts, day_name_from_date,
            mall_columns, norm_date, clean, clean_num, mtime, now, rhash
        )

        conn = sqlite3.connect(str(DB_PATH), timeout=30)
        total_synced_rows = 0
        any_file_changed = False

        for board_file in board_files:
            mod_time = mtime(board_file)

            # 이미 처리된 파일인지 mtime 확인
            row = conn.execute("""
                SELECT COUNT(*) FROM board_import_log
                WHERE source_path = ? AND file_modified_time = ? AND status = 'OK'
            """, (str(board_file), mod_time)).fetchone()

            if row and row[0] > 0:
                continue

            log_func(f"  ▶ 게시판 파일 수정 감지: {board_file.name} (파싱 중...)")
            df, sheet = read_board(board_file)
            if df is None:
                log_func(f"  ❌ 게시판 시트를 읽을 수 없습니다: {board_file.name}")
                continue

            date_col = "일자"
            df = df[df["일자"].notna()].copy()
            df["__date"] = df[date_col].apply(norm_date)
            df = df[df["__date"] != ""].copy()
            # '전체합계' 중복합산 방지 (개별 몰 컬럼만 수집)
            malls = [c for c in mall_columns(df) if "합계" not in str(c) and "total" not in str(c).lower()]

            batch_rows = []
            now_time = now()
            source_file = board_file.name
            source_path = str(board_file)

            for _, r in df.iterrows():
                d = r["__date"]
                parts = date_parts(d)
                day_name = day_name_from_date(d)

                for mall_col in malls:
                    mall = clean(mall_col)
                    count = clean_num(r.get(mall_col, 0))
                    bkey = f"{d}_{mall}"

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

            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")

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
            any_file_changed = True
            total_synced_rows += len(batch_rows)

        conn.close()
        elapsed = time.time() - t0
        if any_file_changed:
            log_func(f"  ✨ 게시판 {total_synced_rows:,}건 고속 동기화 완료! ({elapsed:.1f}초)")
            return True, total_synced_rows
        else:
            log_func(f"  ✓ 게시판 데이터 최신 상태 유지 중 (변경 없음, {elapsed:.2f}초)")
            return False, 0

    except Exception as e:
        log_func(f"  ❌ 게시판 동기화 오류: {e}")
        return False, 0


def sync_channeltalk_fast(days=7, log_func=print):
    """채널톡 Open API 증분 동기화 (기본 최근 7일치)"""
    t0 = time.time()
    log_func(f"▶ [3/3] 채널톡 API 증분 동기화 (최근 {days}일)...")

    try:
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.append(str(SCRIPTS_DIR))
        from sync_channeltalk_api import run_sync
        # export_dashboard=False (모든 수집 완료 후 마지막에 1회만 고속 추출)
        summary = run_sync(days=days, export_dashboard=False)
        elapsed = time.time() - t0
        log_func(f"  ✓ 채널톡 API 상담 동기화 완료 ({elapsed:.1f}초)")
        return True, summary
    except Exception as e:
        log_func(f"  ⚠ 채널톡 API 동기화 건너뜀 또는 오류: {e}")
        return False, str(e)


def run_fast_patch(force_export=False, sync_api=True, api_days=7):
    """통합 원터치 고속 패치 실행 함수"""
    t_start = time.time()
    today_str = datetime.now().strftime("%Y%m%d")
    log_file = LOGS_DIR / f"fast_sync_{today_str}.log"

    log("=" * 60, log_file)
    log("🚀 [패치 시작] 채널톡 · 배송 · 게시판 · 구글시트 초고속 통합 동기화", log_file)
    log("=" * 60, log_file)

    # 1. 구글 스프레드시트 태그 마스터 동기화
    tag_changed = False
    try:
        from sync_tag_master import sync_tag_master_to_db
        tag_changed, _ = sync_tag_master_to_db(lambda m: log(m, log_file))
    except Exception as e:
        log(f"  ⚠️ 구글 시트 태그 마스터 동기화 건너뜀: {e}", log_file)

    shipment_changed, ship_ins, ship_upd = sync_shipments_fast(lambda m: log(m, log_file))
    board_changed, board_rows = sync_board_fast(lambda m: log(m, log_file))

    ct_changed = False
    if sync_api:
        ct_changed, _ = sync_channeltalk_fast(days=api_days, log_func=lambda m: log(m, log_file))

    any_changed = tag_changed or shipment_changed or board_changed or ct_changed or force_export

    if any_changed:
        log("▶ [4/4] VOC 웹 대시보드 실데이터(data.js, data.json) 고속 추출 중...", log_file)
        t_exp = time.time()
        try:
            from export_dashboard_data import extract_dashboard_data, resolve_db_path
            resolved_db = resolve_db_path(str(DB_PATH))
            extract_dashboard_data(resolved_db, DASHBOARD_DIR)
            log(f"  ✨ 대시보드 데이터 갱신 완료! ({time.time() - t_exp:.1f}초)", log_file)
        except Exception as e:
            log(f"  ❌ 대시보드 데이터 추출 오류: {e}", log_file)
    else:
        log("  ✓ 모든 데이터가 이미 최신 상태입니다. (대시보드 재추출 불필요)", log_file)

    total_time = time.time() - t_start
    log("=" * 60, log_file)
    log(f"🎉 [패치 완료] 총 소요 시간: {total_time:.1f}초 (변경반영: {any_changed})", log_file)
    log("=" * 60, log_file)

    return {
        "success": True,
        "changed": any_changed,
        "duration": round(total_time, 1),
        "details": {
            "shipment_changed": shipment_changed,
            "shipment_inserted": ship_ins,
            "board_changed": board_changed,
            "board_rows": board_rows,
            "channeltalk_synced": ct_changed
        }
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fast Unified VOC Sync & Patch")
    parser.add_argument("--force", action="store_true", help="Force re-export dashboard data")
    parser.add_argument("--no-api", action="store_true", help="Skip ChannelTalk API sync")
    parser.add_argument("--days", type=int, default=7, help="ChannelTalk sync days back")
    args = parser.parse_args()

    run_fast_patch(force_export=args.force, sync_api=not args.no_api, api_days=args.days)
