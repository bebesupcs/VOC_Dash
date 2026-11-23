(function () {



"use strict";







const { PARSED_TAGS, CHANNELS, WEEKS, MONTHS, QUARTERS = [], YEARS = [], genChatsForWeek, genBoardCount, genIssues } = window.VOC_DATA;







let initMode = "weekly";
let initIndex = (Array.isArray(WEEKS) && WEEKS.length >= 2) ? WEEKS.length - 2 : (WEEKS.length - 1);
try {
  const u = new URLSearchParams(window.location.search);
  const sMode = u.get("mode") || sessionStorage.getItem("voc_current_mode") || localStorage.getItem("voc_current_mode");
  const sWeek = u.get("week") || sessionStorage.getItem("voc_current_period_key") || localStorage.getItem("voc_current_period_key") || sessionStorage.getItem("voc_current_week") || localStorage.getItem("voc_current_week");
  if (sMode && ["weekly", "monthly", "quarterly", "yearly"].includes(sMode)) {
    initMode = sMode;
  }
  if (initMode === "weekly" && sWeek && Array.isArray(WEEKS)) {
    const foundIdx = WEEKS.findIndex(w => w.key === sWeek);
    if (foundIdx !== -1) initIndex = foundIdx;
  }
} catch (e) {}

const state = {
  mode: initMode,
  periodIndex: initIndex,
  filters: { channel: "all", journey: "all", brand: "all", nature: "all", risk: "all" },
  uniqueIssueOnly: false,
};







function getPeriodList() {



  if (state.mode === "weekly") return WEEKS;



  if (state.mode === "monthly") return MONTHS;



  if (state.mode === "quarterly") return QUARTERS;



  if (state.mode === "yearly") return YEARS;



  return WEEKS;



}







function getPeriod() {



  const list = getPeriodList();



  return list[state.periodIndex] || list[list.length - 1];



}







let _allChatsCache = null;



function getAllChats() {



  if (!_allChatsCache && window.VOC_DATA && window.VOC_DATA.CHATS_BY_WEEK) {



    _allChatsCache = Object.values(window.VOC_DATA.CHATS_BY_WEEK).flat();



  }



  return _allChatsCache || [];



}







let _allCtiCache = null;



function getAllCti() {



  if (!_allCtiCache && window.VOC_DATA && window.VOC_DATA.CTI_BY_WEEK) {



    const list = [];
    for (const wk in window.VOC_DATA.CTI_BY_WEEK) {
      for (const c of window.VOC_DATA.CTI_BY_WEEK[wk]) {
        list.push(Object.assign({ week: wk }, c));
      }
    }
    _allCtiCache = list;



  }



  return _allCtiCache || [];



}

let _allShipmentsCache = null;

function getAllShipments() {
  if (!_allShipmentsCache && window.VOC_DATA && window.VOC_DATA.SHIPMENTS_BY_WEEK) {
    _allShipmentsCache = Object.values(window.VOC_DATA.SHIPMENTS_BY_WEEK).flat();
  }
  return _allShipmentsCache || [];
}







function chatsForWeekKey(weekKey) {



  if (window.VOC_DATA && window.VOC_DATA.CHATS_BY_WEEK && window.VOC_DATA.CHATS_BY_WEEK[weekKey]) {



    return window.VOC_DATA.CHATS_BY_WEEK[weekKey];



  }



  const w = WEEKS.find((x) => x.key === weekKey);



  return typeof genChatsForWeek === "function" ? genChatsForWeek(w?.seed, w?.baseVolume) : [];



}







function rawChats(period) {



  period = period || (typeof getPeriod === "function" ? getPeriod() : null);



  if (!period) return [];



  // 1. 월간 모드: 달력 1일 00:00:00 ~ 말일 23:59:59 (인입일시 또는 접수일자 기준 전체 포함)



  if (period.key && /^\d{4}-\d{2}$/.test(period.key)) {



    const mPrefix = period.key;



    return getAllChats().filter((c) => {



      const t = c.time ? c.time.slice(0, 7) : "";



      const d = c.date ? c.date.slice(0, 7) : "";



      return t === mPrefix || d === mPrefix;



    });



  }



  // 2. 분기 모드: 해당 분기 3개 월 달력 일자 기준



  if (period.key && /^\d{4}-Q[1-4]$/.test(period.key)) {



    const y = period.key.slice(0, 4);



    const q = parseInt(period.key.slice(6), 10);



    const startM = (q - 1) * 3 + 1;



    const months = [startM, startM + 1, startM + 2].map((m) => `${y}-${String(m).padStart(2, "0")}`);



    return getAllChats().filter((c) => {



      const t = c.time ? c.time.slice(0, 7) : "";



      const d = c.date ? c.date.slice(0, 7) : "";



      return months.some((m) => t === m || d === m);



    });



  }



  // 3. 연간 모드: 해당 연도 전체 달력 일자 기준



  if (period.key && /^\d{4}$/.test(period.key)) {



    const yPrefix = period.key;



    return getAllChats().filter((c) => {



      const t = c.time ? c.time.slice(0, 4) : "";



      const d = c.date ? c.date.slice(0, 4) : "";



      return t === yPrefix || d === yPrefix;



    });



  }



  // 4. 주간 모드: 운영 주차 기준



  if (period.weekKeys && period.weekKeys.length) {



    return period.weekKeys.flatMap(chatsForWeekKey);



  }



  return chatsForWeekKey(period.key);



}







function boardCountForWeek(week) {



  if (!week) return 0;



  if (window.VOC_DATA && window.VOC_DATA.BOARD_COUNT_BY_WEEK && window.VOC_DATA.BOARD_COUNT_BY_WEEK[week.key] != null) {



    return window.VOC_DATA.BOARD_COUNT_BY_WEEK[week.key];



  }



  return typeof genBoardCount === "function" ? genBoardCount(week.seed) : 0;



}







function boardCount(period) {
  if (!period) return 0;

  // 1. 월간 모드: 달력 1일~말일 기준 엄격 적용 (10월: 805건)
  if (period.key && /^\d{4}-\d{2}$/.test(period.key)) {
    if (window.VOC_DATA && window.VOC_DATA.BOARD_COUNT_BY_MONTH && window.VOC_DATA.BOARD_COUNT_BY_MONTH[period.key] !== undefined) {
      return window.VOC_DATA.BOARD_COUNT_BY_MONTH[period.key];
    }
  }

  // 2. 분기 모드: 해당 분기 3개 월 달력 기준 엄격 적용
  if (period.key && /^\d{4}-Q[1-4]$/.test(period.key)) {
    if (window.VOC_DATA && window.VOC_DATA.BOARD_COUNT_BY_QUARTER && window.VOC_DATA.BOARD_COUNT_BY_QUARTER[period.key] !== undefined) {
      return window.VOC_DATA.BOARD_COUNT_BY_QUARTER[period.key];
    }
  }

  // 3. 연간 모드: 해당 연도 전체 달력 기준 엄격 적용
  if (period.key && /^\d{4}$/.test(period.key)) {
    if (window.VOC_DATA && window.VOC_DATA.BOARD_COUNT_BY_YEAR && window.VOC_DATA.BOARD_COUNT_BY_YEAR[period.key] !== undefined) {
      return window.VOC_DATA.BOARD_COUNT_BY_YEAR[period.key];
    }
  }

  // 4. 주간 모드: 운영 주차 기준
  if (period.weekKeys && period.weekKeys.length) {
    return period.weekKeys.reduce((s, k) => s + boardCountForWeek(WEEKS.find((x) => x.key === k)), 0);
  }

  return boardCountForWeek(WEEKS.find((x) => x.key === period.key));
}

function boardMalls(period) {
  if (!period || !window.VOC_DATA) return {};

  // 1. 월간 모드: 달력 1일~말일 기준
  if (period.key && /^\d{4}-\d{2}$/.test(period.key)) {
    if (window.VOC_DATA.BOARD_MALLS_BY_MONTH && window.VOC_DATA.BOARD_MALLS_BY_MONTH[period.key]) {
      return window.VOC_DATA.BOARD_MALLS_BY_MONTH[period.key];
    }
  }

  // 2. 분기 모드: 해당 분기 3개 월 달력 기준
  if (period.key && /^\d{4}-Q[1-4]$/.test(period.key)) {
    if (window.VOC_DATA.BOARD_MALLS_BY_QUARTER && window.VOC_DATA.BOARD_MALLS_BY_QUARTER[period.key]) {
      return window.VOC_DATA.BOARD_MALLS_BY_QUARTER[period.key];
    }
  }

  // 3. 연간 모드: 해당 연도 전체 달력 기준
  if (period.key && /^\d{4}$/.test(period.key)) {
    if (window.VOC_DATA.BOARD_MALLS_BY_YEAR && window.VOC_DATA.BOARD_MALLS_BY_YEAR[period.key]) {
      return window.VOC_DATA.BOARD_MALLS_BY_YEAR[period.key];
    }
  }

  // 4. 주간 모드: 운영 주차 기준
  if (period.weekKeys && period.weekKeys.length) {
    const res = {};
    for (const k of period.weekKeys) {
      const m = (window.VOC_DATA.BOARD_MALLS_BY_WEEK && window.VOC_DATA.BOARD_MALLS_BY_WEEK[k]) || {};
      for (const [mall, cnt] of Object.entries(m)) {
        res[mall] = (res[mall] || 0) + cnt;
      }
    }
    return res;
  }

  return (window.VOC_DATA.BOARD_MALLS_BY_WEEK && window.VOC_DATA.BOARD_MALLS_BY_WEEK[period.key]) || {};
}







function issuesForWeekKey(weekKey) {



  if (window.VOC_DATA && window.VOC_DATA.ISSUES_BY_WEEK && window.VOC_DATA.ISSUES_BY_WEEK[weekKey]) {



    return window.VOC_DATA.ISSUES_BY_WEEK[weekKey];



  }



  const w = WEEKS.find((x) => x.key === weekKey);



  return typeof genIssues === "function" ? genIssues(w?.seed) : [];



}







function shipmentsForWeekKey(weekKey) {



  if (window.VOC_DATA && window.VOC_DATA.SHIPMENTS_BY_WEEK && window.VOC_DATA.SHIPMENTS_BY_WEEK[weekKey]) {



    return window.VOC_DATA.SHIPMENTS_BY_WEEK[weekKey];



  }



  return [];



}







function rawShipments(period) {
  if (!period) return [];

  // 1. 월간 모드: 달력 1일 00:00:00 ~ 말일 23:59:59 엄격 적용
  if (period.key && /^\d{4}-\d{2}$/.test(period.key)) {
    const mPrefix = period.key;
    return getAllShipments().filter((s) => (s.claimDate && s.claimDate.startsWith(mPrefix)) || (s.date && s.date.startsWith(mPrefix)));
  }

  // 2. 분기 모드: 해당 분기 3개 월 달력 기준 엄격 적용
  if (period.key && /^\d{4}-Q[1-4]$/.test(period.key)) {
    const y = period.key.slice(0, 4);
    const q = parseInt(period.key.slice(6), 10);
    const startM = (q - 1) * 3 + 1;
    const months = [startM, startM + 1, startM + 2].map((m) => `${y}-${String(m).padStart(2, "0")}`);
    return getAllShipments().filter((s) => months.some((m) => (s.claimDate && s.claimDate.startsWith(m)) || (s.date && s.date.startsWith(m))));
  }

  // 3. 연간 모드: 해당 연도 전체 달력 기준 엄격 적용
  if (period.key && /^\d{4}$/.test(period.key)) {
    const yPrefix = period.key;
    return getAllShipments().filter((s) => (s.claimDate && s.claimDate.startsWith(yPrefix)) || (s.date && s.date.startsWith(yPrefix)));
  }

  // 4. 주간 모드: 운영 주차 기준
  if (period.weekKeys && period.weekKeys.length) {
    return period.weekKeys.flatMap(shipmentsForWeekKey);
  }

  return shipmentsForWeekKey(period.key);
}







function ctiForWeekKey(weekKey) {



  if (window.VOC_DATA && window.VOC_DATA.CTI_BY_WEEK && window.VOC_DATA.CTI_BY_WEEK[weekKey]) {



    return window.VOC_DATA.CTI_BY_WEEK[weekKey];



  }



  return [];



}







function rawCti(period) {



  if (!period) return [];



  // 1. 월간 모드: 달력 1일 00:00:00 ~ 말일 23:59:59 엄격 적용



  if (period.key && /^\d{4}-\d{2}$/.test(period.key)) {



    const mPrefix = period.key;



    return getAllCti().filter((c) => c.time && c.time.startsWith(mPrefix));



  }



  // 2. 분기 모드: 해당 분기 3개월 달력 기준 엄격 적용



  if (period.key && /^\d{4}-Q[1-4]$/.test(period.key)) {



    const y = period.key.slice(0, 4);



    const q = parseInt(period.key.slice(6), 10);



    const startM = (q - 1) * 3 + 1;



    const months = [startM, startM + 1, startM + 2].map((m) => `${y}-${String(m).padStart(2, "0")}`);



    return getAllCti().filter((c) => months.some((m) => c.time && c.time.startsWith(m)));



  }



  // 3. 연간 모드: 해당 연도 전체 달력 기준 엄격 적용



  if (period.key && /^\d{4}$/.test(period.key)) {



    const yPrefix = period.key;



    return getAllCti().filter((c) => c.time && c.time.startsWith(yPrefix));



  }



  // 4. 주간 모드: 운영 주차 기준



  if (period.weekKeys && period.weekKeys.length) {



    return period.weekKeys.flatMap(ctiForWeekKey);



  }



  return ctiForWeekKey(period.key);



}







function isOperatingHour(timeStr) {



  if (!timeStr) return false;



  const parts = timeStr.split(" ");



  if (parts.length >= 2) {



    const dParts = parts[0].split("-");



    const tParts = parts[1].split(":");



    const year = parseInt(dParts[0], 10);



    const month = parseInt(dParts[1], 10) - 1;



    const day = parseInt(dParts[2], 10);



    const hour = parseInt(tParts[0], 10);



    const min = parseInt(tParts[1], 10);



    const d = new Date(year, month, day, hour, min);



    const dow = d.getDay();



    if (dow === 0 || dow === 6) return false; // 토/일 휴무



    const totalMin = hour * 60 + min;



    return totalMin >= 600 && totalMin < 1020; // 10:00 ~ 17:00



  }



  return false;



}







const CTI_TARGET_REASONS = [



  "응대 가능 상담원 없음",



  "상담원 수신 거절",



  "대기열 최대 대기시간 초과",



  "링 울리는 시간 초과",



  "최대 대기열 수 초과",



  "링 울리는 중 고객 종료",



  "음성 사서함",



  "고객이 먼저 끊었을 때"



];







let _channelTalkMode = false;

function setChannelTalkMode(val) {
  _channelTalkMode = Boolean(val);
  if (typeof window !== "undefined") {
    window.__CHANNELTALK_MODE = _channelTalkMode;
    window.__CTI_INCLUDE_OUT_ABSENT = _channelTalkMode;
  }
}

function getChannelTalkMode() {
  if (typeof window !== "undefined" && window.__CHANNELTALK_MODE != null) {
    return window.__CHANNELTALK_MODE;
  }
  return _channelTalkMode;
}

const setOutboundIncludeAbsent = setChannelTalkMode;
const getOutboundIncludeAbsent = getChannelTalkMode;

function aggregateCti(period, options = {}) {
  const calls = rawCti(period);
  const totalCallsRaw = calls.length;

  const isCtMode = (options && options.isChannelTalkMode != null)
    ? Boolean(options.isChannelTalkMode)
    : (options && options.includeOutAbsent != null ? Boolean(options.includeOutAbsent) : getChannelTalkMode());

  let inTotal = 0;
  let inAns = 0;
  let inMissed = 0;
  let inOpMissed = 0; // 운영시간 내 부재
  let inOffMissed = 0; // 운영시간 외 (야간/주말) ARS
  let inTargetMissed = 0;
  let inNonTargetMissed = 0;
  let ivrWorkflowResolved = 0; // IVR/AI 워크플로우 자체 해결 (18건)

  let outAttempts = 0;
  let outAllAns = 0;
  let outAllMiss = 0;
  let outPureAns = 0;

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

        let reason = (c.reason || "").trim();
        let isTarget = false;
        if (reason.includes("액션") || reason.includes("워크플로우")) {
          ivrWorkflowResolved++;
          isTarget = false;
        } else if (CTI_TARGET_REASONS.includes(reason)) {
          isTarget = true;
        } else if (reason === "대기열에서 고객 종료") {
          if (isOp) {
            isTarget = true;
            reason = "대기열 고객종료 (운영시간 내)";
          } else {
            isTarget = false;
            reason = "대기열 고객종료 (운영시간 외)";
          }
        } else if (!reason) {
          reason = isOp ? "상담원 연결 전 종료" : "운영시간 외 ARS 안내";
          isTarget = false;
        } else {
          isTarget = false;
        }

        if (isTarget) inTargetMissed++;
        else inNonTargetMissed++;

        missedReasonMap[reason] = (missedReasonMap[reason] || 0) + 1;
      }
    } else if (isOut) {
      outAttempts++;
      const isAbsent = !isAnswered || (c.tag || "").includes("부재") || (c.reason || "").includes("부재");
      if (isAnswered) {
        outAllAns++;
        if (!isAbsent) {
          outPureAns++;
        }
      } else {
        outAllMiss++;
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
      agentMap[ag] = { agent: ag, inAns: 0, outAns: 0, totalAns: 0, totalTalkSec: 0, maxTalkSec: 0, missedAssigned: 0, longCalls: 0, outAttempts: 0, outMissed: 0 };
    }
    if (isOut) {
      agentMap[ag].outAttempts++;
      if (!isAnswered) agentMap[ag].outMissed++;
    }
    const isCountedOut = !isOut || (isCtMode ? isAnswered : (!((c.tag || "").includes("부재") || (c.reason || "").includes("부재"))));
    if (isAnswered && (isIn || isCountedOut)) {
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

  // 1. 순수 실통화 완료 (수신 실통화 + 발신 순수 실통화)
  const realTotalCalls = inAns + outPureAns; // W43: 56 + 37 = 93건
  // 2. 채널톡 공식 전화 수 (수신 성공 + 수신 부재 + 발신 성공 + 발신 미연결)
  const channelTalkTotal = inAns + inTargetMissed + outAllAns + outAllMiss; // W43: 56 + 6 + 48 + 27 = 137건
  
  // 모드에 따른 주요 지표 설정
  const totalCalls = isCtMode ? channelTalkTotal : realTotalCalls;
  const inRealTotal = inAns;
  const outTotal = isCtMode ? outAllAns : outPureAns;
  const outMissed = isCtMode ? outAllMiss : (outAttempts - outPureAns);
  const outAns = outTotal;
  const inRawTotal = inTotal;
  const rawTotalCalls = inTotal + outAttempts;

  // 채널톡 공식 실질 응답률 (Answer Rate: 응답 콜 / (응답 콜 + 실질 대기열 부재호))
  const targetCalls = inAns + inTargetMissed;
  const answerRate = targetCalls > 0 ? (inAns / targetCalls) * 100 : 0;

  // 전체 인입 연결률 (Connect Rate: 응답 콜 / ARS 포함 전체 인바운드 인입)
  const connectRate = inRawTotal > 0 ? (inAns / inRawTotal) * 100 : 0;
  const outboundRate = outAttempts > 0 ? (outTotal / outAttempts) * 100 : 0;

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
    totalCalls,                 // 모드 반영: 채널톡 137건 / 실통화 93건
    realTotalCalls,             // 순수 실통화 93건
    channelTalkTotal,           // 채널톡 공식 137건
    ivrWorkflowResolved,        // IVR 워크플로우 자체 해결 18건
    isChannelTalkMode: isCtMode,
    totalConnected: realTotalCalls,
    rawTotalCalls,
    inTotal: inRealTotal,
    inConnected: inAns,
    inRawTotal,
    inAns,
    inMissed,
    inOpMissed,
    inOffMissed,
    inTargetMissed,
    inNonTargetMissed,
    targetCalls,
    answerRate,
    connectRate,
    inboundRate: answerRate,
    outTotal,                   // 모드 반영: 채널톡 48건 / 실통화 37건
    outConnected: outAns,
    outAttempts,                // 75건
    outAns,
    outMissed,                  // 모드 반영: 채널톡 27건 / 실통화 38건
    outAllAns,                  // 48건
    outAllMiss,                 // 27건
    outPureAns,                 // 37건
    outPureMiss: outAttempts - outPureAns,
    outboundRate,
    includeOutAbsent: isCtMode,
    avgTalkSec,
    avgWaitSec,
    longCalls,
    missedReasons,
    agentStats,
    calls
  };
}







function applyFilters(chats) {



  const f = state.filters;



  return chats.filter((c) => {



    if (!c.valid) return false;



    if (state.uniqueIssueOnly && !c.unique_issue) return false;



    if (f.channel !== "all") {



      if (f.channel === "채팅") {



        if (c.channel !== "상담사챗" && c.channel !== "챗봇(ALF)") return false;



      } else if (c.channel !== f.channel) {



        return false;



      }



    }



    if (f.journey !== "all" && c.journey !== f.journey) return false;



    if (f.brand !== "all" && c.brand !== f.brand) return false;



    if (f.nature !== "all" && c.nature !== f.nature) return false;



    if (f.risk !== "all" && c.risk !== f.risk) return false;



    return true;



  });



}







function getRawSummary(period) {



  if (!period || !window.VOC_DATA || !window.VOC_DATA.RAW_SUMMARY) return null;
  const isCtMode = getChannelTalkMode();



  if (window.VOC_DATA.RAW_SUMMARY[period.key]) {
    const raw = window.VOC_DATA.RAW_SUMMARY[period.key];
    if (!isCtMode) {
      return raw;
    }
    const cti = aggregateCti(period, { isChannelTalkMode: true });
    const ctCall = cti.channelTalkTotal;
    const delta = ctCall - raw.raw_call;
    return Object.assign({}, raw, {
      raw_call: ctCall,
      total_offered_raw: raw.total_offered_raw + delta,
      isChannelTalkMode: true
    });
  }



  // 월간/분기/연간 모드: 달력 기준 rawChats / rawCti로 실데이터 동적 산출 (1일~말일 달력 기준 100% 일치)



  if (period.key && (/^\d{4}-\d{2}$/.test(period.key) || /^\d{4}-Q[1-4]$/.test(period.key) || /^\d{4}$/.test(period.key))) {



    const cti = aggregateCti(period);



    const chats = rawChats(period);



    const b_cnt = boardCount(period);



    const chat_in = chats.filter((c) => ["채팅", "상담사챗", "챗봇(ALF)"].includes(c.channel) && c.channel !== "배송접수" && c.direction !== "OUTBOUND").length;



    const chat_out = chats.filter((c) => ["채팅", "상담사챗", "챗봇(ALF)"].includes(c.channel) && c.channel !== "배송접수" && c.direction === "OUTBOUND").length;



    const chats_all = chat_in + chat_out;



    const calls_in = cti.inTotal;



    const calls_out = cti.outAns; // 실통화만 체크



    const calls_total = calls_in + calls_out;



    return {



      total_offered_raw: b_cnt + calls_total + chats_all,



      raw_board: b_cnt,



      raw_call: calls_total,



      raw_call_inbound: calls_in,



      raw_call_outbound: calls_out,



      raw_chat: chats_all,



      raw_chat_inbound: chat_in,



      raw_chat_outbound: chat_out



    };



  }



  if (period.weekKeys && period.weekKeys.length) {



    return period.weekKeys.reduce((acc, k) => {



      const s = window.VOC_DATA.RAW_SUMMARY[k] || {};



      acc.total_offered_raw += s.total_offered_raw || 0;



      acc.raw_board += s.raw_board || 0;



      acc.raw_call += s.raw_call || 0;



      acc.raw_call_inbound += s.raw_call_inbound != null ? s.raw_call_inbound : (s.raw_call || 0);



      acc.raw_call_outbound += s.raw_call_outbound || 0;



      acc.raw_chat += s.raw_chat || 0;



      acc.raw_chat_inbound += s.raw_chat_inbound || 0;



      acc.raw_chat_outbound += s.raw_chat_outbound || 0;



      return acc;



    }, { total_offered_raw: 0, raw_board: 0, raw_call: 0, raw_call_inbound: 0, raw_call_outbound: 0, raw_chat: 0, raw_chat_inbound: 0, raw_chat_outbound: 0 });



  }



  return window.VOC_DATA.RAW_SUMMARY[period.key] || null;



}







function getOperationalKpi(period) {



  if (!period || !window.VOC_DATA || !window.VOC_DATA.OPERATIONAL_KPIS) return null;



  if (window.VOC_DATA.OPERATIONAL_KPIS[period.key]) {



    return window.VOC_DATA.OPERATIONAL_KPIS[period.key];



  }



  // 월간/분기/연간 모드: 달력 기준 동적 산출



  if (period.key && (/^\d{4}-\d{2}$/.test(period.key) || /^\d{4}-Q[1-4]$/.test(period.key) || /^\d{4}$/.test(period.key))) {



    const cti = aggregateCti(period);



    const chats = rawChats(period);



    const in_hours_calls = cti.targetCalls;



    const in_hours_calls_ans = cti.inAns;



    const in_hours_chats = chats.filter((c) => ["채팅", "상담사챗", "챗봇(ALF)"].includes(c.channel) && ["INBOUND", "OUTBOUND"].includes(c.direction) && c.is_in_hours && c.channel !== "배송접수").length;



    const in_hours_chats_handled = in_hours_chats;



    const in_hours_offered = in_hours_calls + in_hours_chats;



    const handled_offered = in_hours_calls_ans + in_hours_chats_handled;



    let handled_contacts = chats.filter((c) => c.is_in_hours && c.valid && c.channel !== "배송접수").length;



    if (handled_offered > handled_contacts) handled_contacts = handled_offered;



    const repeat_contacts = chats.filter((c) => c.is_in_hours && c.is_repeat && c.channel !== "배송접수").length;



    const after_hours_traffic = chats.filter((c) => !c.is_in_hours && c.channel !== "배송접수").length;



    const ans_rate = in_hours_offered > 0 ? Number(((handled_offered / in_hours_offered) * 100).toFixed(1)) : 0;



    const call_ans_rate = cti.answerRate;



    const chat_ans_rate = in_hours_chats > 0 ? Number(((in_hours_chats_handled / in_hours_chats) * 100).toFixed(1)) : 0;



    const rep_rate = handled_contacts > 0 ? Number(((repeat_contacts / handled_contacts) * 100).toFixed(1)) : 0;



    return {



      in_hours_offered,



      handled_contacts,



      handled_offered,



      operational_answer_rate: ans_rate,



      call_answer_rate: call_ans_rate,



      call_in_hours_offered: in_hours_calls,



      call_in_hours_handled: in_hours_calls_ans,



      chat_answer_rate: chat_ans_rate,



      chat_in_hours_offered: in_hours_chats,



      chat_in_hours_handled: in_hours_chats_handled,



      repeat_contact_rate: rep_rate,



      repeat_contacts,



      after_hours_traffic,



      in_hours_board: boardCount(period)



    };



  }



  if (period.weekKeys && period.weekKeys.length) {



    const aggr = period.weekKeys.reduce((acc, k) => {



      const s = window.VOC_DATA.OPERATIONAL_KPIS[k] || {};



      acc.in_hours_offered += s.in_hours_offered || 0;



      acc.handled_contacts += s.handled_contacts || 0;



      acc.handled_offered += s.handled_offered || 0;



      acc.call_in_hours_offered += s.call_in_hours_offered || 0;



      acc.call_in_hours_handled += s.call_in_hours_handled || 0;



      acc.chat_in_hours_offered += s.chat_in_hours_offered || 0;



      acc.chat_in_hours_handled += s.chat_in_hours_handled || 0;



      acc.repeat_contacts += s.repeat_contacts || 0;



      acc.after_hours_traffic += s.after_hours_traffic || 0;



      acc.in_hours_board += s.in_hours_board || 0;



      return acc;



    }, {



      in_hours_offered: 0,



      handled_contacts: 0,



      handled_offered: 0,



      call_in_hours_offered: 0,



      call_in_hours_handled: 0,



      chat_in_hours_offered: 0,



      chat_in_hours_handled: 0,



      repeat_contacts: 0,



      after_hours_traffic: 0,



      in_hours_board: 0



    });



    aggr.operational_answer_rate = aggr.in_hours_offered > 0 ? Number(((aggr.handled_offered / aggr.in_hours_offered) * 100).toFixed(1)) : 0;



    aggr.call_answer_rate = aggr.call_in_hours_offered > 0 ? Number(((aggr.call_in_hours_handled / aggr.call_in_hours_offered) * 100).toFixed(1)) : 0;



    aggr.chat_answer_rate = aggr.chat_in_hours_offered > 0 ? Number(((aggr.chat_in_hours_handled / aggr.chat_in_hours_offered) * 100).toFixed(1)) : 0;



    aggr.repeat_contact_rate = aggr.handled_contacts > 0 ? Number(((aggr.repeat_contacts / aggr.handled_contacts) * 100).toFixed(1)) : 0;



    return aggr;



  }



  return window.VOC_DATA.OPERATIONAL_KPIS[period.key] || null;



}







function prevPeriod() {



  const list = getPeriodList();



  return state.periodIndex > 0 ? list[state.periodIndex - 1] : null;



}







function groupCount(chats, key) {



  const m = new Map();



  for (const c of chats) {



    const v = c[key] ?? "(미지정)";



    m.set(v, (m.get(v) || 0) + 1);



  }



  return [...m.entries()].sort((a, b) => b[1] - a[1]);



}







function avg(arr) { return arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0; }



function fmtDur(sec) {



  if (sec < 60) return `${Math.round(sec)}초`;



  return `${(sec / 60).toFixed(1)}분`;



}



function delta(cur, prev) {



  if (prev == null || prev === 0) return null;



  return ((cur - prev) / prev) * 100;



}







const JOURNEY_ORDER = ["구매전 탐색", "주문/결제", "배송/수령", "제품사용", "사후관리/클레임", "운영관리"];







// 클레임 3분류: 품질(고객여정 제품사용) / 배송 / 서비스(고객여정 사후관리/클레임)



const SERVICE_TAGS = ["강성클레임", "상급자통화", "유저인터뷰", "판매처", "시스템", "휴먼에러"];







function isQualityClaim(c) {



  if (!c) return false;



  if (c.sub === "재통화") return false;



  return c.journey === "제품사용";



}







function claimBuckets(chats) {



  if (!chats || !Array.isArray(chats)) return { quality: [], delivery: [], service: [] };



    // 1. 품질 클레임 우선 판정 (구글 시트 매핑 기준: 고객 여정이 '제품사용'인 건)
  const quality = chats.filter((c) => isQualityClaim(c));

  // 2. 배송 클레임: 품질 클레임이 아니면서 배송 채널/여정/태그에 해당하는 건
  const delivery = chats.filter((c) =>
    !quality.includes(c) && (
      c.channel === "배송접수" ||
      c.journey === "배송/수령" ||
      c.journey === "구매/배송" ||
      c.mid === "배송" ||
      (c.brand && c.brand.startsWith("배송")) ||
      (c.tag && c.tag.includes("배송"))
    )
  );



  const service = chats.filter((c) =>



    !delivery.includes(c) && !quality.includes(c) && (c.journey === "사후관리/클레임" || (c.nature === "클레임" && c.sub !== "재통화" && !c.is_repeat))



  );



  return { quality, delivery, service };



}







function getServiceCategory(c) {



  if (c.mid === "휴먼에러" || (c.tag || "").includes("휴먼에러")) return "휴먼에러";



  if (c.mid === "시스템" || (c.tag || "").includes("시스템")) return "시스템";



  if (c.mid === "상급자통화" || (c.tag || "").includes("상급자통화") || (c.tag || "").includes("강성")) return "상급자통화";



  if (c.mid === "계절성" || (c.tag || "").includes("계절성")) return "계절성";



  if ((c.tag || "").includes("품절") || (c.tag || "").includes("성분불만") || (c.tag || "").includes("정책")) return "제품불만";



  if ((c.tag || "").startsWith("단순/")) return "단순인입";



  return "제품불만";



}







function getServiceSub(c) {



  if (c.sub) return c.sub;



  if ((c.tag || "").includes("상급자통화")) return "상급자통화";



  if ((c.tag || "").includes("강성")) return "강성클레임";



  if ((c.tag || "").includes("물티슈팽창")) return "물티슈팽창";



  if (c.tag) {



    const parts = c.tag.split("/");



    const last = parts[parts.length - 1];



    if (last && last !== "단순" && last !== "클레임") return last;



  }



  return c.mid || "일반문의";



}







function aggregateAlf(period) {



  // 전화 채널은 AI 상담 대상이 아니므로 순수 채팅 인입만 엄격 필터링
  const chats = rawChats(period).filter((c) => c.valid && c.channel !== "전화" && (c.alfInflow || c.agent === "ALF (AI 상담)"));
  const totalInflow = chats.length;

  // 챗봇 자체해결 판별: 상담사 미이관 상태로 완결된 건 (agent가 ALF이거나 미배정 완결)
  const isAlfComp = (c) => c.agent === "ALF (AI 상담)" || (c.alfResolved && (!c.agent || c.agent === "미배정"));
  const completed = chats.filter(isAlfComp);
  const transferred = chats.filter((c) => !isAlfComp(c));

  const compCount = completed.length;
  const transCount = transferred.length;
  const compRate = totalInflow > 0 ? ((compCount / totalInflow) * 100).toFixed(1) : "0.0";
  const transRate = totalInflow > 0 ? ((transCount / totalInflow) * 100).toFixed(1) : "0.0";

  const csatScores = completed.map((c) => c.csat).filter((s) => s != null && s > 0);
  const avgCsat = csatScores.length ? (csatScores.reduce((a, b) => a + b, 0) / csatScores.length).toFixed(1) : "–";

  const tagMap = {};
  for (const c of chats) {
    const t = c.tag || "(미분류)";
    if (!tagMap[t]) {
      tagMap[t] = { tag: t, journey: c.journey || "–", total: 0, completed: 0, transferred: 0 };
    }
    tagMap[t].total++;
    if (isAlfComp(c)) tagMap[t].completed++;
    else tagMap[t].transferred++;
  }







  const topTags = Object.values(tagMap)



    .map((t) => ({



      ...t,



      compRate: t.total > 0 ? ((t.completed / t.total) * 100).toFixed(1) : "0.0"



    }))



    .sort((a, b) => b.total - a.total);







  return {



    totalInflow,



    compCount,



    transCount,



    compRate,



    transRate,



    avgCsat,



    topTags,



    chats



  };



}







function getQualityRaw() {



  if (window.VOC_DATA && Array.isArray(window.VOC_DATA.QUALITY_RAW)) {



    return window.VOC_DATA.QUALITY_RAW;



  }



  return [];



}







function analyzeClaimLeadtime(period, scope = "period", windowDays = 30) {



  const all = getAllCti();



  if (!all || all.length === 0) {
    return {
      claims: [],
      unmatchedRecalls: [],
      summary: {
        totalClaims: 0,
        avgCalls: "0.0",
        avgDurationMin: "0.0",
        avgLeadTimeHours: "0.0",
        avgLeadTimeDays: "0.0",
        fcrRate: "0.0",
        repeatRate: "0.0",
        callDist: { count1: 0, count2_3: 0, count4_plus: 0 },
        leadDist: { sameDay: 0, days1_3: 0, days4_7: 0, gt7Days: 0 },
        categoryBreakdown: [],
        tagBreakdown: []
      }
    };
  }







  function getCustKey(c) {



    const p = (c.phone || "").trim();



    const nm = (c.cust || "").trim();



    if (p && p !== "None" && p.includes("***")) return nm + "_" + p;



    if (p && p !== "None") return p;



    return nm || "Unknown";



  }







  const custGroups = {};



  for (const c of all) {



    if (!c.time) continue;



    const k = getCustKey(c);



    if (!custGroups[k]) custGroups[k] = [];



    custGroups[k].push(c);



  }







  function isClaimTag(t, c) {



    if (!t) return false;



    return t.includes("클레임") || t.includes("불만") || t.includes("하자") || t.includes("파손") ||



           (c && (c.journey === "제품사용" || c.journey === "품질" || c.journey === "사후관리/클레임"));



  }







  function isRecallTag(t) {



    return t && t.includes("재통화");



  }







  const allClaims = [];



  let unmatchedRecalls = 0;







  for (const k in custGroups) {



    const recs = custGroups[k];



    recs.sort((a, b) => a.time.localeCompare(b.time));







    let curClaim = null;







    for (const r of recs) {



      const t = r.tag || "";



      const isClaim = isClaimTag(t, r);



      const isRecall = isRecallTag(t);



      const rTime = new Date(r.time.replace(" ", "T"));



      const talkSec = Number(r.talk || 0) || 0;







      if (isClaim) {



        curClaim = {



          claim_id: "CLM_" + r.id,



          cust: r.cust || "소비자",



          phone: r.phone || "-",



          cust_key: k,



          first_tag: t,



          first_time: r.time,



          first_dt: rTime,



          last_time: r.time,



          last_dt: rTime,



          week: r.week || "",



          calls: [r],



          call_count: 1,



          total_talk_sec: talkSec,



          agent: r.agent || "-",



          issue: r.issue || "",



          act: r.act || "",



          journey: r.journey || ""



        };



        allClaims.push(curClaim);



      } else if (isRecall) {



        if (curClaim) {



          const diffDays = (rTime - curClaim.first_dt) / 86400000;



          if (diffDays >= 0 && diffDays <= windowDays) {



            curClaim.calls.push(r);



            curClaim.call_count += 1;



            curClaim.total_talk_sec += talkSec;



            curClaim.last_time = r.time;



            curClaim.last_dt = rTime;



            if (r.agent && curClaim.agent === "-") curClaim.agent = r.agent;



          } else {



            unmatchedRecalls++;



          }



        } else {



          unmatchedRecalls++;



        }



      }



    }



  }







  for (const c of allClaims) {



    const durMin = c.total_talk_sec / 60.0;



    c.total_call_duration = Number(durMin.toFixed(1));



    c.total_call_duration_str = `${Math.floor(c.total_talk_sec / 60)}분 ${c.total_talk_sec % 60}초`;







    const leadHrs = (c.last_dt - c.first_dt) / 3600000;



    const leadDays = leadHrs / 24.0;



    c.lead_time_hours = Number(leadHrs.toFixed(1));



    c.lead_time_days = Number(leadDays.toFixed(1));



  }







  let targetClaims = allClaims;



  if (scope === "period" && period) {



    if (period.key && /^\d{4}-\d{2}$/.test(period.key)) {



      const mPrefix = period.key;



      targetClaims = allClaims.filter(c => c.first_time && c.first_time.startsWith(mPrefix));



    } else if (period.key && /^\d{4}-Q[1-4]$/.test(period.key)) {



      const y = period.key.slice(0, 4);



      const q = parseInt(period.key.slice(6), 10);



      const startM = (q - 1) * 3 + 1;



      const months = [startM, startM + 1, startM + 2].map(m => `${y}-${String(m).padStart(2, "0")}`);



      targetClaims = allClaims.filter(c => months.some(m => c.first_time && c.first_time.startsWith(m)));



    } else if (period.key && /^\d{4}$/.test(period.key)) {



      const yPrefix = period.key;



      targetClaims = allClaims.filter(c => c.first_time && c.first_time.startsWith(yPrefix));



    } else if (period.weekKeys && period.weekKeys.length) {



      targetClaims = allClaims.filter(c => period.weekKeys.includes(c.week));



    } else if (period.key) {



      targetClaims = allClaims.filter(c => c.week === period.key);



    }



  }







  const totalClaims = targetClaims.length;



  let sumCalls = 0;



  let sumTalkSec = 0;



  let sumLeadHrs = 0;



  let count1 = 0;



  let count2_3 = 0;



  let count4_plus = 0;



  let sameDay = 0;



  let days1_3 = 0;



  let days4_7 = 0;



  let gt7Days = 0;







  for (const c of targetClaims) {



    sumCalls += c.call_count;



    sumTalkSec += c.total_talk_sec;



    sumLeadHrs += c.lead_time_hours;







    if (c.call_count === 1) count1++;



    else if (c.call_count <= 3) count2_3++;



    else count4_plus++;







    if (c.lead_time_hours <= 24.0) sameDay++;



    else if (c.lead_time_hours <= 72.0) days1_3++;



    else if (c.lead_time_hours <= 168.0) days4_7++;



    else gt7Days++;



  }







  const avgCalls = totalClaims > 0 ? (sumCalls / totalClaims).toFixed(2) : "0.0";



  const avgDurMin = totalClaims > 0 ? (sumTalkSec / 60 / totalClaims).toFixed(1) : "0.0";



  const avgLeadHrs = totalClaims > 0 ? (sumLeadHrs / totalClaims).toFixed(1) : "0.0";



  const avgLeadDays = totalClaims > 0 ? (sumLeadHrs / 24.0 / totalClaims).toFixed(1) : "0.0";



  const fcrRate = totalClaims > 0 ? ((count1 / totalClaims) * 100).toFixed(1) : "0.0";



  const repeatRate = totalClaims > 0 ? (((count2_3 + count4_plus) / totalClaims) * 100).toFixed(1) : "0.0";







  // 유형별(품질 vs 배송 vs 서비스/휴먼에러 vs 기타) 병목 분석



  const catMap = {};



  for (const c of targetClaims) {



    let cat = "기타 클레임";



    const t = c.first_tag || "";



    if (t.includes("배송")) cat = "배송 클레임 (파손/오배송/지연)";



    else if (t.includes("제품") || t.includes("품질") || t.includes("물티슈") || t.includes("패밀리") || t.includes("이취") || t.includes("원단")) cat = "제품 품질 클레임 (제조/불량/성분)";



    else if (t.includes("휴먼에러") || t.includes("세팅오류") || t.includes("오발주")) cat = "휴먼에러 (세팅/오발주)";



    else if (t.includes("시스템") || t.includes("판매처")) cat = "시스템 / 판매처 연동 오류";







    c.category = cat;







    if (!catMap[cat]) catMap[cat] = { category: cat, total: 0, repeats: 0, sumLeadHrs: 0, sumCalls: 0, sumTalkSec: 0 };



    catMap[cat].total += 1;



    if (c.call_count >= 2) catMap[cat].repeats += 1;



    catMap[cat].sumLeadHrs += c.lead_time_hours;



    catMap[cat].sumCalls += c.call_count;



    catMap[cat].sumTalkSec += c.total_talk_sec;



  }







  const categoryBreakdown = Object.values(catMap).map(m => ({
    category: m.category,
    total: m.total,
    repeats: m.repeats,
    repeatRate: ((m.repeats / m.total) * 100).toFixed(1),
    avgLeadHours: (m.sumLeadHrs / m.total).toFixed(1),
    avgLeadDays: (m.sumLeadHrs / 24.0 / m.total).toFixed(1),
    avgCalls: (m.sumCalls / m.total).toFixed(2),
    avgDurationMin: (m.sumTalkSec / 60 / m.total).toFixed(1)
  })).sort((a, b) => b.total - a.total);

  // 8. 세부 태그별 상세 리드타임 & 재통화율 랭킹
  const tagMap = {};
  for (const c of targetClaims) {
    const t = c.first_tag || '기타';
    if (!tagMap[t]) tagMap[t] = { tag: t, category: c.category, total: 0, repeats: 0, sumLeadHrs: 0, sumCalls: 0, sumTalkSec: 0 };
    tagMap[t].total += 1;
    if (c.call_count >= 2) tagMap[t].repeats += 1;
    tagMap[t].sumLeadHrs += c.lead_time_hours;
    tagMap[t].sumCalls += c.call_count;
    tagMap[t].sumTalkSec += c.total_talk_sec;
  }

  const tagBreakdown = Object.values(tagMap).map(m => {
    const repeatRate = Number(((m.repeats / m.total) * 100).toFixed(1));
    const avgLeadHours = Number((m.sumLeadHrs / m.total).toFixed(1));
    let quadrant = '3'; // 1: 최우선개선, 2: 장기검수, 3: 빠른해결, 4: 단기핑퐁
    if (repeatRate >= 20.0 && avgLeadHours >= 24.0) quadrant = '1';
    else if (repeatRate < 20.0 && avgLeadHours >= 24.0) quadrant = '2';
    else if (repeatRate < 20.0 && avgLeadHours < 24.0) quadrant = '3';
    else quadrant = '4';

    return {
      tag: m.tag,
      category: m.category,
      total: m.total,
      repeats: m.repeats,
      repeatRate,
      avgLeadHours,
      avgLeadDays: Number((m.sumLeadHrs / 24.0 / m.total).toFixed(1)),
      avgCalls: Number((m.sumCalls / m.total).toFixed(2)),
      avgDurationMin: Number((m.sumTalkSec / 60 / m.total).toFixed(1)),
      quadrant,
      r: Math.max(5, Math.min(22, Math.round(Math.sqrt(m.total) * 2.2)))
    };
  }).sort((a, b) => b.total - a.total);

  const tagQuadrantMap = {};
  tagBreakdown.forEach(t => { tagQuadrantMap[t.tag] = t.quadrant; });
  targetClaims.forEach(c => { c.quadrant = tagQuadrantMap[c.first_tag || '기타'] || '3'; });

  return {
    claims: targetClaims,
    unmatchedRecalls,
    summary: {
      totalClaims,
      avgCalls,
      avgDurationMin: avgDurMin,
      avgLeadTimeHours: avgLeadHrs,
      avgLeadTimeDays: avgLeadDays,
      fcrRate,
      repeatRate,
      callDist: { count1, count2_3, count4_plus },
      leadDist: { sameDay, days1_3, days4_7, gt7Days },
      categoryBreakdown,
      tagBreakdown
    }
  };



}







window.VOC_ENGINE = {



  state, getPeriod, getPeriodList, rawChats, rawShipments, shipmentsForWeekKey, boardCount, boardCountForWeek, boardMalls, applyFilters, prevPeriod,



  getRawSummary, getOperationalKpi, getQualityRaw,



  groupCount, avg, fmtDur, delta, chatsForWeekKey, claimBuckets, isQualityClaim, genIssues, issuesForWeekKey,



  ctiForWeekKey, rawCti, aggregateCti, aggregateAlf, analyzeClaimLeadtime,
  setOutboundIncludeAbsent, getOutboundIncludeAbsent, setChannelTalkMode, getChannelTalkMode,



  getServiceCategory, getServiceSub,



  PARSED_TAGS, CHANNELS, WEEKS, MONTHS, QUARTERS, YEARS, JOURNEY_ORDER,



};



})();



