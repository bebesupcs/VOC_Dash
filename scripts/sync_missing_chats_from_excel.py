# -*- coding: utf-8 -*-
"""
sync_missing_chats_from_excel.py
CX팀_26년_10월2주차_VOC현황.xlsb의 'UserChat data' 시트에서
2026년 누락된 채팅(미종료 채팅 76건 등)을 userchat / userchat_description에 적재
"""

import sys
import sqlite3
from pathlib import Path
import pandas as pd
import pyxlsb

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
EXCEL_PATH = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\voc 파일\CX팀_26년_10월2주차_VOC현황.xlsb"
X_SCRIPTS = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\scripts"

sys.path.append(X_SCRIPTS)
import import_channeltalk_db as icd


def run_sync():
    conn = sqlite3.connect(DB_PATH, timeout=120)
    cur = conn.cursor()

    cur.execute("SELECT id FROM userchat")
    existing_ids = set(r[0] for r in cur.fetchall() if r[0])
    print(f"▶ SQLite 현재 userchat 전체 건수: {len(existing_ids):,}건")

    print(f"▶ 공식 엑셀 스캔 시작 (2026년 데이터 대상): {EXCEL_PATH}")
    header = None
    missing_rows = []

    with pyxlsb.open_workbook(EXCEL_PATH) as wb:
        with wb.get_sheet('UserChat data') as s:
            for r_idx, row in enumerate(s.rows()):
                vals = [c.v for c in row]
                if r_idx == 0:
                    header = vals
                    continue
                if not vals or not vals[0]:
                    continue
                # 2026년 데이터만 대상 (Col 108)
                if len(vals) > 108 and vals[108] == 2026.0:
                    cid = str(vals[0]).strip()
                    if cid and cid not in existing_ids:
                        missing_rows.append(vals)

    print(f"✓ SQLite에 누락된 2026년 엑셀 채팅 건수: {len(missing_rows):,}건")
    if not missing_rows:
        print("모든 2026년 채팅이 이미 DB에 적재되어 있습니다.")
        return

    # DataFrame 생성 (기존 icd.process_userchat 규격)
    padded_rows = []
    for r in missing_rows:
        if len(r) < len(header):
            r = r + [None] * (len(header) - len(r))
        padded_rows.append(r[:len(header)])

    df = pd.DataFrame(padded_rows, columns=header)
    print(f"▶ DataFrame 변환 완료: {df.shape[0]}행 x {df.shape[1]}열")

    print("▶ icd.process_userchat 실행...")
    ins, upd, skp = icd.process_userchat(conn, df, Path(EXCEL_PATH), 'UserChat data')
    conn.commit()
    print(f"✓ process_userchat 완료: 삽입 {ins}건, 업데이트 {upd}건, 건너뜀 {skp}건")

    # 검증: 10월 2주 클레임 건수 확인
    print("\n=== 10월 2주 fact_voc 품질 클레임 정합성 검증 ===")
    cur.execute("""
        SELECT COUNT(*)
        FROM fact_voc
        WHERE year = 2026 AND month LIKE '%10%' AND week_of_month LIKE '%2%'
          AND tag_a = '물티슈'
    """)
    wipes_count = cur.fetchone()[0]
    print(f"물티슈 클레임 건수: {wipes_count}건 (공식 목표: 18건)")

    cur.execute("""
        SELECT tag_b, COUNT(*)
        FROM fact_voc
        WHERE year = 2026 AND month LIKE '%10%' AND week_of_month LIKE '%2%'
          AND tag_a = '물티슈'
        GROUP BY tag_b
        ORDER BY COUNT(*) DESC
    """)
    for r in cur.fetchall():
        print(f"  - {r[0]}: {r[1]}건")

    conn.close()

if __name__ == "__main__":
    run_sync()
