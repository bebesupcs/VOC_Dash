# -*- coding: utf-8 -*-
"""
run_unified_sync.py
베베숲 CX팀 통합 VOC 데이터 자동 동기화 오케스트레이터

파이프라인 순서:
1. 채널톡 Open API v5 동기화 (최신 상담, 상담원, AI응대, 요약문 파싱)
2. 배송(CJ/풀필먼트) 클레임 엑셀 증분 동기화
3. 게시판(쇼핑몰 수기접수) 일별 집계 엑셀 고속 배치 동기화
4. 대시보드 실데이터(data.js, data.json) 자동 추출 및 갱신
5. 실행 결과 및 처리 건수 로그 기록 (logs/sync_YYYYMMDD.log)
"""

from datetime import datetime
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

# 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

X_BASE = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황"
DB_PATH = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
X_SCRIPTS = Path(X_BASE) / "scripts"


def log(msg, log_file):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now_str}] {msg}"
    print(line)
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def sync_board_fast(log_file):
    """게시판 엑셀 고속 일괄 적재"""
    board_file = Path(X_BASE) / "26년" / "raw" / "게시판 데이터 원본" / "게시판_통합운영.xlsx"
    if not board_file.exists():
        log(f"  - 게시판 원본 파일 없음: {board_file}", log_file)
        return False

    sys.path.append(str(X_SCRIPTS))
    try:
        from import_boards import (
            read_board, date_parts, day_name_from_date,
            mall_columns, norm_date, clean, clean_num, mtime, now, rhash
        )

        mod_time = mtime(board_file)
        conn = sqlite3.connect(DB_PATH, timeout=60)
        
        # 이미 처리된 파일인지 mtime 확인
        row = conn.execute("""
            SELECT COUNT(*) FROM board_import_log
            WHERE source_path = ? AND file_modified_time = ? AND status = 'OK'
        """, (str(board_file), mod_time)).fetchone()

        if row and row[0] > 0:
            log("  ✓ 게시판 파일 최신 상태 (이미 반영됨, FILE SKIP)", log_file)
            conn.close()
            return True

        log(f"  ▶ 게시판 엑셀 로드 및 파싱: {board_file.name}", log_file)
        df, sheet = read_board(board_file)
        if df is None:
            log("  ❌ 게시판 시트를 읽을 수 없습니다.", log_file)
            conn.close()
            return False

        date_col = "일자"
        df = df[df["일자"].notna()].copy()
        df["__date"] = df[date_col].apply(norm_date)
        df = df[df["__date"] != ""].copy()
        malls = mall_columns(df)

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
        conn.close()
        log(f"  ✓ 게시판 {len(batch_rows)}건 고속 동기화 완료!", log_file)
        return True

    except Exception as e:
        log(f"  ❌ 게시판 동기화 실패: {e}", log_file)
        return False


def run_pipeline():
    today_str = datetime.now().strftime("%Y%m%d")
    log_file = LOGS_DIR / f"sync_{today_str}.log"

    log("=" * 65, log_file)
    log("🚀 [시작] 베베숲 CX팀 통합 VOC 일일 자동 동기화 파이프라인", log_file)
    log("=" * 65, log_file)

    # 1. 채널톡 Open API v5 동기화
    log("▶ [1/5] 채널톡 Open API v5 실시간 상담 동기화 시작...", log_file)
    try:
        sys.path.append(str(SCRIPTS_DIR))
        from sync_channeltalk_api import run_sync
        # 대시보드 추출은 마지막 단계에서 일괄 수행
        run_sync(days=14)
        log("  ✓ 채널톡 API 상담 데이터 동기화 완료", log_file)
    except Exception as e:
        log(f"  ❌ 채널톡 API 동기화 오류: {e}", log_file)

    # 2. 채널톡 CTI 통화 원장(UserChat meet data) 엑셀 증분 동기화
    log("▶ [2/5] 채널톡 CTI 전화 통화 원장(meet data) 증분 동기화 시작...", log_file)
    try:
        from sync_channel_excel_meets import sync_meet_excels
        sync_meet_excels(log_func=lambda m: log(m, log_file))
    except Exception as e:
        log(f"  ❌ CTI 통화 원장 동기화 오류: {e}", log_file)

    # 3. 배송 클레임 데이터 동기화
    log("▶ [3/5] 배송사고/클레임 데이터 동기화 시작...", log_file)
    shipment_script = X_SCRIPTS / "import_shipments.py"
    if shipment_script.exists():
        try:
            res = subprocess.run(
                [sys.executable, str(shipment_script), "--base", X_BASE, "--db", DB_PATH],
                capture_output=True,
                text=True,
                timeout=180,
                encoding="utf-8",
                errors="replace"
            )
            log("  ✓ 배송 데이터 체크 완료", log_file)
        except subprocess.TimeoutExpired:
            log("  ⚠ 배송 데이터 수집 시간 초과 (다음 단계로 진행)", log_file)
        except Exception as e:
            log(f"  ⚠ 배송 데이터 수집 실패: {e}", log_file)
    else:
        log(f"  - 배송 스크립트를 찾을 수 없습니다: {shipment_script}", log_file)

    # 4. 게시판 데이터 동기화 (고속 배치)
    log("▶ [4/5] 게시판 수기접수 데이터 동기화 시작...", log_file)
    sync_board_fast(log_file)

    # 5. VOC 대시보드 실데이터(data.js, data.json) 추출
    log("▶ [5/5] VOC 대시보드 실데이터 추출 및 갱신...", log_file)
    try:
        from export_dashboard_data import extract_dashboard_data
        extract_dashboard_data(DB_PATH, BASE_DIR / "dashboard")
        log("  ✓ 대시보드 데이터(data.js, data.json) 갱신 완료", log_file)
    except Exception as e:
        log(f"  ❌ 대시보드 데이터 추출 실패: {e}", log_file)

    log("=" * 65, log_file)
    log("✨ [완료] 전사 통합 VOC 동기화 및 대시보드 반영 완료!", log_file)
    log("=" * 65, log_file)


if __name__ == "__main__":
    run_pipeline()
