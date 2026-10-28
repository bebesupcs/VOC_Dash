# -*- coding: utf-8 -*-
import json

with open(r'D:\dev\VOC리포트\dashboard\data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

k = "2026-W39"
raw = d.get('RAW_SUMMARY', {}).get(k, {})
chats = d.get('CHATS_BY_WEEK', {}).get(k, [])
board = d.get('BOARD_COUNT_BY_WEEK', {}).get(k, 0)

# 1. 상단 카드 값
card_total = raw.get("total_offered_raw")
valid_chats = [c for c in chats if c.get('valid') and c.get('channel') != '배송접수']
calls_count = len([c for c in valid_chats if c.get('channel') == '전화'])
chats_count = len([c for c in valid_chats if c.get('channel') in ('상담사챗', '챗봇(ALF)')])
handled_total = calls_count + chats_count + board

print("=== 1. 상단 VOC 요약 카드 ===")
print(f"총 인입 (전수): {card_total}건")
print(f"서브 텍스트: 실응대 {handled_total}건 (콜 {calls_count} · 채팅 {chats_count} · 게시판 {board})")

# 2. 하단 2번 차트 값 (개선 후)
chart_calls = raw.get("raw_call")
chart_chats = raw.get("raw_chat")
chart_board = raw.get("raw_board")
chart_total = raw.get("total_offered_raw")

print("\n=== 2. 하단 채널별 추이 차트 (개선 후) ===")
print(f"전화(콜): {chart_calls}건")
print(f"채팅(상담사/챗봇): {chart_chats}건")
print(f"게시판: {chart_board}건")
print(f"전체 VOC 인입량 (Total): {chart_total}건")

print("\n=== 일치 여부 확인 ===")
print(f"상단 카드 총 인입 ({card_total}) == 하단 차트 Total ({chart_total}) : {card_total == chart_total}")
