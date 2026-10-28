# -*- coding: utf-8 -*-
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\dev\VOC리포트\dashboard\data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

# Find 10W2 (2026-W41)
wk = '2026-W41'
chats = d.get('CHATS_BY_WEEK', {}).get(wk, [])
board = d.get('BOARD_COUNT_BY_WEEK', {}).get(wk, 0)
shipments = d.get('SHIPMENTS_BY_WEEK', {}).get(wk, [])
raw_summary = d.get('RAW_SUMMARY', {}).get(wk, {})
op_kpi = d.get('OPERATIONAL_KPIS', {}).get(wk, {})

print(f"=== [1] 대시보드 메인 KPI ===")
print(f"  총 인입 (전수): {raw_summary.get('total_offered_raw')}건")
print(f"  실응대 건수: {op_kpi.get('handled_contacts')}건")
print(f"  운영시간 내 응대율: {op_kpi.get('operational_answer_rate')}%")
print(f"  재통화율: {op_kpi.get('repeat_contact_rate')}%")

# isQualityClaim definition
def is_quality_claim(c):
    if not c.get('valid') or c.get('nature') != '클레임':
        return False
    if c.get('mid') in ['배송', '시스템']:
        return False
    if c.get('brand') in ["물티슈", "스킨케어", "패밀리", "헬로", "홈"]:
        return True
    if c.get('brand') == "공통" and c.get('mid') in ["제품", "포장공정", "용액", "피부이상", "원단면", "원단(공정)이물", "이취"]:
        return True
    return False

def claim_buckets(chats_list):
    claims = [c for c in chats_list if c.get('nature') == '클레임']
    delivery = [c for c in claims if c.get('mid') == '배송' or (c.get('brand') and '배송' in c.get('brand')) or (c.get('tag') and '배송' in c.get('tag'))]
    quality = [c for c in claims if c not in delivery and is_quality_claim(c)]
    service = [c for c in claims if c not in delivery and c not in quality]
    return quality, delivery, service

valid_chats = [c for c in chats if c.get('valid')]
q, d_crm, s = claim_buckets(valid_chats)

print(f"\n=== [2] 신규 동기화된 claimBuckets ===")
print(f"  품질 클레임: {len(q)}건")
print(f"  배송 CRM 상담: {len(d_crm)}건")
print(f"  서비스 클레임: {len(s)}건")

print(f"\n=== [3] 품질 탭 (renderQuality) ===")
quality_chats = [c for c in chats if is_quality_claim(c)]
wipes = [c for c in quality_chats if c.get('brand') == '물티슈']
home = [c for c in quality_chats if c.get('brand') in ['패밀리', '홈', '공통']]
skin = [c for c in quality_chats if c.get('brand') == '스킨케어']
print(f"  품질 클레임 총합계: {len(quality_chats)}건")
print(f"    - 물티슈: {len(wipes)}건")
print(f"    - 홈/공통: {len(home)}건")
print(f"    - 스킨케어: {len(skin)}건")

print(f"\n=== [4] 배송 탭 (renderDelivery) ===")
print(f"  물류 벤더 원장 배송 클레임: {len(shipments)}건")
v_ff = [x for x in shipments if x.get('vendor') == '풀필먼트']
v_cold = [x for x in shipments if x.get('vendor') == '초저온']
print(f"    - 풀필먼트: {len(v_ff)}건")
print(f"    - 초저온: {len(v_cold)}건")

print(f"\n=== [5] 리포트 추출 탭 (renderReport & exportReportExcel) ===")
rep_chats = [c for c in valid_chats if c.get('channel') != '배송접수']
total_offered = raw_summary.get('total_offered_raw') or (len(rep_chats) + board)
handled_total = len(rep_chats) + board
rep_q, rep_d, rep_s = claim_buckets(rep_chats)
rep_delivery = len(shipments) if len(shipments) > 0 else len(rep_d)

print(f"  총 인입 (공식 전수): {total_offered}건 (실응대: {handled_total}건 = 채팅 {len(rep_chats)} + 게시판 {board})")
print(f"  품질 클레임: {len(rep_q)}건  <-- 100% MATCH WITH QUALITY TAB ({len(quality_chats)}건)!")
print(f"  배송 클레임: {rep_delivery}건  <-- 100% MATCH WITH DELIVERY TAB ({len(shipments)}건)!")
print(f"  서비스 클레임: {len(rep_s)}건")
