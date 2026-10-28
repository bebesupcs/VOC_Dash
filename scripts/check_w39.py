# -*- coding: utf-8 -*-
import json

with open(r'D:\dev\VOC리포트\dashboard\data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

# 9월 4주 키 찾기
weeks = d.get('WEEKS', [])
w_target = None
for w in weeks:
    if '9월 4주' in (w.get('week_of_month') or '') or '9월 4' in (w.get('label') or ''):
        w_target = w
        break

if not w_target:
    # 2026년 9월 마지막 주차
    w_target = [w for w in weeks if w.get('year') == 2026 and '09' in w.get('month', '')][-1]

k = w_target['key']
print("Target Week:", k, w_target)

raw_sum = d.get('RAW_SUMMARY', {}).get(k, {})
op_kpi = d.get('OPERATIONAL_KPIS', {}).get(k, {})
board_cnt = d.get('BOARD_COUNT_BY_WEEK', {}).get(k, 0)
chats = d.get('CHATS_BY_WEEK', {}).get(k, [])

valid_chats = [c for c in chats if c.get('valid')]
invalid_chats = [c for c in chats if not c.get('valid')]

phone_all = [c for c in valid_chats if c.get('channel') == '전화']
phone_in = [c for c in valid_chats if c.get('channel') == '전화' and c.get('direction') == 'INBOUND']
phone_out = [c for c in valid_chats if c.get('channel') == '전화' and c.get('direction') == 'OUTBOUND']

chat_all = [c for c in valid_chats if c.get('channel') in ['상담사챗', '챗봇(ALF)']]
chat_in = [c for c in chat_all if c.get('direction') == 'INBOUND']
chat_out = [c for c in chat_all if c.get('direction') == 'OUTBOUND']

print("\n=== RAW_SUMMARY ===")
print("total_offered_raw:", raw_sum.get("total_offered_raw"))
print("raw_call:", raw_sum.get("raw_call"))
print("raw_chat:", raw_sum.get("raw_chat"))
print("raw_board:", raw_sum.get("raw_board"))

print("\n=== DB 실제 건수 (valid) ===")
print(f"전화 전체: {len(phone_all)} (IN: {len(phone_in)}, OUT: {len(phone_out)})")
print(f"채팅 전체: {len(chat_all)} (IN: {len(chat_in)}, OUT: {len(chat_out)})")
print(f"게시판: {board_cnt}")
print(f"무효(INVALID) 태그 건수: {len(invalid_chats)}")

print("\n=== 합계 비교 ===")
print(f"1) 전화IN({len(phone_in)}) + 채팅({len(chat_all)}) + 게시판({board_cnt}) = {len(phone_in) + len(chat_all) + board_cnt}")
print(f"2) 전화전체({len(phone_all)}) + 채팅({len(chat_all)}) + 게시판({board_cnt}) = {len(phone_all) + len(chat_all) + board_cnt}")
print(f"3) 무효포함 전화 + 채팅 + 게시판 = {len(chats) + board_cnt}")
print(f"4) raw_summary total_offered_raw = {raw_sum.get('total_offered_raw')}")
