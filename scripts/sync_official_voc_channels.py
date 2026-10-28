import sys
import sqlite3
import pyxlsb
from pathlib import Path

# UTF-8 출력 강제 설정
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def sync_channels():
    xlsb_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\voc 파일\CX팀_26년_10월2주차_VOC현황.xlsb"
    db_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"

    print(f"▶ 원본 엑셀 로드: {xlsb_path}")
    print(f"▶ 대상 SQLite DB: {db_path}")

    records = []
    with pyxlsb.open_workbook(xlsb_path) as wb:
        with wb.get_sheet(wb.sheets[5]) as s: # UserChat data
            for r_idx, row in enumerate(s.rows()):
                if r_idx > 0:
                    vals = [c.v for c in row]
                    if len(vals) > 107 and vals[0]:
                        cid = str(vals[0]).strip()
                        c100_wk = str(vals[100]).strip() if vals[100] is not None else ""
                        c106_ai = str(vals[106]).strip() if vals[106] is not None else ""
                        c107_ch = str(vals[107]).strip() if vals[107] is not None else "" # 콜 or 채팅
                        if c107_ch in ["콜", "채팅"]:
                            records.append((cid, c107_ch, c106_ai, c100_wk))

    print(f"✓ UserChat data에서 {len(records):,}건 공식 분류 추출 완료")

    conn = sqlite3.connect(db_path, timeout=120)
    cur = conn.cursor()

    # Create or update official_channel mapping table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS official_channel_override (
            id TEXT PRIMARY KEY,
            channel_type TEXT,
            is_ai TEXT,
            week_name TEXT
        )
    """)

    cur.executemany("""
        INSERT OR REPLACE INTO official_channel_override (id, channel_type, is_ai, week_name)
        VALUES (?, ?, ?, ?)
    """, records)
    conn.commit()
    print("✓ official_channel_override 테이블 저장 완료")

    # Update fact_voc channel_type based on official_channel_override
    cur.execute("""
        UPDATE fact_voc
        SET channel_type = (
            SELECT o.channel_type 
            FROM official_channel_override o 
            WHERE o.id = fact_voc.id
        )
        WHERE id IN (SELECT id FROM official_channel_override)
    """)
    updated_cnt = cur.rowcount
    conn.commit()
    print(f"✓ fact_voc 테이블 channel_type 동기화 완료: {updated_cnt:,}건 업데이트")

    # Also update alf_triggered in fact_voc and userchat if is_ai == 'AI'
    cur.execute("""
        UPDATE fact_voc
        SET alf_triggered = 'true', is_ai_completed = 1
        WHERE id IN (SELECT id FROM official_channel_override WHERE is_ai = 'AI')
    """)
    cur.execute("""
        UPDATE userchat
        SET alfTriggered = 'true'
        WHERE id IN (SELECT id FROM official_channel_override WHERE is_ai = 'AI')
    """)
    conn.commit()
    print("✓ fact_voc 및 userchat AI봇 단순종결 플래그 동기화 완료")

    # Verify weekly breakdown for key weeks
    test_weeks = [
        ('7월 4주', '2026-07-23'),
        ('8월 1주', '2026-07-30'),
        ('8월 2주', '2026-08-06'),
        ('9월 3주', '2026-09-17'),
        ('9월 4주', '2026-09-24'),
        ('10월 1주', '2026-10-01'),
        ('10월 2주', '2026-10-08')
    ]

    print("\n=== 동기화 검증: 주차별 건수 ===")
    for name, s_date in test_weeks:
        cur.execute("""
            SELECT 
                SUM(CASE WHEN channel_type = '콜' AND UPPER(direction) = 'INBOUND' THEN 1 ELSE 0 END) as calls_in,
                SUM(CASE WHEN channel_type = '채팅' AND UPPER(direction) IN ('INBOUND', 'OUTBOUND') THEN 1 ELSE 0 END) as chats,
                COUNT(*) as total_chats
            FROM fact_voc
            WHERE week_start_date = ?
        """, (s_date,))
        r = cur.fetchone()
        
        cur.execute("SELECT SUM(board_count) FROM board_daily_counts WHERE week_start_date = ?", (s_date,))
        b = cur.fetchone()[0] or 0
        
        c_in = r[0] or 0
        ch = r[1] or 0
        total = b + c_in + ch
        print(f"[{name}] 게시판: {b}, 채팅: {ch}, 콜: {c_in} => 전체: {total}")

    conn.close()

if __name__ == "__main__":
    sync_channels()
