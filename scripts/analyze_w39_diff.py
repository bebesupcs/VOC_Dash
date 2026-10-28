# -*- coding: utf-8 -*-
import json

with open(r'D:\dev\VOC리포트\dashboard\data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

k = "2026-W39"
chats = d.get('CHATS_BY_WEEK', {}).get(k, [])
board = d.get('BOARD_COUNT_BY_WEEK', {}).get(k, 0)
raw = d.get('RAW_SUMMARY', {}).get(k, {})

print("=== RAW_SUMMARY ===")
print("total_offered_raw:", raw.get("total_offered_raw"))
print("raw_call:", raw.get("raw_call"))
print("raw_chat:", raw.get("raw_chat"))
print("raw_board:", raw.get("raw_board"))

print("\n=== chats 데이터 상세 ===")
print("Total chats in CHATS_BY_WEEK:", len(chats))
for c in chats[:5]:
    print(c.get("channel"), c.get("direction"), c.get("valid"), c.get("sub"), c.get("tag"))

print("\n--- 채널 & 유효성(valid) & 방향별 건수 ---")
from collections import Counter
counts = Counter((c.get("channel"), c.get("direction"), c.get("valid"), c.get("sub")) for c in chats)
for (ch, d_dir, v, sub), cnt in sorted(counts.items()):
    print(f"채널: {ch:8s} | 방향: {str(d_dir):8s} | valid: {str(v):5s} | sub: {str(sub):12s} | {cnt}건")

valid_chats = [c for c in chats if c.get('valid') and c.get('channel') != '배송접수']
print(f"\nvalid_chats (channel != 배송접수) 총합: {len(valid_chats)}")
print(f"valid 전화: {len([c for c in valid_chats if c.get('channel') == '전화'])}")
print(f"valid 채팅(상담사챗+챗봇): {len([c for c in valid_chats if c.get('channel') in ('상담사챗', '챗봇(ALF)')])}")
