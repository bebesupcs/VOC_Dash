import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\dev\VOC리포트\dashboard\data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

print("=== Dashboard Data Verification ===")
cbw = d.get('CHATS_BY_WEEK', {})

target_weeks = ['2026-W38', '2026-W39', '2026-W40', '2026-W41']
week_names = {
    '2026-W38': '9월 3주',
    '2026-W39': '9월 4주',
    '2026-W40': '10월 1주',
    '2026-W41': '10월 2주'
}

for wk in target_weeks:
    chats = cbw.get(wk, [])
    wipes_claims = [c for c in chats if c.get('valid') and c.get('nature') == '클레임' and c.get('brand') == '물티슈']
    
    # Other quality claims (홈, 패밀리, 스킨케어, 공통 제품)
    other_q = [c for c in chats if c.get('valid') and c.get('nature') == '클레임' and c.get('mid') not in ['배송', '시스템'] and (c.get('brand') in ['스킨케어', '패밀리', '헬로', '홈'] or (c.get('brand') == '공통' and c.get('mid') == '제품'))]
    
    total_q = len(wipes_claims) + len(other_q)
    print(f"\n[{week_names[wk]} ({wk})] 총 상담: {len(chats)}건 | 물티슈 품질 클레임: {len(wipes_claims)}건 | 홈/스킨/공통: {len(other_q)}건 | 품질 총합계: {total_q}건")
    
    if wk == '2026-W41':
        print("  ▶ 10월 2주 물티슈 불만 유형(중분류)별 집계 (공식 리포트 대조):")
        from collections import Counter
        mids = Counter([c.get('mid') for c in wipes_claims])
        for m, cnt in mids.most_common():
            print(f"     - {m}: {cnt}건")

# Check board counts
bc = d.get('BOARD_COUNT_BY_WEEK', {})
print("\n=== 게시판 인입 건수 (최근 5개 주차) ===")
for wk in target_weeks:
    print(f"  {week_names[wk]} ({wk}): {bc.get(wk, 0)}건")

# Check shipments
sbw = d.get('SHIPMENTS_BY_WEEK', {})
for wk in target_weeks[-1:]:
    s_list = sbw.get(wk, [])
    cold = len([s for s in s_list if s.get('vendor') == '초저온'])
    ful = len([s for s in s_list if s.get('vendor') == '풀필먼트'])
    print(f"\n=== 배송 클레임 10W2 ===\n  전체: {len(s_list)}건 (초저온 CJ: {cold}건 / 풀필먼트: {ful}건)")
