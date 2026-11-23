# -*- coding: utf-8 -*-
import re
import sys

def patch():
    with open('dashboard/engine.js', 'r', encoding='utf-8') as f:
        content = f.read()

    old_agg_pattern = r'function aggregateCti\(period\)\s*\{[\s\S]*?return\s*\{[\s\S]*?calls\s*\n\s*\};\s*\}'

    new_agg = '''function aggregateCti(period) {
  const calls = rawCti(period);
  const totalCalls = calls.length;

  let inTotal = 0;
  let inAns = 0;
  let inMissed = 0;
  let inOpMissed = 0; // 운영시간 내 부재
  let inOffMissed = 0; // 운영시간 외 (야간/주말) ARS
  let inTargetMissed = 0;
  let inNonTargetMissed = 0;

  let outAttempts = 0;
  let outAns = 0;
  let outMissed = 0;

  let talkSecSum = 0;
  let talkSecCount = 0;
  let waitSecSum = 0;
  let longCalls = 0; // 10분(600초) 이상 통화

  const missedReasonMap = {};
  const agentMap = {};

  for (const c of calls) {
    const isOut = c.dir === "outbound";
    const isIn = c.dir === "inbound" || c.dir === "missed";
    const isAnswered = c.ans === 1;

    if (isIn) {
      inTotal++;
      if (isAnswered) {
        inAns++;
      } else {
        inMissed++;
        const isOp = c.is_in_hours != null ? Boolean(c.is_in_hours) : isOperatingHour(c.time);
        if (isOp) {
          inOpMissed++;
        } else {
          inOffMissed++;
        }

        let reason = (c.reason || "").trim() || (isOp ? "상담원 대기 포기 (운영시간 내)" : "운영시간 외 ARS 안내");
        let isTarget = isOp;
        if (CTI_TARGET_REASONS.includes(reason)) {
          isTarget = true;
        } else if (reason === "대기열에서 고객 종료") {
          if (isOp) {
            isTarget = true;
            reason = "대기열 고객종료 (운영시간 내)";
          } else {
            isTarget = false;
            reason = "대기열 고객종료 (운영시간 외)";
          }
        }

        if (isTarget) inTargetMissed++;
        else inNonTargetMissed++;

        missedReasonMap[reason] = (missedReasonMap[reason] || 0) + 1;
      }
    } else if (isOut) {
      outAttempts++;
      const isAbsent = !isAnswered || (c.tag || "").includes("부재") || (c.reason || "").includes("부재");
      if (isAbsent) {
        outMissed++;
      } else {
        outAns++;
      }
    }

    if (isAnswered && c.talk > 0) {
      talkSecSum += c.talk;
      talkSecCount++;
      if (c.talk >= 600) {
        longCalls++;
      }
    }

    if (c.wait > 0) {
      waitSecSum += c.wait;
    }

    const ag = c.agent && c.agent !== "미배정" ? c.agent : (isAnswered ? "기타" : "미배정(포기호)");
    if (!agentMap[ag]) {
      agentMap[ag] = { agent: ag, inAns: 0, outAns: 0, totalAns: 0, totalTalkSec: 0, maxTalkSec: 0, missedAssigned: 0, longCalls: 0 };
    }
    if (isAnswered) {
      if (isIn) agentMap[ag].inAns++;
      if (isOut) agentMap[ag].outAns++;
      agentMap[ag].totalAns++;
      agentMap[ag].totalTalkSec += c.talk;
      if (c.talk > agentMap[ag].maxTalkSec) agentMap[ag].maxTalkSec = c.talk;
      if (c.talk >= 600) agentMap[ag].longCalls++;
    } else {
      agentMap[ag].missedAssigned++;
    }
  }

  // 제안 2번: 실제로 통화를 나눈 실통화 건수 (Answered/Connected) 중심 집계
  const realTotalCalls = inAns + outAns; // 실통화 합계 (수신 실통화 + 발신 실통화)
  const inRealTotal = inAns;             // 인바운드 수신 실통화
  const outTotal = outAns;               // 아웃바운드 발신 실통화
  const inRawTotal = inTotal;            // ARS 및 부재 포함 전체 인입 시도
  const rawTotalCalls = inTotal + outAttempts; // 전체 시도

  // 운영시간 내 실질 응답률 (Answer Rate: 응답 성공 콜 / 운영시간 내 전체 인입 대상)
  const targetCalls = inAns + inOpMissed;
  const answerRate = targetCalls > 0 ? (inAns / targetCalls) * 100 : 0;

  // 전체 인입 연결률 (Connect Rate: 응답 콜 / ARS 포함 전체 인바운드 인입)
  const connectRate = inRawTotal > 0 ? (inAns / inRawTotal) * 100 : 0;
  const outboundRate = outAttempts > 0 ? (outAns / outAttempts) * 100 : 0;

  const avgTalkSec = talkSecCount > 0 ? Math.round(talkSecSum / talkSecCount) : 0;
  const avgWaitSec = realTotalCalls > 0 ? Math.round(waitSecSum / realTotalCalls) : 0;

  const missedReasons = Object.entries(missedReasonMap)
    .map(([reason, count]) => ({ reason, count, pct: inMissed > 0 ? ((count / inMissed) * 100).toFixed(1) : "0" }))
    .sort((a, b) => b.count - a.count);

  const agentStats = Object.values(agentMap)
    .filter(a => a.agent !== "미배정(포기호)")
    .map(a => ({
      ...a,
      avgTalkSec: a.totalAns > 0 ? Math.round(a.totalTalkSec / a.totalAns) : 0
    }))
    .sort((a, b) => b.totalAns - a.totalAns);

  return {
    totalCalls: realTotalCalls, // 실질 CTI 통화 처리량 (제안 2번: 실통화 합계 inAns + outAns)
    totalConnected: realTotalCalls,
    rawTotalCalls,              // ARS 및 부재 포함 전체 시도
    inTotal: inRealTotal,       // 인바운드 수신 실통화 (inAns)
    inConnected: inAns,
    inRawTotal,                 // ARS 포함 인바운드 전체 시도
    inAns,                      // 인바운드 수신 실통화
    inMissed,                   // 전체 미연결 건수
    inOpMissed,                 // 운영시간 내 부재/대기열 포기
    inOffMissed,                // 운영시간 외 야간/주말 ARS
    inTargetMissed: inOpMissed, // 호환성
    inNonTargetMissed: inOffMissed, // 호환성
    targetCalls,                // 운영시간 내 전체 인입 (inAns + inOpMissed)
    answerRate,
    connectRate,
    inboundRate: answerRate,    // 하위 호환성 유지
    outTotal,                   // 아웃바운드 발신 실통화 (부재 제외)
    outConnected: outAns,
    outAttempts,                // 전체 발신 시도 (부재 포함)
    outAns,                     // 아웃바운드 발신 실통화
    outMissed,                  // 부재 미연결 건수
    outboundRate,
    avgTalkSec,
    avgWaitSec,
    longCalls,
    missedReasons,
    agentStats,
    calls
  };
}'''

    new_content, count = re.subn(old_agg_pattern, new_agg, content)
    print(f'aggregateCti replaced: {count}')

    new_content, count2 = re.subn(r'const calls_in = cti\.targetCalls;', 'const calls_in = cti.inTotal;', new_content)
    print(f'getRawSummary replaced: {count2}')

    if count > 0 and count2 > 0:
        with open('dashboard/engine.js', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print('SUCCESS: engine.js successfully patched!')
    else:
        print('FAILURE: regex did not match.')

if __name__ == '__main__':
    patch()
