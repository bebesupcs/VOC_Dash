import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('dashboard/data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

w42_chats = d.get('CHATS_BY_WEEK', {}).get('2026-W42', [])
chat_only = [c for c in w42_chats if c.get('channel') == '채팅']
counselor_chats = [c for c in chat_only if c.get('agent') and c.get('agent') not in ['ALF (AI 상담)', '미배정']]
alf_chats = [c for c in chat_only if c.get('agent') == 'ALF (AI 상담)' or c.get('alfInflow')]

print('=== 2026-W42 채팅상담 상세 분석 KPI ===')
print(f'총 채팅 접수량: {len(chat_only)}건')
print(f'상담사 직접 응대: {len(counselor_chats)}건 ({(len(counselor_chats)/len(chat_only)*100):.1f}%)')
print(f'ALF (AI 챗봇) 연동/처리: {len(alf_chats)}건')

print('\n=== 상담원별 온라인 채팅 처리 실적 차트 ===')
chat_agent_counts = {}
for c in chat_only:
    ag = c.get('agent') or '미배정'
    chat_agent_counts[ag] = chat_agent_counts.get(ag, 0) + 1
for k, v in sorted(chat_agent_counts.items(), key=lambda x: -x[1]):
    print(f'  {k}: {v}건')

print('\n=== 상담사별 종합 실적 매트릭스 (전화 / 채팅 구분) ===')
calls = d.get('CTI_BY_WEEK', {}).get('2026-W42', [])
agent_map = {}
for c in calls:
    if c.get('ans') == 1:
        ag = c.get('agent') or '미배정'
        if ag not in agent_map:
            agent_map[ag] = {'callIn': 0, 'callOut': 0, 'callTotal': 0, 'chatTotal': 0}
        if c.get('dir') == 'inbound':
            agent_map[ag]['callIn'] += 1
        elif c.get('dir') == 'outbound':
            agent_map[ag]['callOut'] += 1
        agent_map[ag]['callTotal'] += 1

for c in counselor_chats:
    ag = c.get('agent') or '미배정'
    if ag not in agent_map:
        agent_map[ag] = {'callIn': 0, 'callOut': 0, 'callTotal': 0, 'chatTotal': 0}
    agent_map[ag]['chatTotal'] += 1

total_call_ans = sum(st['callTotal'] for st in agent_map.values())
total_chat_ans = sum(st['chatTotal'] for st in agent_map.values())

for ag, st in sorted(agent_map.items(), key=lambda x: -(x[1]['callTotal'] + x[1]['chatTotal'])):
    tot = st['callTotal'] + st['chatTotal']
    cin = st['callIn']
    cout = st['callOut']
    ctot = st['callTotal']
    chattot = st['chatTotal']
    print(f'  {ag}: 전화 {ctot}건 (수신 {cin} / 발신 {cout}) + 채팅 {chattot}건 = 총 {tot}건')

print(f'\n합계: 전화 {total_call_ans}건 + 채팅 {total_chat_ans}건 = 총 {total_call_ans + total_chat_ans}건')
