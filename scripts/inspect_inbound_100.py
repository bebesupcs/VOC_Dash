# -*- coding: utf-8 -*-
import sqlite3
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

db_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=== 10월 3주 (2026-10-15 ~ 2026-10-21) 상세 분석 ===")

print("\n[1. 전화 (콜 / CTI) - 100% 사람이 통화, AI 콜봇 없음!]")
cur.execute("""
    SELECT 
        CASE 
            WHEN direction = 'inbound' AND is_answered = 1 THEN '상담사 실제 수신 통화 (통화 성공)'
            WHEN direction = 'inbound' AND is_answered = 0 THEN '고객이 걸었으나 대기 중 종료 (부재)'
            WHEN direction = 'missed' AND missed_reason = 'notInOperation' THEN '운영시간 외 ARS 안내'
            WHEN direction = 'missed' AND missed_reason = 'workflow' THEN 'ARS 시나리오 중 종료'
            WHEN direction = 'missed' THEN '기타 부재중'
            WHEN direction = 'outbound' THEN '상담사 발신 (아웃바운드)'
        END as call_cat,
        count(*)
    FROM standard_meet
    WHERE started_at >= '2026-10-15' AND started_at <= '2026-10-21 23:59:59'
    GROUP BY call_cat
""")
for r in cur.fetchall():
    print(f"  - {r[0]}: {r[1]}건")

print("\n[2. 채팅 - 상담사 vs AI(ALF 챗봇)]")
cur.execute("""
    SELECT 
        CASE 
            WHEN is_ai_completed = 1 AND (manager_name IS NULL OR manager_name = '' OR manager_name = 'ALF') THEN 'AI 챗봇 셀프완결 (상담사 미개입)'
            WHEN is_ai_transferred = 1 THEN 'AI 챗봇에서 상담사로 이관된 채팅'
            ELSE '고객이 상담사에게 직접 인입된 채팅'
        END as chat_cat,
        direction,
        count(*)
    FROM fact_voc
    WHERE date >= '2026-10-15' AND date <= '2026-10-21'
      AND channel_type = '채팅'
      AND (customer_name NOT LIKE '%홍길동%' AND (description IS NULL OR description NOT LIKE '%테스트건%'))
    GROUP BY chat_cat, direction
""")
for r in cur.fetchall():
    print(f"  - {r[0]} ({r[1]}): {r[2]}건")

print("\n[3. 상담사별 통화 수신 건수 in 10월 3주]")
cur.execute("""
    SELECT m.name, count(*)
    FROM standard_meet s
    LEFT JOIN userchat u ON s.user_chat_id = u.id
    LEFT JOIN manager m ON COALESCE(NULLIF(s.assignee_id, ''), NULLIF(u.assigneeId, '')) = CAST(m.id AS TEXT)
    WHERE s.started_at >= '2026-10-15' AND s.started_at <= '2026-10-21 23:59:59'
      AND s.direction = 'inbound' AND s.is_answered = 1
    GROUP BY m.name
    ORDER BY count(*) DESC
""")
for r in cur.fetchall():
    print(f"  - {r[0]}: {r[1]}건")

conn.close()
