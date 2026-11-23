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

weeks = [
    ('10월 1주 (W40)', '2026-10-01', '2026-10-07', 121),
    ('10월 2주 (W41)', '2026-10-08', '2026-10-14', 174),
    ('10월 3주 (W42)', '2026-10-15', '2026-10-21', 192),
    ('10월 4주 (W43)', '2026-10-22', '2026-10-28', 133),
]

import json
with open(r'D:\dev\VOC리포트\dashboard\data.json', 'r', encoding='utf-8') as f:
    djson = json.load(f)

print("=== WEEKLY COMPARISON (DASHBOARD vs USER REPORT) ===")
for wname, start, end, user_call in weeks:
    # 1. Total standard_meet
    cur.execute(f"SELECT count(*) FROM standard_meet WHERE started_at >= '{start}' AND started_at <= '{end} 23:59:59'")
    total_meet = cur.fetchone()[0]

    # Inbound total (inbound + missed)
    cur.execute(f"SELECT count(*) FROM standard_meet WHERE started_at >= '{start}' AND started_at <= '{end} 23:59:59' AND direction IN ('inbound', 'missed')")
    in_total = cur.fetchone()[0]

    # Inbound answered
    cur.execute(f"SELECT count(*) FROM standard_meet WHERE started_at >= '{start}' AND started_at <= '{end} 23:59:59' AND direction = 'inbound' AND is_answered = 1")
    in_ans = cur.fetchone()[0]

    # Inbound missed
    cur.execute(f"SELECT count(*) FROM standard_meet WHERE started_at >= '{start}' AND started_at <= '{end} 23:59:59' AND direction = 'missed'")
    missed_cnt = cur.fetchone()[0]

    # Outbound total & ans
    cur.execute(f"SELECT count(*) FROM standard_meet WHERE started_at >= '{start}' AND started_at <= '{end} 23:59:59' AND direction = 'outbound'")
    out_total = cur.fetchone()[0]

    cur.execute(f"SELECT count(*) FROM standard_meet WHERE started_at >= '{start}' AND started_at <= '{end} 23:59:59' AND direction = 'outbound' AND is_answered = 1")
    out_ans = cur.fetchone()[0]

    # How dashboard calculated CTI for this week
    wkey = f"2026-W{wname.split('W')[1][:2]}"
    cti_items = djson.get("CTI_BY_WEEK", {}).get(wkey, [])
    dash_in = len([c for c in cti_items if c["dir"] in ("inbound", "missed")])
    dash_out = len([c for c in cti_items if c["dir"] == "outbound"])

    # Board
    cur.execute(f"SELECT sum(board_count) FROM board_daily_counts WHERE date >= '{start}' AND date <= '{end}'")
    board_cnt = cur.fetchone()[0]

    # Fact_voc chat
    cur.execute(f"SELECT count(*) FROM fact_voc WHERE date >= '{start}' AND date <= '{end}' AND channel_type = '채팅' AND (customer_name NOT LIKE '%홍길동%' AND (description IS NULL OR description NOT LIKE '%테스트건%'))")
    chat_cnt = cur.fetchone()[0]

    print(f"\n[{wname}: {start} ~ {end}]")
    print(f"  * 사용자 보고서: 콜={user_call}건")
    print(f"  * standard_meet: 전체={total_meet}건 | 인바운드총(수신+부재)={in_total}건 (수신:{in_ans}, 부재:{missed_cnt}) | 아웃바운드={out_total}건(성공:{out_ans})")
    print(f"  * 대시보드 CTI:   cti_items 전체={len(cti_items)}건 (인:{dash_in}, 아웃:{dash_out})")
    print(f"  * 게시판:        {board_cnt}건")
    print(f"  * 채팅:          {chat_cnt}건")

conn.close()
