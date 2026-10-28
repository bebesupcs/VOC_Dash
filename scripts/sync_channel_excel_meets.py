# -*- coding: utf-8 -*-
"""
sync_channel_excel_meets.py
채널톡 원본 엑셀(UserChat meet data / UserChat) 증분 동기화 스크립트

주요 기능:
1. 'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\채널톡 원본 데이터' 폴더 내 엑셀 스캔
2. 미적재된 파일의 'UserChat meet data' 시트를 standard_meet 및 userchat_meet에 고속 적재
3. UserChat 시트의 direction(INBOUND/OUTBOUND) 메타데이터 보정
4. import_log에 기록하여 중복 처리 방지
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
X_BASE = Path(r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황")
DB_PATH = X_BASE / "db" / "channeltalk_voc.db"
X_SCRIPTS = X_BASE / "scripts"
CH_RAW_DIR = X_BASE / "26년" / "채널톡 원본 데이터"

sys.path.append(str(X_SCRIPTS))
import import_channeltalk_db as icd


def sync_meet_excels(conn=None, log_func=print):
    close_conn = False
    if conn is None:
        conn = sqlite3.connect(str(DB_PATH), timeout=120)
        close_conn = True

    try:
        if not CH_RAW_DIR.exists():
            log_func(f"  ⚠ 채널톡 원본 폴더 없음: {CH_RAW_DIR}")
            return False

        files = sorted(CH_RAW_DIR.glob("*.xlsx"), key=lambda x: x.stat().st_mtime)
        valid_files = [f for f in files if not f.name.startswith("~$")]

        log_func(f"  ▶ 채널톡 원본 데이터 엑셀 검사: 총 {len(valid_files)}개 파일")

        # 대상: 아직 standard_meet로 적재되지 않은 파일
        todo_files = []
        for f in valid_files:
            c = conn.execute(
                "SELECT COUNT(*) FROM import_log WHERE source_path = ? AND target_table = 'standard_meet' AND status = 'OK'",
                (str(f),)
            ).fetchone()[0]
            if c == 0:
                todo_files.append(f)

        log_func(f"  ▶ 신규 CTI 통화 원장(UserChat meet data) 적재 대상: {len(todo_files)}개 파일")

        total_inserted = 0
        total_updated = 0
        total_skipped = 0

        for f in todo_files:
            log_func(f"    - 처리 중: {f.name}")
            try:
                # 1. UserChat meet data 처리
                df_meet, sheet = icd.read_sheet(f, icd.MEET_SHEETS)
                if df_meet is not None and not df_meet.empty:
                    i, u, s = icd.process_meet(conn, df_meet, f, sheet)
                    total_inserted += i
                    total_updated += u
                    total_skipped += s
                    log_func(f"      ✓ {sheet}: insert {i}, update {u}, skip {s}")
                else:
                    # meet 시트가 없는 경우 로그 기록
                    icd.log_import(conn, f, "", "standard_meet", 0, 0, 0, "OK", "meet sheet not found or empty")

                # 2. UserChat 시트의 direction 컬럼 보정 (있는 경우)
                df_uc, uc_sheet = icd.read_sheet(f, icd.USERCHAT_SHEETS)
                if df_uc is not None and not df_uc.empty and "direction" in df_uc.columns:
                    dir_updates = []
                    for _, r in df_uc.iterrows():
                        uid = str(r.get("id") or "").strip()
                        udep = str(r.get("direction") or "").strip().upper()
                        if uid and udep in ["INBOUND", "OUTBOUND"]:
                            dir_updates.append((udep, uid))
                    if dir_updates:
                        conn.executemany("UPDATE userchat SET direction = ? WHERE id = ? AND (direction IS NULL OR direction = '' OR direction != ?)",
                                         [(d, uid, d) for d, uid in dir_updates])
                        log_func(f"      ✓ {uc_sheet}: direction 보정 {len(dir_updates)}건 완료")

                conn.commit()
            except Exception as fe:
                log_func(f"      ❌ {f.name} 처리 오류: {fe}")
                conn.rollback()

        if total_inserted > 0 or total_updated > 0:
            log_func("  ▶ standard_meet Reason Flags 갱신 중...")
            icd.refresh_standard_meet_reason_flags(conn)
            conn.commit()

        log_func(f"  ✓ 채널톡 CTI 통화 원장 동기화 완료: +{total_inserted}건 추가, {total_updated}건 갱신")
        return True

    finally:
        if close_conn:
            conn.close()


if __name__ == "__main__":
    print("Starting sync_meet_excels...")
    sync_meet_excels()
