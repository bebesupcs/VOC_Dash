import json
import sys

with open("dashboard/data.json", "r", encoding="utf-8") as f:
    d = json.load(f)

CTI_TARGET_REASONS = [
    "응대 가능 상담원 없음", "상담원 수신 거절", "대기열 최대 대기시간 초과",
    "링 울리는 시간 초과", "최대 대기열 수 초과", "링 울리는 중 고객 종료",
    "음성 사서함", "고객이 먼저 끊었을 때"
]

def is_target_missed(c):
    if c.get("ans") == 1:
        return False
    reason = (c.get("reason") or "").strip()
    is_op = c.get("is_in_hours", False)
    if reason in CTI_TARGET_REASONS:
        return True
    if reason == "대기열에서 고객 종료" and is_op:
        return True
    return False

print("=== 2026년 월별 실질 통화량 vs 부풀려진 기존 수치 비교 ===")
for m in d["MONTHS"]:
    if not m["key"].startswith("2026"):
        continue
    all_calls = []
    for wk in m.get("weekKeys", []):
        all_calls.extend(d.get("CTI_BY_WEEK", {}).get(wk, []))
    if not all_calls:
        continue

    in_ans = sum(1 for c in all_calls if c.get("dir") in ("inbound", "missed") and c.get("ans") == 1)
    in_target_miss = sum(1 for c in all_calls if c.get("dir") in ("inbound", "missed") and is_target_missed(c))
    in_nontarget_miss = sum(1 for c in all_calls if c.get("dir") in ("inbound", "missed") and c.get("ans") != 1 and not is_target_missed(c))
    outb = sum(1 for c in all_calls if c.get("dir") == "outbound")

    real_in = in_ans + in_target_miss
    real_total = real_in + outb

    raw_in = real_in + in_nontarget_miss
    raw_total = raw_in + outb

    lbl = m.get("label")
    m_key = m["key"]
    print(f"{m_key} ({lbl}):")
    print(f"  ● [정상] 실질 총 통화: {real_total}건 | 인바운드: {real_in}건 (응답 {in_ans} + 포기 {in_target_miss}) | 아웃: {outb}건")
    print(f"  ▲ [기존] 부풀려진 수치: {raw_total}건 (인바운드 {raw_in}건에 운영외 ARS안내 {in_nontarget_miss}건이 합산되어 부풀려짐)")
    print()
