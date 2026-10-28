import sys
import sqlite3

# UTF-8 출력 강제 설정
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def update_view():
    db_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
    conn = sqlite3.connect(db_path, timeout=120)
    cur = conn.cursor()

    cur.execute("SELECT sql FROM sqlite_master WHERE name = 'fact_voc'")
    row = cur.fetchone()
    if not row:
        print("View fact_voc not found!")
        return
    old_sql = row[0]

    old_channel_snippet = """        CASE
            WHEN LOWER(TRIM(COALESCE(p.mediumName, ''))) = 'phonenumber'
                THEN '콜'
            ELSE '채팅'
        END AS channel_type,"""

    new_channel_sql = """        COALESCE(
            oco.channel_type,
            CASE
                WHEN LOWER(TRIM(COALESCE(p.mediumName, ''))) = 'phonenumber'
                    THEN '콜'
                ELSE '채팅'
            END
        ) AS channel_type,"""

    if old_channel_snippet not in old_sql:
        print("old_channel_snippet not found in old_sql!")
        return

    updated_sql = old_sql.replace(old_channel_snippet, new_channel_sql)
    # Add LEFT JOIN official_channel_override
    join_target = "LEFT JOIN manager mgr\n        ON CAST(p.assigneeId AS TEXT) = CAST(mgr.id AS TEXT)"
    if join_target in updated_sql:
        updated_sql = updated_sql.replace(
            join_target,
            join_target + "\n    LEFT JOIN official_channel_override oco\n        ON p.id = oco.id"
        )
    else:
        updated_sql += "\n    LEFT JOIN official_channel_override oco ON p.id = oco.id"

    cur.execute("DROP VIEW IF EXISTS fact_voc")
    cur.execute(updated_sql)
    conn.commit()
    print("✓ fact_voc VIEW successfully updated with official_channel_override!")

    # Verify counts for key weeks!
    test_weeks = [
        ('7월 4주', '2026-07-23'),
        ('8월 1주', '2026-07-30'),
        ('8월 2주', '2026-08-06'),
        ('9월 3주', '2026-09-17'),
        ('9월 4주', '2026-09-24'),
        ('10월 1주', '2026-10-01'),
        ('10월 2주', '2026-10-08')
    ]

    print("\n=== 검증: 주차별 건수 ===")
    for name, s_date in test_weeks:
        cur.execute("""
            SELECT 
                SUM(CASE WHEN channel_type = '콜' AND UPPER(direction) = 'INBOUND' THEN 1 ELSE 0 END) as calls_in,
                SUM(CASE WHEN channel_type = '채팅' AND UPPER(direction) IN ('INBOUND', 'OUTBOUND') THEN 1 ELSE 0 END) as chats
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
    update_view()
