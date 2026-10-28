# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('dashboard/engine.js', 'r', encoding='utf-8') as f:
    content = f.read()

target = """function getQualityRaw() {
  if (window.VOC_DATA && Array.isArray(window.VOC_DATA.QUALITY_RAW)) {
    return window.VOC_DATA.QUALITY_RAW;
  }
  return [];
}"""

replacement = """function getQualityRaw() {
  if (window.VOC_DATA && Array.isArray(window.VOC_DATA.QUALITY_RAW)) {
    return window.VOC_DATA.QUALITY_RAW;
  }
  return [];
}

function analyzeClaimLeadtime(period, scope = "period") {
  const all = getAllCti();
  if (!all || all.length === 0) {
    return {
      claims: [],
      summary: {
        totalClaims: 0,
        avgCalls: "0.0",
        avgDurationMin: "0.0",
        avgLeadTimeHours: "0.0",
        avgLeadTimeDays: "0.0",
        callDist: { count1: 0, count2_3: 0, count4_plus: 0 },
        leadDist: { sameDay: 0, days1_3: 0, days4_7: 0, gt7Days: 0 }
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
          if (diffDays >= 0 && diffDays <= 14.0) {
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

  return {
    claims: targetClaims,
    unmatchedRecalls,
    summary: {
      totalClaims,
      avgCalls,
      avgDurationMin: avgDurMin,
      avgLeadTimeHours: avgLeadHrs,
      avgLeadTimeDays: avgLeadDays,
      callDist: { count1, count2_3, count4_plus },
      leadDist: { sameDay, days1_3, days4_7, gt7Days }
    }
  };
}"""

if target in content:
    content = content.replace(target, replacement)
    content = content.replace("ctiForWeekKey, rawCti, aggregateCti, aggregateAlf,", "ctiForWeekKey, rawCti, aggregateCti, aggregateAlf, analyzeClaimLeadtime,")
    with open('dashboard/engine.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully patched dashboard/engine.js!")
else:
    print("Target not found in dashboard/engine.js")
