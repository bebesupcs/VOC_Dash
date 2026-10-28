(function () {
"use strict";

const E = window.VOC_ENGINE;
const ACCENT = "#0f766e";
const PALETTE = ["#0f766e", "#0d9488", "#2dd4bf", "#f59e0b", "#dc2626", "#64748b"];
const charts = {};
let currentView = "dashboard";

function destroyChart(id) { if (charts[id]) { charts[id].destroy(); delete charts[id]; } }
if (window.Chart && Chart.defaults) {
  if (window.ChartDataLabels) {
    Chart.register(ChartDataLabels);
    Chart.defaults.plugins.datalabels = {
      display: function(ctx) {
        const v = ctx.dataset.data[ctx.dataIndex];
        return v != null && Number(v) > 0;
      },
      color: "#334155",
      font: {
        family: "Inter, system-ui, sans-serif",
        weight: "600",
        size: 10
      },
      formatter: function(v) {
        if (v == null || v === 0) return "";
        return Number(v).toLocaleString();
      }
    };
  }
  if (Chart.defaults.scale && Chart.defaults.scale.ticks) {
    Chart.defaults.scale.ticks.precision = 0;
  }
  if (Chart.defaults.scales && Chart.defaults.scales.linear) {
    Chart.defaults.scales.linear.ticks = Chart.defaults.scales.linear.ticks || {};
    Chart.defaults.scales.linear.ticks.precision = 0;
    Chart.defaults.scales.linear.ticks.maxTicksLimit = 4;
    Chart.defaults.scales.linear.ticks.callback = function (v) {
      return Number(v).toLocaleString();
    };
  }
}

// 고객명 마스킹 추출 및 생성 (개인정보보호 표준 준수: 김*희, 이*진 등)
const KOREAN_SURNAMES = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임", "한", "오", "서", "신", "권", "황", "안", "송", "류", "홍", "고", "문", "양", "손", "배", "백", "허", "유", "남", "심"];
const KOREAN_GIVENS = ["민", "서", "준", "진", "영", "우", "현", "지", "수", "은", "원", "호", "정", "재", "희", "하", "빈", "선", "태", "훈", "혜", "아", "경", "율", "채", "윤", "나", "솔", "린", "슬"];

function getChatCustomerName(c) {
  if (!c) return "고객";
  const directName = c.cust || c.custName || c.name || "";
  if (directName && directName !== "고객" && directName !== "-" && directName !== "–") {
    return directName;
  }
  const text = (c.issue || "") + " " + (c.act || "");
  const m1 = text.match(/([가-힣]{1,2}\*[가-힣]{1,2})(?:님|고객)?/);
  if (m1) {
    c.custName = m1[1];
    return c.custName;
  }
  const m2 = text.match(/([가-힣]{2,4})(?:님| 고객)/);
  if (m2 && m2[1].length >= 2 && m2[1].length <= 4) {
    const n = m2[1];
    if (n.length === 2) c.custName = n[0] + "*";
    else if (n.length === 3) c.custName = n[0] + "*" + n[2];
    else c.custName = n[0] + "**" + n[3];
    return c.custName;
  }
  const seed = (c.phone || "") + (c.id || "") + (c.mfg || "");
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  const sur = KOREAN_SURNAMES[hash % KOREAN_SURNAMES.length];
  const given = KOREAN_GIVENS[(hash >>> 5) % KOREAN_GIVENS.length];
  c.custName = `${sur}*${given}`;
  return c.custName;
}
const getCtiCustomerName = getChatCustomerName;

function formatMfgDate(raw) {
  if (!raw) return "–";
  const str = String(raw).trim();
  if (!str) return "–";
  // 1) 8자리 연월일 + 라인/공장코드 (예: 20241031P2 -> 20241031, 20250306T1 -> 20250306)
  const m8 = str.match(/^(\d{8})/);
  if (m8) return m8[1];
  // 2) 2027.04.23 또는 2027-04-23 형태
  const mDot = str.match(/^(\d{4})[.\-/](\d{2})[.\-/](\d{2})/);
  if (mDot) return `${mDot[1]}${mDot[2]}${mDot[3]}`;
  return str;
}

function formatPeriodDisplayLabel(p, mode) {
  if (!p) return "";
  const curMode = mode || E.state.mode;
  if (curMode === "weekly") {
    if (typeof p === "object") {
      if (p.week_of_month) return p.week_of_month;
      const wObj = (E.WEEKS || []).find((x) => x.key === p.key);
      if (wObj && wObj.week_of_month) return wObj.week_of_month;
      return (p.label || p.key || "").replace(/202[56]년\s*/, "");
    }
    const wObj = (E.WEEKS || []).find((x) => x.key === p);
    if (wObj && wObj.week_of_month) return wObj.week_of_month;
    return String(p).replace(/202[56]-W/, "") + "주";
  }
  if (curMode === "monthly") {
    const lbl = typeof p === "object" ? (p.label || p.key) : String(p);
    return lbl.replace(/202[56]년\s*/, "").trim();
  }
  if (curMode === "quarterly") {
    const lbl = typeof p === "object" ? (p.label || p.key) : String(p);
    return lbl.replace(/202[56]년\s*/, "").trim();
  }
  if (curMode === "yearly") {
    const key = typeof p === "object" ? (p.key || p.label) : String(p);
    const yr = key.slice(0, 4);
    return yr ? `${yr}년` : key;
  }
  return typeof p === "object" ? (p.label || p.key) : String(p);
}

function kpiCard(label, value, deltaPct, opts = {}) {
  const d = deltaPct;
  let badge = "";
  if (d != null) {
    const up = d >= 0;
    const good = opts.inverse ? !up : up;
    const color = d === 0 ? "text-zinc-400" : good ? "text-teal-700" : "text-red-600";
    const arrow = d > 0 ? "▲" : d < 0 ? "▼" : "–";
    badge = `<span class="tnum text-xs font-medium ${color}">${arrow} ${Math.abs(d).toFixed(0)}%</span>`;
  }
  const alert = opts.alert ? `<span class="ml-1 text-amber-500" title="주의">⚠</span>` : "";

  let tooltipEl = "";
  if (opts.tooltip) {
    tooltipEl = `
      <div class="relative group/tip inline-flex items-center">
        <span class="cursor-help rounded-full bg-zinc-100 hover:bg-zinc-200 text-zinc-600 w-3.5 h-3.5 inline-flex items-center justify-center text-[10px] font-bold ml-1 ring-1 ring-black/10">ℹ</span>
        <div class="pointer-events-none absolute top-full left-1/2 -translate-x-1/2 mt-2 hidden group-hover/tip:block z-[999] w-64 sm:w-72 rounded-lg bg-zinc-900/95 backdrop-blur-xs p-3 text-[11px] font-normal leading-relaxed text-zinc-100 shadow-2xl ring-1 ring-white/10 text-left">
          ${opts.tooltip.replace(/\n/g, '<br/>')}
          <div class="absolute -top-1.5 left-1/2 -translate-x-1/2 border-4 border-transparent border-b-zinc-900"></div>
        </div>
      </div>`;
  }

  const subTextHtml = opts.subHtml
    ? opts.subHtml
    : opts.subText
      ? `<div class="mt-1 text-[11px] text-zinc-400 font-normal truncate whitespace-nowrap">${opts.subText}</div>`
      : "";

  return `<div class="bg-white p-3.5 h-full flex flex-col justify-between">
    <div>
      <div class="flex items-center text-xs text-zinc-500">
        <span class="truncate whitespace-nowrap">${label}</span>
        ${alert}
        ${tooltipEl}
      </div>
      <div class="mt-1 flex items-baseline gap-2">
        <span class="tnum text-2xl font-semibold tracking-tight whitespace-nowrap">${value}</span>
        ${badge}
      </div>
    </div>
    ${subTextHtml}
  </div>`;
}

let anomalyIncludeInquiry = false;

function computeKPIs(chats, prevChats) {
  const period = E.getPeriod();
  const prevP = E.prevPeriod();

  const curRaw = E.getRawSummary(period);
  const prevRaw = prevP ? E.getRawSummary(prevP) : null;
  const curOp = E.getOperationalKpi(period);
  const prevOp = prevP ? E.getOperationalKpi(prevP) : null;

  const curBoard = E.boardCount(period);
  const prevBoard = prevP ? E.boardCount(prevP) : 0;

  // Visible customer contact channels: 전화, 상담사챗, 챗봇
  const curVisibleChats = chats.filter((c) => c.channel !== "배송접수");
  const prevVisibleChats = prevChats ? prevChats.filter((c) => c.channel !== "배송접수") : [];

  const chFilter = E.state.filters.channel;
  let total, prevTotal;
  if (chFilter === "전체" || chFilter === "all") {
    total = curRaw ? curRaw.total_offered_raw : (curVisibleChats.length + curBoard);
    prevTotal = prevRaw ? prevRaw.total_offered_raw : (prevChats ? prevVisibleChats.length + prevBoard : null);
  } else if (chFilter === "게시판") {
    total = curRaw ? curRaw.raw_board : curBoard;
    prevTotal = prevRaw ? prevRaw.raw_board : (prevChats ? prevBoard : null);
  } else if (chFilter === "전화") {
    total = curRaw ? curRaw.raw_call : curVisibleChats.length;
    prevTotal = prevRaw ? prevRaw.raw_call : (prevChats ? prevVisibleChats.length : null);
  } else {
    total = curRaw ? curRaw.raw_chat : curVisibleChats.length;
    prevTotal = prevRaw ? prevRaw.raw_chat : (prevChats ? prevVisibleChats.length : null);
  }

  const opWait = E.avg(chats.map((c) => c.waiting));
  const opRes = E.avg(chats.map((c) => c.resolution));
  const prevRes = prevChats ? E.avg(prevChats.map((c) => c.resolution)) : null;

  const alfInflow = chats.filter((c) => c.alfInflow);
  const alfResolved = alfInflow.filter((c) => c.alfResolved).length;
  const alfRate = alfInflow.length ? (alfResolved / alfInflow.length) * 100 : 0;
  const prevAlfInflow = prevChats ? prevChats.filter((c) => c.alfInflow) : null;
  const prevAlfRate = prevAlfInflow && prevAlfInflow.length ? (prevAlfInflow.filter((c) => c.alfResolved).length / prevAlfInflow.length) * 100 : null;

  const csats = chats.map((c) => c.csat).filter((v) => v != null && v > 0);
  const csat = E.avg(csats);
  const csatCount = csats.length;

  const high = chats.filter((c) => c.risk === "HIGH").length;
  const prevHigh = prevChats ? prevChats.filter((c) => c.risk === "HIGH").length : null;

  return {
    curRaw, prevRaw, curOp, prevOp,
    total, prevTotal, opWait, opRes, prevRes,
    alfRate, prevAlfRate, alfResolved, alfInflowCount: alfInflow.length,
    csat, csatCount, high, prevHigh
  };
}

function renderKPIs(k) {
  const row = document.getElementById("kpiRow");
  if (!row) return;

  const curRaw = k.curRaw;
  const prevRaw = k.prevRaw;
  const curOp = k.curOp;
  const prevOp = k.prevOp;

  // 1. 총 인입 (전수) - 채널톡 DB & CTI 시스템 원장 100% 일치
  const totalVal = curRaw?.total_offered_raw != null ? `${curRaw.total_offered_raw.toLocaleString()}건` : `${k.total.toLocaleString()}건`;
  const totalDelta = E.delta(curRaw?.total_offered_raw, prevRaw?.total_offered_raw);
  const totalCard = kpiCard("총 인입 (전수)", totalVal, totalDelta, {
    tooltip: `채널톡 DB 및 CTI 교환기 원장 전수 기준 인입\n• 게시판: ${(curRaw?.raw_board || 0).toLocaleString()}건\n• 콜 (CTI 전수): ${(curRaw?.raw_call || 0).toLocaleString()}건 (인 ${(curRaw?.raw_call_inbound || curRaw?.raw_call || 0).toLocaleString()} / 아웃 ${(curRaw?.raw_call_outbound || 0).toLocaleString()})\n• 채팅 (인/아웃): ${(curRaw?.raw_chat || 0).toLocaleString()}건`,
    subText: `게시판 ${curRaw?.raw_board || 0} · 콜 ${curRaw?.raw_call || 0} · 채팅 ${curRaw?.raw_chat || 0}`
  });

  // 2. 실응대 건수 (재통화 포함)
  const handledVal = curOp?.handled_contacts != null ? `${curOp.handled_contacts.toLocaleString()}건` : "–";
  const handledDelta = E.delta(curOp?.handled_contacts, prevOp?.handled_contacts);
  const handledCard = kpiCard("실응대 (재통화 포함)", handledVal, handledDelta, {
    tooltip: `운영시간 내(평일 09~17시) 상담팀이 실제 완료한 유효 응대 건수\n• 일반 유효 문의 + 재통화 포함 (실제 업무 공수 반영)\n• 무효(테스트/오발신/부재/인입후끊김) 제외`,
    subText: `운영시간 내 유효 응대 실적`
  });

  // 3. 전화 응대율 (콜) - 사용자 원칙: "응대율은 전화로 보자, 대시보드에는 전화/채팅 값도 따로 보여주자"
  const callRate = curOp?.call_answer_rate ?? (curOp?.operational_answer_rate ?? 0);
  const prevCallRate = prevOp?.call_answer_rate ?? prevOp?.operational_answer_rate ?? null;
  const callAnsVal = `${callRate.toFixed(1)}%`;
  const callAnsDelta = prevCallRate != null ? callRate - prevCallRate : null;

  const callOffered = curOp?.call_in_hours_offered ?? curRaw?.raw_call_inbound ?? 0;
  const callHandled = curOp?.call_in_hours_handled ?? 0;
  const chatOffered = curOp?.chat_in_hours_offered ?? curRaw?.raw_chat ?? 0;
  const chatHandled = curOp?.chat_in_hours_handled ?? 0;
  const chatRate = curOp?.chat_answer_rate ?? 100.0;
  const chatAnsVal = `${chatRate.toFixed(1)}%`;
  const totalAnsRate = curOp?.operational_answer_rate != null ? `${curOp.operational_answer_rate.toFixed(1)}%` : "–";

  const ansCard = kpiCard("전화 응대율 (콜)", callAnsVal, callAnsDelta, {
    alert: callRate < 80,
    tooltip: `채널별 세부 응대 실적\n• [전화(콜)] 실질 응대율: ${callAnsVal} (${callHandled.toLocaleString()}건 응답 / ${callOffered.toLocaleString()}건 인입)\n• [채팅] 실질 응대율: ${chatAnsVal} (${chatHandled.toLocaleString()}건 완료 / ${chatOffered.toLocaleString()}건 인입)\n• [통합] 운영시간 내 전체 응대율: ${totalAnsRate} (${(curOp?.handled_offered || 0).toLocaleString()}건 / ${(curOp?.in_hours_offered || 0).toLocaleString()}건)`,
    subHtml: `
      <div class="mt-1 flex items-center justify-between text-[10.5px] text-zinc-500 font-medium whitespace-nowrap gap-1">
        <span class="inline-flex items-center px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 font-semibold ring-1 ring-emerald-600/20" title="전화 인바운드 콜 실질 응대율: ${callAnsVal} (${callHandled}건 / ${callOffered}건)">전화 ${callAnsVal} <span class="text-emerald-600/70 font-normal ml-0.5">(${callHandled})</span></span>
        <span class="inline-flex items-center px-1.5 py-0.5 rounded bg-blue-50 text-blue-800 font-semibold ring-1 ring-blue-600/20" title="온라인 채팅 상담 응대율: ${chatAnsVal} (${chatHandled}건 / ${chatOffered}건)">채팅 ${chatAnsVal} <span class="text-blue-600/70 font-normal ml-0.5">(${chatHandled})</span></span>
      </div>`
  });

  // 4. 재통화율 (FCR 품질)
  const repVal = curOp?.repeat_contact_rate != null ? `${curOp.repeat_contact_rate.toFixed(1)}%` : "–";
  const repDelta = (curOp?.repeat_contact_rate != null && prevOp?.repeat_contact_rate != null)
    ? curOp.repeat_contact_rate - prevOp.repeat_contact_rate
    : null;
  const repCard = kpiCard("재통화율", repVal, repDelta, {
    inverse: true,
    alert: curOp?.repeat_contact_rate != null && curOp.repeat_contact_rate > 20,
    tooltip: `실응대 건수 중 재통화(재인입) 상담이 차지하는 비율 (FCR 품질 관리 지표)\n(산식: 재통화 건수 ÷ 실응대 건수 × 100)\n• 재통화 발생: ${(curOp?.repeat_contacts || 0).toLocaleString()}건\n• 전체 실응대: ${(curOp?.handled_contacts || 0).toLocaleString()}건`,
    subText: `재통화 ${curOp?.repeat_contacts || 0}건 / 실응대 ${curOp?.handled_contacts || 0}건`
  });

  // 5. 챗봇(ALF) 완결율
  const alfDelta = k.prevAlfRate != null ? k.alfRate - k.prevAlfRate : null;
  const alfCard = kpiCard("챗봇(ALF) 완결율", `${k.alfRate.toFixed(1)}%`, alfDelta, {
    alert: k.alfRate < 30,
    tooltip: "챗봇(ALF)으로 인입된 상담 중 상담사 연결로 이관되지 않고 챗봇 단계에서 해결·종료된 비율\n(산식: 자체완결 건수 ÷ 챗봇 총 인입 건수 × 100)",
    subText: `완결 ${k.alfResolved}건 / 총 ${k.alfInflowCount}건`
  });

  // 6. 운영 외 인입
  const afterVal = curOp?.after_hours_traffic != null ? `${curOp.after_hours_traffic.toLocaleString()}건` : "–";
  const afterDelta = E.delta(curOp?.after_hours_traffic, prevOp?.after_hours_traffic);
  const afterCard = kpiCard("운영 외 인입", afterVal, afterDelta, {
    inverse: true,
    tooltip: `상담 운영시간 외(야간, 주말, 공휴일) 발생한 총 인입 시도 건수\n• 상담팀 응대율 분모에서 분리하여 왜곡 방지\n• 야간 챗봇/콜백 및 채널 운영 확장 검토용 지표`,
    subText: `야간 · 주말 인입 트래픽`
  });

  row.innerHTML = totalCard + handledCard + ansCard + repCard + alfCard + afterCard;
}

function renderAnomaly(chats, prevChats) {
  const box = document.getElementById("anomaly");
  if (!box) return;
  if (!prevChats) { box.innerHTML = ""; return; }

  // Filter based on toggle: default is claims only, toggle adds simple inquiries
  const curTargetChats = anomalyIncludeInquiry ? chats : chats.filter((c) => c.nature === "클레임");
  const prevTargetChats = anomalyIncludeInquiry ? prevChats : prevChats.filter((c) => c.nature === "클레임");

  const cur = Object.fromEntries(E.groupCount(curTargetChats, "tag"));
  const prev = Object.fromEntries(E.groupCount(prevTargetChats, "tag"));
  const alerts = [];
  for (const [tag, c] of Object.entries(cur)) {
    const p = prev[tag] || 0;
    if (c >= 3 && (p === 0 || (c - p) / p >= 0.4)) {
      const pct = p === 0 ? "신규" : `+${(((c - p) / p) * 100).toFixed(0)}%`;
      const sample = curTargetChats.find((x) => x.tag === tag);
      const risk = sample?.risk;
      const nature = sample?.nature || "클레임";
      alerts.push({ tag, c, p, pct, risk, nature });
    }
  }
  alerts.sort((a, b) => (b.risk === "HIGH") - (a.risk === "HIGH") || b.c - a.c);

  const toggleCheck = anomalyIncludeInquiry ? "☑" : "☐";
  const toggleBtnClass = anomalyIncludeInquiry
    ? "bg-teal-50 text-teal-800 ring-teal-600/30 font-semibold"
    : "bg-white text-zinc-600 ring-black/10 hover:bg-zinc-50";

  box.innerHTML = `<div class="rounded-xl bg-amber-50/80 p-4 ring-1 ring-amber-200">
    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-amber-200/60 pb-2.5">
      <div class="flex items-center gap-2">
        <h2 class="text-sm font-semibold text-amber-900 flex items-center gap-1.5">
          <span class="inline-block w-2 h-2 rounded-full bg-amber-500 animate-ping"></span>
          ⚠ 이상징후 · 전기간 대비 급증 모니터링
        </h2>
        <span class="rounded bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800">
          ${anomalyIncludeInquiry ? "클레임 + 단순문의 전체" : "클레임 태그 전용"}
        </span>
      </div>
      <button id="toggleAnomalyInquiry" type="button" class="inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium ring-1 shadow-sm transition ${toggleBtnClass}">
        <span class="tnum font-bold">${toggleCheck}</span>
        <span>단순(문의) 태그 포함하기</span>
      </button>
    </div>
    <ul class="mt-2.5 space-y-1.5" role="list">
      ${
        alerts.length
          ? alerts.slice(0, 6).map((a) => {
              const riskBadge = a.risk === "HIGH"
                ? '<span class="rounded bg-red-600 px-1.5 py-0.5 text-[10px] font-semibold text-white">HIGH</span>'
                : (a.nature === "클레임"
                    ? '<span class="rounded bg-amber-600 px-1.5 py-0.5 text-[10px] font-medium text-white">클레임</span>'
                    : '<span class="rounded bg-zinc-200 px-1.5 py-0.5 text-[10px] font-medium text-zinc-700">단순문의</span>');
              return `<li class="flex items-center justify-between gap-2 text-sm bg-white/60 rounded-lg px-2.5 py-1 ring-1 ring-amber-900/5">
                <div class="flex items-center gap-2 truncate">
                  ${riskBadge}
                  <span class="text-zinc-800 font-medium truncate">${a.tag}</span>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                  <span class="tnum font-semibold text-rose-600">${a.pct}</span>
                  <span class="tnum text-xs text-zinc-400">(${a.p.toLocaleString()} → ${a.c.toLocaleString()}건)</span>
                </div>
              </li>`;
            }).join("")
          : '<li class="text-xs text-zinc-500 py-1">급증 이상징후가 감지되지 않았습니다.</li>'
      }
    </ul>
  </div>`;

  const btn = document.getElementById("toggleAnomalyInquiry");
  if (btn) {
    btn.addEventListener("click", () => {
      anomalyIncludeInquiry = !anomalyIncludeInquiry;
      renderAnomaly(chats, prevChats);
    });
  }
}

function barChart(id, labels, data, opts = {}) {
  destroyChart(id);
  const isHoriz = !!opts.horizontal;
  const sum = data.reduce((a, b) => a + (Number(b) || 0), 0);

  charts[id] = new Chart(document.getElementById(id), {
    type: "bar",
    data: { labels, datasets: [{ data, backgroundColor: opts.colors || ACCENT, borderRadius: 4 }] },
    options: {
      indexAxis: isHoriz ? "y" : "x",
      layout: {
        padding: isHoriz ? { right: opts.showPercentage ? 80 : 50 } : { top: 22 }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (item) => {
              const val = Number(item.raw != null ? item.raw : 0);
              const pct = sum > 0 ? ((val / sum) * 100).toFixed(1) : "0.0";
              const prefix = item.dataset.label ? item.dataset.label + ': ' : '';
              return `${prefix}${val.toLocaleString()}건 (${pct}%)`;
            }
          }
        },
        datalabels: {
          display: (ctx) => {
            const v = ctx.dataset.data[ctx.dataIndex];
            return v != null && v > 0;
          },
          color: isHoriz ? "#1e293b" : "#334155",
          anchor: isHoriz ? "end" : "end",
          align: isHoriz ? "end" : "top",
          offset: 3,
          font: { weight: "600", size: 10 },
          formatter: (v) => {
            if (!v) return "";
            if (opts.showPercentage && sum > 0) {
              const pct = ((v / sum) * 100).toFixed(1);
              return `${Number(v).toLocaleString()}건 (${pct}%)`;
            }
            return `${Number(v).toLocaleString()}건`;
          }
        }
      },
      scales: {
        x: {
          grid: { display: isHoriz, color: "rgba(0,0,0,.05)" },
          ticks: {
            font: { size: 11 },
            precision: 0,
            ...(isHoriz ? {
              maxTicksLimit: 4,
              callback: (v) => Number(v).toLocaleString()
            } : {})
          },
          beginAtZero: true,
          ...(isHoriz ? { grace: "15%" } : {})
        },
        y: {
          grid: { display: !isHoriz, color: "rgba(0,0,0,.05)" },
          ticks: {
            font: { size: 11 },
            precision: 0,
            ...(!isHoriz ? {
              maxTicksLimit: 4,
              callback: (v) => Number(v).toLocaleString()
            } : {})
          },
          beginAtZero: true,
          ...(!isHoriz ? { grace: "15%" } : {})
        }
      },
      onClick: opts.onClick,
      responsive: true,
      maintainAspectRatio: false,
    },
  });
}

function doughnutChart(id, labels, data) {
  destroyChart(id);
  const sum = data.reduce((a, b) => a + (Number(b) || 0), 0);

  charts[id] = new Chart(document.getElementById(id), {
    type: "doughnut",
    data: { labels, datasets: [{ data, backgroundColor: PALETTE, borderWidth: 1, borderColor: "#ffffff" }] },
    options: {
      cutout: "62%",
      plugins: {
        legend: { position: "right", labels: { font: { size: 11 }, boxWidth: 10 } },
        tooltip: {
          callbacks: {
            label: (item) => {
              const val = Number(item.raw != null ? item.raw : 0);
              const pct = sum > 0 ? ((val / sum) * 100).toFixed(1) : "0.0";
              return `${item.label}: ${val.toLocaleString()}건 (${pct}%)`;
            }
          }
        },
        datalabels: {
          display: (ctx) => {
            const v = ctx.dataset.data[ctx.dataIndex];
            return v > 0 && sum > 0 && (v / sum >= 0.04);
          },
          color: "#ffffff",
          font: { weight: "bold", size: 10 },
          formatter: (val) => {
            const pct = sum > 0 ? ((val / sum) * 100).toFixed(1) : "0.0";
            return `${Number(val).toLocaleString()}건\n(${pct}%)`;
          },
          textAlign: "center"
        }
      },
      responsive: true,
      maintainAspectRatio: false
    },
  });
}

function lineChart(id, labels, datasets) {
  destroyChart(id);
  charts[id] = new Chart(document.getElementById(id), {
    type: "line",
    data: { labels, datasets: datasets.map((d, i) => ({ ...d, borderColor: PALETTE[i], backgroundColor: PALETTE[i], tension: 0.3, borderWidth: 2, pointRadius: 3, pointHoverRadius: 5 })) },
    options: {
      layout: {
        padding: { top: 22 }
      },
      plugins: {
        datalabels: { display: false },
        legend: { position: "top", labels: { font: { size: 11 }, boxWidth: 10 } },
        tooltip: {
          callbacks: {
            label: (item) => `${item.dataset.label ? item.dataset.label + ': ' : ''}${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`
          }
        },
        datalabels: {
          display: (ctx) => {
            const v = ctx.dataset.data[ctx.dataIndex];
            return v != null && v > 0;
          },
          align: "top",
          anchor: "end",
          offset: 2,
          font: { size: 9.5, weight: "600" },
          color: (ctx) => ctx.dataset.borderColor || "#334155",
          formatter: (v) => `${Number(v).toLocaleString()}건`
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 } } },
        y: {
          grid: { color: "rgba(0,0,0,.05)" },
          beginAtZero: true,
          grace: "15%",
          ticks: {
            font: { size: 10 },
            precision: 0,
            maxTicksLimit: 4,
            callback: (v) => Number(v).toLocaleString()
          }
        }
      },
      responsive: true,
      maintainAspectRatio: false
    },
  });
}

let midDrill = null;
function renderMain(chats) {
  const prevP = E.prevPeriod();
  const prevChats = prevP ? E.rawChats(prevP).filter((c) => c.valid) : [];
  const curJmap = Object.fromEntries(E.groupCount(chats, "journey"));
  const prevJmap = Object.fromEntries(E.groupCount(prevChats, "journey"));

  const jLabels = E.JOURNEY_ORDER;
  barChart("journeyChart", jLabels, jLabels.map((j) => curJmap[j] || 0), { horizontal: true });

  const jTableBody = document.getElementById("journeyDeltaTableBody");
  if (jTableBody) {
    jTableBody.innerHTML = jLabels.map((j) => {
      const c = curJmap[j] || 0;
      const p = prevJmap[j] || 0;
      const diff = c - p;
      let badge = `<span class="tnum text-zinc-400">– 0%</span>`;
      if (diff > 0) {
        const pct = p > 0 ? `+${(((c - p) / p) * 100).toFixed(0)}%` : "신규";
        badge = `<span class="tnum text-rose-600 font-semibold">▲ ${diff.toLocaleString()} <span class="text-[10px]">(${pct})</span></span>`;
      } else if (diff < 0) {
        const pct = p > 0 ? `${(((c - p) / p) * 100).toFixed(0)}%` : "0%";
        badge = `<span class="tnum text-teal-700 font-semibold">▼ ${Math.abs(diff).toLocaleString()} <span class="text-[10px]">(${pct})</span></span>`;
      }
      return `<tr class="hover:bg-zinc-50/50">
        <td class="py-1.5 px-2 font-medium text-zinc-800">${j}</td>
        <td class="py-1.5 px-1 text-right tnum text-zinc-400">${p.toLocaleString()}</td>
        <td class="py-1.5 px-1 text-right tnum font-semibold text-zinc-900">${c.toLocaleString()}</td>
        <td class="py-1.5 px-2 text-right">${badge}</td>
      </tr>`;
    }).join("");
  }

  const channelChats = chats.filter((c) => c.channel !== "배송접수");
  const cc = E.groupCount(channelChats, "channel");
  doughnutChart("channelChart", cc.map((x) => x[0]), cc.map((x) => x[1]));

  // 상담(전화+채팅) 인입/발신 문의 유형(태그)별 증감 분석
  renderMainTagAnalysis(chats, prevChats);

  if (midDrill) {
    const subs = E.groupCount(chats.filter((c) => c.mid === midDrill), "sub").filter((x) => x[0] !== "(미지정)");
    document.getElementById("drillHint").textContent = `← ${midDrill} 소분류 (클릭해 복귀)`;
    barChart("midChart", subs.map((x) => x[0]), subs.map((x) => x[1]), {
      horizontal: true, colors: "#0d9488",
      onClick: () => { midDrill = null; renderMain(window._curChats); },
    });
  } else {
    const mids = E.groupCount(chats, "mid").filter((x) => x[0] !== "(미지정)").slice(0, 10);
    document.getElementById("drillHint").textContent = "막대 클릭 → 소분류 드릴다운";
    barChart("midChart", mids.map((x) => x[0]), mids.map((x) => x[1]), {
      horizontal: true,
      onClick: (_evt, els) => { if (els.length) { midDrill = mids[els[0].index][0]; renderMain(window._curChats); } },
    });
  }

  const brandCard = document.getElementById("brandChartCard");
  const brandEl = document.getElementById("brandChart");
  if (brandEl && brandCard && !brandCard.classList.contains("hidden")) {
    const claims = chats.filter((c) => c.nature === "클레임");
    const bc = E.groupCount(claims, "brand").filter((x) => x[0] !== "(미지정)");
    barChart("brandChart", bc.map((x) => x[0]), bc.map((x) => x[1]), { colors: "#dc2626" });
  } else {
    destroyChart("brandChart");
  }
}

function renderTrend() {
  const list = E.getPeriodList();
  // 4주, 4개월, 4분기, 2년
  const lookback = E.state.mode === "weekly" ? 4 : (E.state.mode === "monthly" ? 4 : (E.state.mode === "quarterly" ? 4 : 2));
  const recent = list.slice(Math.max(0, E.state.periodIndex - lookback + 1), E.state.periodIndex + 1);
  const curPeriod = E.getPeriod();
  const labels = recent.map((w) => {
    const dispLabel = formatPeriodDisplayLabel(w, E.state.mode);
    return w.key === curPeriod.key ? `${dispLabel} (선택)` : dispLabel;
  });

  const callSeries = [], chatSeries = [], boardSeries = [], totalSeries = [];
  for (const p of recent) {
    const raw = E.getRawSummary(p);
    let calls, chatsCnt, b, total;
    if (raw) {
      calls = raw.raw_call;
      chatsCnt = raw.raw_chat;
      b = raw.raw_board;
      total = raw.total_offered_raw;
    } else {
      const cs = E.rawChats(p).filter((c) => c.valid && c.channel !== "배송접수");
      b = E.boardCount(p);
      // 전화: 순수 인바운드 건수만 인입 추이에 포함 (아웃바운드 제외)
      calls = cs.filter((c) => c.channel === "전화" && (c.direction || "INBOUND") === "INBOUND").length;
      // 채팅: 인바운드 & 아웃바운드 모두 포함
      chatsCnt = cs.filter((c) => (c.channel === "상담사챗" || c.channel === "챗봇(ALF)") && (c.direction === "INBOUND" || c.direction === "OUTBOUND")).length;
      total = calls + chatsCnt + b;
    }

    callSeries.push(calls);
    chatSeries.push(chatsCnt);
    boardSeries.push(b);
    totalSeries.push(total);
  }

  destroyChart("trendChart");
  const el = document.getElementById("trendChart");
  if (!el) return;

  const trendDataLabelsPlugin = {
    id: "trendDataLabels",
    afterDatasetsDraw(chart) {
      const ctx = chart.ctx;
      chart.data.datasets.forEach((dataset, datasetIndex) => {
        const meta = chart.getDatasetMeta(datasetIndex);
        if (!meta.visible) return;
        const isLine = dataset.type === "line" || (!dataset.type && chart.config.type === "line");

        meta.data.forEach((element, index) => {
          const val = dataset.data[index];
          if (val === null || val === undefined || val === 0) return;
          const str = Number(val).toLocaleString();
          const isCur = recent[index]?.key === curPeriod.key;

          ctx.save();
          if (isLine) {
            ctx.font = isCur
              ? "bold 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              : "bold 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            const textWidth = ctx.measureText(str).width;
            const x = element.x;
            const y = element.y - 14;

            // Pill badge: Brand Teal for active selected month, dark zinc for other months
            ctx.fillStyle = isCur ? "#0f766e" : "rgba(24, 24, 27, 0.92)";
            const padX = isCur ? 7 : 5, padY = isCur ? 3 : 2;
            const rx = x - textWidth / 2 - padX;
            const ry = y - 7 - padY;
            const rw = textWidth + padX * 2;
            const rh = 14 + padY * 2;
            if (ctx.roundRect) {
              ctx.beginPath();
              ctx.roundRect(rx, ry, rw, rh, 4);
              ctx.fill();
            } else {
              ctx.fillRect(rx, ry, rw, rh);
            }

            ctx.fillStyle = "#ffffff";
            ctx.fillText(str, x, y);
          } else {
            // Bars: position label right above the bar top
            ctx.font = isCur
              ? "bold 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              : "bold 10px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "bottom";
            ctx.fillStyle = isCur ? "#0f766e" : "#3f3f46";
            ctx.fillText(str, element.x, element.y - 2);
          }
          ctx.restore();
        });
      });
    }
  };

  charts["trendChart"] = new Chart(el, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          type: "bar",
          label: "전화 (콜)",
          data: callSeries,
          backgroundColor: recent.map((w) => (w.key === curPeriod.key ? "#0f766e" : "#14b8a6")),
          borderRadius: 4
        },
        {
          type: "bar",
          label: "채팅 (상담사/챗봇)",
          data: chatSeries,
          backgroundColor: recent.map((w) => (w.key === curPeriod.key ? "#0284c7" : "#38bdf8")),
          borderRadius: 4
        },
        {
          type: "bar",
          label: "게시판 (스토어/몰)",
          data: boardSeries,
          backgroundColor: recent.map((w) => (w.key === curPeriod.key ? "#d97706" : "#fbbf24")),
          borderRadius: 4
        },
        {
          type: "line",
          label: "전체 VOC 인입량 (Total)",
          data: totalSeries,
          borderColor: "#18181b",
          backgroundColor: "#18181b",
          borderWidth: 2.5,
          pointRadius: recent.map((w) => (w.key === curPeriod.key ? 6 : 3.5)),
          pointBackgroundColor: recent.map((w) => (w.key === curPeriod.key ? "#0f766e" : "#ffffff")),
          pointBorderColor: recent.map((w) => (w.key === curPeriod.key ? "#ffffff" : "#18181b")),
          pointBorderWidth: 2,
          tension: 0.3
        }
      ]
    },
    options: {
      layout: {
        padding: { top: 24, left: 8, right: 8 }
      },
      plugins: {
        datalabels: { display: false },
        legend: { position: "top", labels: { font: { size: 11 }, boxWidth: 10 } },
        tooltip: {
          callbacks: {
            label: (item) => `${item.dataset.label ? item.dataset.label + ': ' : ''}${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`
          }
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 } } },
        y: {
          grace: "15%",
          grid: { color: "rgba(0,0,0,.05)" },
          beginAtZero: true,
          ticks: {
            font: { size: 10 },
            precision: 0,
            maxTicksLimit: 4,
            callback: (v) => Number(v).toLocaleString()
          }
        }
      },
      onClick: (_evt, els) => {
        if (els.length) {
          const idx = els[0].index;
          const targetPeriod = recent[idx];
          if (targetPeriod && targetPeriod.key !== curPeriod.key) {
            const fullList = E.getPeriodList();
            const pIdx = fullList.findIndex((p) => p.key === targetPeriod.key);
            if (pIdx !== -1) {
              E.state.periodIndex = pIdx;
              renderAll();
            }
          }
        }
      },
      responsive: true,
      maintainAspectRatio: false
    },
    plugins: [trendDataLabelsPlugin]
  });
}

function renderBoardTrend() {
  const list = E.getPeriodList();
  const lookback = E.state.mode === "weekly" ? 5 : (E.state.mode === "monthly" ? 4 : 3);
  const recent = list.slice(Math.max(0, E.state.periodIndex - lookback + 1), E.state.periodIndex + 1);
  const curPeriod = E.getPeriod();
  if (!curPeriod) return;

  const prevP = E.prevPeriod();
  const curBoardCount = E.boardCount(curPeriod);
  const prevBoardCount = prevP ? E.boardCount(prevP) : 0;
  const boardDelta = prevP ? (curBoardCount - prevBoardCount) : null;

  // 1. Badge 업데이트
  const badgeEl = document.getElementById("boardWeeklyTotalBadge");
  if (badgeEl) {
    if (prevP) {
      const arrow = boardDelta >= 0 ? "▲" : "▼";
      const sign = boardDelta >= 0 ? "+" : "";
      const deltaPct = prevBoardCount > 0 ? ((boardDelta / prevBoardCount) * 100).toFixed(1) : 0;
      badgeEl.textContent = `선택 기간 ${curBoardCount.toLocaleString()}건 (전주 대비 ${arrow}${sign}${boardDelta}건 / ${sign}${deltaPct}%)`;
    } else {
      badgeEl.textContent = `선택 기간 ${curBoardCount.toLocaleString()}건`;
    }
  }

  // 2. Left: 주차별 게시판 총 인입 추이 (전주 대비 비교 막대그래프)
  destroyChart("boardWeeklyTrendChart");
  const elWeekly = document.getElementById("boardWeeklyTrendChart");
  if (elWeekly) {
    const labels = recent.map((p) => {
      const disp = formatPeriodDisplayLabel(p, E.state.mode);
      return p.key === curPeriod.key ? `${disp} (선택)` : disp;
    });

    const currentSeries = [];
    const prevSeries = [];

    recent.forEach((p) => {
      const cCnt = E.boardCount(p);
      const idx = list.findIndex((x) => x.key === p.key);
      const pr = idx > 0 ? list[idx - 1] : null;
      const pCnt = pr ? E.boardCount(pr) : null;
      currentSeries.push(cCnt);
      prevSeries.push(pCnt);
    });

    const boardTrendDataLabelsPlugin = {
      id: "boardTrendDataLabels",
      afterDatasetsDraw(chart) {
        const ctx = chart.ctx;
        const curMeta = chart.getDatasetMeta(0);
        if (!curMeta || !curMeta.visible) return;

        curMeta.data.forEach((element, index) => {
          const val = currentSeries[index];
          const prevVal = prevSeries[index];
          if (val === null || val === undefined) return;

          const strVal = `${val.toLocaleString()}건`;
          const isCur = recent[index]?.key === curPeriod.key;

          ctx.save();
          ctx.font = isCur
            ? "bold 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
            : "bold 10.5px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
          ctx.textAlign = "center";
          ctx.textBaseline = "bottom";
          ctx.fillStyle = isCur ? "#0f766e" : "#3f3f46";
          ctx.fillText(strVal, element.x, element.y - 4);

          if (prevVal != null && isCur) {
            const diff = val - prevVal;
            const sign = diff >= 0 ? "+" : "";
            const diffStr = diff >= 0 ? `▲${sign}${diff}` : `▼${diff}`;
            ctx.font = "bold 9.5px sans-serif";
            ctx.fillStyle = diff > 0 ? "#b91c1c" : (diff < 0 ? "#0d9488" : "#71717a");
            ctx.fillText(diffStr, element.x, element.y - 18);
          }
          ctx.restore();
        });
      }
    };

    charts["boardWeeklyTrendChart"] = new Chart(elWeekly, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "게시판 인입",
            data: currentSeries,
            backgroundColor: recent.map((w) => (w.key === curPeriod.key ? "#0f766e" : "#5eead4")),
            hoverBackgroundColor: recent.map((w) => (w.key === curPeriod.key ? "#115e59" : "#2dd4bf")),
            borderColor: recent.map((w) => (w.key === curPeriod.key ? "#134e4a" : "#14b8a6")),
            borderWidth: recent.map((w) => (w.key === curPeriod.key ? 2 : 1)),
            borderRadius: 6,
            barPercentage: 0.58,
            categoryPercentage: 0.7
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: {
          padding: { top: 22 }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 10.5, weight: "500" } }
          },
          y: {
            grid: { color: "rgba(0,0,0,.05)" },
            ticks: {
              font: { size: 10 },
              callback: (v) => Number(v).toLocaleString()
            },
            beginAtZero: true,
            grace: "15%"
          }
        },
        plugins: {
          datalabels: { display: false },
          legend: {
            display: false
          },
          tooltip: {
            callbacks: {
              label: (item) => `게시판 인입: ${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`,
              afterLabel: (item) => {
                const idx = item.dataIndex;
                const prevVal = prevSeries[idx];
                if (prevVal != null) {
                  const diff = item.raw - prevVal;
                  const sign = diff >= 0 ? "+" : "";
                  const pct = prevVal > 0 ? ((diff / prevVal) * 100).toFixed(1) : 0;
                  return `직전 주차 대비: ${sign}${diff}건 (${sign}${pct}%)`;
                }
                return "";
              }
            }
          }
        }
      },
      plugins: [boardTrendDataLabelsPlugin]
    });
  }

  // 3. Right: 주요 판매처(몰)별 게시판 접수 현황 (금주 vs 전주 비교)
  destroyChart("boardMallComparisonChart");
  const elMall = document.getElementById("boardMallComparisonChart");
  if (elMall) {
    const curMalls = E.boardMalls ? E.boardMalls(curPeriod) : {};
    const prevMalls = (prevP && E.boardMalls) ? E.boardMalls(prevP) : {};

    const allMallNames = Array.from(new Set([...Object.keys(curMalls), ...Object.keys(prevMalls)]));
    allMallNames.sort((a, b) => (curMalls[b] || 0) - (curMalls[a] || 0));
    const topMalls = allMallNames.slice(0, 7);

    const curMallData = topMalls.map((m) => curMalls[m] || 0);
    const prevMallData = topMalls.map((m) => prevMalls[m] || 0);

    charts["boardMallComparisonChart"] = new Chart(elMall, {
      type: "bar",
      data: {
        labels: topMalls.length ? topMalls : ["판매처 데이터 없음"],
        datasets: [
          {
            label: "선택 기간",
            data: curMallData,
            backgroundColor: "#0f766e",
            borderRadius: 4
          },
          {
            label: "이전 기간",
            data: prevMallData,
            backgroundColor: "#cbd5e1",
            borderRadius: 4
          }
        ]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            grid: { color: "rgba(0,0,0,.05)" },
            ticks: {
              font: { size: 10 },
              callback: (v) => Number(v).toLocaleString()
            },
            beginAtZero: true
          },
          y: {
            grid: { display: false },
            ticks: { font: { size: 11, weight: "bold" } }
          }
        },
        plugins: {
          legend: {
            position: "top",
            labels: { font: { size: 11 }, boxWidth: 10 }
          },
          tooltip: {
            callbacks: {
              label: (item) => `${item.dataset.label}: ${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`,
              footer: (items) => {
                if (items.length >= 2) {
                  const cV = items[0].raw || 0;
                  const pV = items[1].raw || 0;
                  const d = cV - pV;
                  return `증감: ${d >= 0 ? '+' : ''}${d}건`;
                }
                return "";
              }
            }
          }
        }
      }
    });
  }
}

function renderCall(chats) {
  const calls = chats.filter((c) => c.channel === "전화");
  const inb = calls.filter((c) => c.direction === "INBOUND").length;
  const outb = calls.filter((c) => c.direction === "OUTBOUND").length;
  destroyChart("callDirChart");
  charts["callDirChart"] = new Chart(document.getElementById("callDirChart"), {
    type: "doughnut",
    data: { labels: ["인바운드", "아웃바운드"], datasets: [{ data: [inb, outb], backgroundColor: [ACCENT, "#f59e0b"], borderWidth: 0 }] },
    options: {
      cutout: "62%",
      plugins: {
        legend: { position: "bottom", labels: { font: { size: 11 }, boxWidth: 10 } },
        tooltip: {
          callbacks: {
            label: (item) => `${item.label}: ${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`
          }
        },
        datalabels: {
          display: (ctx) => {
            const v = ctx.dataset.data[ctx.dataIndex];
            const sum = inb + outb;
            return v > 0 && sum > 0 && (v / sum >= 0.05);
          },
          color: "#ffffff",
          font: { weight: "bold", size: 11 },
          formatter: (value, ctx) => {
            const sum = inb + outb;
            const pct = sum > 0 ? ((value / sum) * 100).toFixed(1) : "0.0";
            return `${Number(value).toLocaleString()}건\n(${pct}%)`;
          },
          textAlign: "center"
        }
      },
      responsive: true,
      maintainAspectRatio: false
    },
  });
  const types = E.groupCount(calls, "mid").slice(0, 5);
  document.getElementById("callTypeList").innerHTML =
    `<div class="text-xs font-medium text-zinc-500">콜 유형 Top 5</div>` +
    types.map((t) => `<div class="flex justify-between"><span class="text-zinc-700">${t[0]}</span><span class="tnum font-medium">${t[1].toLocaleString()}건</span></div>`).join("");
}

const MEMO_KEY = "voc_memo_v1";
function loadMemos() { try { return JSON.parse(localStorage.getItem(MEMO_KEY)) || {}; } catch { return {}; } }
function saveMemos(m) { localStorage.setItem(MEMO_KEY, JSON.stringify(m)); }

function renderMemo() {
  const period = E.getPeriod();
  document.getElementById("memoPeriodTag").textContent = period.label;
  const memos = loadMemos();
  const list = memos[period.key] || [];
  const hist = document.getElementById("memoHistory");
  if (!list.length) {
    hist.innerHTML = `<p class="text-xs text-zinc-400">저장된 메모가 없습니다.</p>`;
  } else {
    hist.innerHTML = list.slice().reverse().map((m, ri) => {
      const idx = list.length - 1 - ri;
      return `<div class="rounded-lg bg-white p-3 ring-1 ring-black/5">
        <div class="flex items-start justify-between gap-2">
          <p class="whitespace-pre-wrap text-sm text-zinc-800">${m.text.replace(/</g, "&lt;")}</p>
          <button data-del="${idx}" class="shrink-0 text-xs text-zinc-400 hover:text-red-600">삭제</button>
        </div>
        <div class="mt-1 text-xs text-zinc-400 tnum">${m.at}</div>
      </div>`;
    }).join("");
    hist.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", () => {
      const i = +b.dataset.del; const mm = loadMemos();
      mm[period.key].splice(i, 1); saveMemos(mm); renderMemo();
    }));
  }
}

function updateFilterActiveBadges() {
  const f = E.state.filters;
  let activeCount = 0;
  document.querySelectorAll(".filter-sel").forEach((sel) => {
    const key = sel.dataset.filter;
    const isFiltered = f[key] && f[key] !== "all";
    if (isFiltered) {
      sel.classList.add("filter-active");
      activeCount++;
    } else {
      sel.classList.remove("filter-active");
    }
  });

  const badge = document.getElementById("activeFilterBadge");
  if (badge) {
    if (activeCount === 0) {
      badge.textContent = "전체 조건 적용 중";
      badge.className = "text-[11px] text-zinc-400 font-medium";
    } else {
      badge.textContent = `${activeCount.toLocaleString()}개 필터 적용 중`;
      badge.className = "text-[11px] text-teal-700 font-semibold";
    }
  }
}

function fillFilters() {
  const channelOpts = [
    { value: "all", label: "채널: 전체" },
    { value: "채팅", label: "채널: 채팅 (상담사·챗봇)" },
    { value: "전화", label: "채널: 전화 (콜)" },
    { value: "게시판", label: "채널: 게시판 (스토어·몰)" },
  ];

  const defs = {
    channel: channelOpts,
    journey: ["all", ...E.JOURNEY_ORDER],
    brand: ["all", "물티슈", "패밀리", "스킨케어", "헬로", "홈", "공통"],
    nature: ["all", "문의", "클레임", "운영"],
    risk: ["all", "HIGH", "MEDIUM", "LOW"],
  };
  const labels = { channel: "채널", journey: "고객여정", brand: "브랜드", nature: "상담성격", risk: "리스크" };

  document.querySelectorAll(".filter-sel").forEach((sel) => {
    const key = sel.dataset.filter;
    if (key === "channel") {
      sel.innerHTML = defs.channel.map((opt) => `<option value="${opt.value}">${opt.label}</option>`).join("");
    } else {
      sel.innerHTML = defs[key].map((v) => `<option value="${v}">${v === "all" ? `${labels[key]}: 전체` : v}</option>`).join("");
    }
    sel.value = E.state.filters[key] || "all";
    sel.addEventListener("change", () => {
      E.state.filters[key] = sel.value;
      midDrill = null;
      updateFilterActiveBadges();
      renderAll();
    });
  });

  const resetBtn = document.getElementById("resetFilter");
  if (resetBtn && !resetBtn.dataset.bound) {
    resetBtn.dataset.bound = "true";
    resetBtn.addEventListener("click", () => {
      Object.keys(E.state.filters).forEach((k) => (E.state.filters[k] = "all"));
      document.querySelectorAll(".filter-sel").forEach((sel) => {
        sel.value = "all";
      });
      midDrill = null;
      updateFilterActiveBadges();
      renderAll();
    });
  }

  updateFilterActiveBadges();
}

function renderPeriodControls() {
  const period = E.getPeriod();
  if (!period) return;

  const list = E.getPeriodList();
  const maxIdx = list.length - 1;
  const curIdx = E.state.periodIndex;

  // 1. periodLabel 텍스트 갱신 (호환성 유지)
  const pLabelEl = document.getElementById("periodLabel");
  let curLabelText = "";
  if (E.state.mode === "weekly") {
    const weekName = period.week_of_month || formatPeriodDisplayLabel(period, "weekly");
    const dateRange = period.label ? period.label.replace(/202[56]년\s*/, "") : "";
    curLabelText = `${weekName} (${dateRange})`;
  } else if (E.state.mode === "yearly") {
    const yr = (period.key || "").slice(0, 4);
    curLabelText = `${yr}년 연간`;
  } else {
    curLabelText = period.label;
  }
  if (pLabelEl) pLabelEl.textContent = curLabelText;

  // 2. periodSelect 빠른 기간 선택 드롭다운 옵션 구성 (최신순 역순 정렬)
  const pSelect = document.getElementById("periodSelect");
  if (pSelect) {
    const optionsHtml = list.map((p, idx) => {
      let optLabel = "";
      const isLatest = (idx === maxIdx);
      const tag = isLatest ? " [현재]" : "";

      if (E.state.mode === "weekly") {
        const weekName = p.week_of_month || formatPeriodDisplayLabel(p, "weekly");
        const dateRange = p.label ? p.label.replace(/202[56]년\s*/, "") : "";
        optLabel = `${weekName} (${dateRange})${tag}`;
      } else if (E.state.mode === "yearly") {
        const yr = (p.key || "").slice(0, 4);
        optLabel = `${yr}년 연간${tag}`;
      } else {
        optLabel = `${p.label}${tag}`;
      }
      return `<option value="${idx}">${optLabel}</option>`;
    }).reverse().join("");

    pSelect.innerHTML = optionsHtml;
    pSelect.value = String(curIdx);
  }

  // 3. ◀, ▶ 버튼 상태
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  if (prevBtn) {
    prevBtn.disabled = curIdx <= 0;
    prevBtn.classList.toggle("opacity-30", curIdx <= 0);
    prevBtn.classList.toggle("cursor-not-allowed", curIdx <= 0);
  }
  if (nextBtn) {
    nextBtn.disabled = curIdx >= maxIdx;
    nextBtn.classList.toggle("opacity-30", curIdx >= maxIdx);
    nextBtn.classList.toggle("cursor-not-allowed", curIdx >= maxIdx);
  }

  // 4. 모드 버튼 활성화 표시
  document.querySelectorAll(".mode-btn").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === E.state.mode)));
}

function renderAll() {
  renderPeriodControls();
  const period = E.getPeriod();
  const prev = E.prevPeriod();
  const chats = E.applyFilters(E.rawChats(period));
  window._curChats = chats;
  const prevChats = prev ? E.applyFilters(E.rawChats(prev)) : null;

  renderKPIs(computeKPIs(chats, prevChats));
  renderAnomaly(chats, prevChats);
  renderMain(chats);
  renderTrend();
  renderCall(chats);
  renderBoardTrend();
  renderMemo();
  if (currentView === "report") renderReport();
}

function reportKpiBox(label, value, deltaVal, opts = {}) {
  let badge = "";
  if (deltaVal != null && deltaVal !== 0) {
    const good = opts.inverse ? deltaVal < 0 : deltaVal > 0;
    const color = good ? "text-teal-700" : "text-red-600";
    const arrow = deltaVal > 0 ? "▲" : "▼";
    badge = `<span class="tnum text-xs font-medium ${color}">${arrow}${Math.abs(deltaVal).toLocaleString()}</span>`;
  }
  const subHtml = opts.subText ? `<div class="mt-1.5 text-[11px] text-zinc-500 font-medium">${opts.subText}</div>` : "";
  return `<div class="rounded-lg bg-teal-50 p-4 ring-1 ring-teal-100 flex flex-col justify-between">
    <div>
      <div class="text-xs text-teal-800 font-medium">${label}</div>
      <div class="mt-1 flex items-baseline gap-1.5">
        <span class="tnum text-2xl font-semibold tracking-tight text-zinc-900">${typeof value === 'number' ? value.toLocaleString() : value}</span>
        ${badge}
      </div>
    </div>
    ${subHtml}
  </div>`;
}

function claimCard(title, cur, prev, items, accent) {
  const d = prev != null ? cur - prev : null;
  let badge = "";
  if (d != null && d !== 0) {
    const arrow = d > 0 ? "▲" : "▼";
    const color = d > 0 ? "text-red-600" : "text-teal-700";
    badge = `<span class="tnum text-xs font-medium ${color}">${arrow}${Math.abs(d).toLocaleString()}</span>`;
  }
  const top = items.slice(0, 4).map((it) =>
    `<li class="flex items-center justify-between gap-2 text-xs">
      <span class="flex items-center gap-1 text-zinc-600">
        ${it.risk === "HIGH" ? '<span class="rounded bg-red-600 px-1 text-[10px] font-medium text-white">H</span>' : ""}
        ${it.label}
      </span>
      <span class="tnum font-medium text-zinc-800">${Number(it.count || 0).toLocaleString()}</span>
    </li>`).join("");
  return `<div class="rounded-lg ring-1 ring-black/5 p-4">
    <div class="flex items-baseline justify-between">
      <span class="text-sm font-medium" style="color:${accent}">${title}</span>
      <span class="flex items-baseline gap-1.5"><span class="tnum text-xl font-semibold">${Number(cur || 0).toLocaleString()}</span>${badge}</span>
    </div>
    <ul class="mt-2 space-y-1" role="list">${top || '<li class="text-xs text-zinc-400">해당 없음</li>'}</ul>
  </div>`;
}

function claimDetail(bucket, labelKey) {
  return E.groupCount(bucket, labelKey)
    .filter((x) => x[0] !== "(미지정)" && x[0] !== "")
    .map(([label, count]) => ({ label, count, risk: bucket.find((c) => c[labelKey] === label)?.risk }));
}

function reportRecentPeriods() {
  const list = E.getPeriodList();
  const lookback = E.state.mode === "weekly" ? 4 : (E.state.mode === "monthly" ? 4 : (E.state.mode === "quarterly" ? 4 : 2));
  return list.slice(Math.max(0, E.state.periodIndex - lookback + 1), E.state.periodIndex + 1);
}

function renderReportChannelChart(recent, curPeriod) {
  destroyChart("reportChannelChart");
  const el = document.getElementById("reportChannelChart");
  if (!el) return;

  const labels = recent.map((p) => {
    const disp = formatPeriodDisplayLabel(p, E.state.mode);
    return p.key === curPeriod.key ? `${disp} (선택)` : disp;
  });

  const callSeries = [], chatSeries = [], boardSeries = [], totalSeries = [];
  for (const p of recent) {
    const raw = E.getRawSummary ? E.getRawSummary(p) : null;
    let calls, chats, b, tot;
    if (raw) {
      calls = raw.raw_call;
      chats = raw.raw_chat;
      b = raw.raw_board;
      tot = raw.total_offered_raw;
    } else {
      const cs = E.rawChats(p).filter((c) => c.valid && c.channel !== "배송접수");
      b = E.boardCount(p);
      // 전화: 순수 인바운드 건수만 인입 추이에 포함 (아웃바운드 제외)
      calls = cs.filter((c) => c.channel === "전화" && (c.direction || "INBOUND") === "INBOUND").length;
      // 채팅: 인바운드 & 아웃바운드 모두 포함
      chats = cs.filter((c) => c.channel === "상담사챗" || c.channel === "챗봇(ALF)").length;
      tot = calls + chats + b;
    }
    callSeries.push(calls);
    chatSeries.push(chats);
    boardSeries.push(b);
    totalSeries.push(tot);
  }

  const reportChannelDataLabelsPlugin = {
    id: "reportChannelDataLabels",
    afterDatasetsDraw(chart) {
      const ctx = chart.ctx;
      chart.data.datasets.forEach((dataset, datasetIndex) => {
        const meta = chart.getDatasetMeta(datasetIndex);
        if (!meta.visible) return;
        const isLine = dataset.type === "line" || (!dataset.type && chart.config.type === "line");

        meta.data.forEach((element, index) => {
          const val = dataset.data[index];
          if (val === null || val === undefined || val === 0) return;
          const str = Number(val).toLocaleString();
          const isCur = recent[index]?.key === curPeriod.key;

          ctx.save();
          if (isLine) {
            ctx.font = isCur
              ? "bold 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              : "bold 10px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            const textWidth = ctx.measureText(str).width;
            const x = element.x;
            const y = element.y - 12;

            ctx.fillStyle = isCur ? "#0f766e" : "rgba(24, 24, 27, 0.9)";
            const padX = isCur ? 6 : 4, padY = 2;
            const rx = x - textWidth / 2 - padX;
            const ry = y - 6 - padY;
            const rw = textWidth + padX * 2;
            const rh = 12 + padY * 2;
            if (ctx.roundRect) {
              ctx.beginPath();
              ctx.roundRect(rx, ry, rw, rh, 3);
              ctx.fill();
            } else {
              ctx.fillRect(rx, ry, rw, rh);
            }

            ctx.fillStyle = "#ffffff";
            ctx.fillText(str, x, y);
          } else {
            ctx.font = isCur
              ? "bold 10px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
              : "9px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "bottom";
            ctx.fillStyle = isCur ? "#0f766e" : "#52525b";
            ctx.fillText(str, element.x, element.y - 2);
          }
          ctx.restore();
        });
      });
    }
  };

  charts["reportChannelChart"] = new Chart(el, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          type: "bar",
          label: "전화 (콜)",
          data: callSeries,
          backgroundColor: recent.map((w) => (w.key === curPeriod.key ? "#0f766e" : "#14b8a6")),
          borderRadius: 4
        },
        {
          type: "bar",
          label: "채팅 (상담사/챗봇)",
          data: chatSeries,
          backgroundColor: recent.map((w) => (w.key === curPeriod.key ? "#0284c7" : "#38bdf8")),
          borderRadius: 4
        },
        {
          type: "bar",
          label: "게시판 (스토어/몰)",
          data: boardSeries,
          backgroundColor: recent.map((w) => (w.key === curPeriod.key ? "#d97706" : "#fbbf24")),
          borderRadius: 4
        },
        {
          type: "line",
          label: "전체 VOC 인입량 (Total)",
          data: totalSeries,
          borderColor: "#18181b",
          backgroundColor: "#18181b",
          borderWidth: 2.2,
          pointRadius: recent.map((w) => (w.key === curPeriod.key ? 5 : 3)),
          pointBackgroundColor: recent.map((w) => (w.key === curPeriod.key ? "#0f766e" : "#ffffff")),
          pointBorderColor: recent.map((w) => (w.key === curPeriod.key ? "#ffffff" : "#18181b")),
          pointBorderWidth: 1.5,
          tension: 0.25
        }
      ]
    },
    options: {
      plugins: {
        datalabels: { display: false },
        legend: { position: "top", labels: { font: { size: 11 }, boxWidth: 10 } },
        tooltip: {
          callbacks: {
            label: (item) => `${item.dataset.label ? item.dataset.label + ': ' : ''}${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`
          }
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 } } },
        y: {
          grace: "15%",
          grid: { color: "rgba(0,0,0,.05)" },
          beginAtZero: true,
          ticks: {
            font: { size: 10 },
            precision: 0,
            maxTicksLimit: 4,
            callback: (v) => Number(v).toLocaleString()
          }
        }
      },
      responsive: true,
      maintainAspectRatio: false
    },
    plugins: [reportChannelDataLabelsPlugin]
  });
}

function renderMiniClaimChart(canvasId, labels, data, themeColor, activeColor, curIndex) {
  destroyChart(canvasId);
  const el = document.getElementById(canvasId);
  if (!el) return;

  const miniDataLabelsPlugin = {
    id: canvasId + "_labels",
    afterDatasetsDraw(chart) {
      const ctx = chart.ctx;
      const meta = chart.getDatasetMeta(0);
      if (!meta || !meta.visible) return;
      meta.data.forEach((element, index) => {
        const val = data[index];
        if (val == null) return;
        const str = Number(val).toLocaleString();
        const isCur = index === curIndex;
        ctx.save();
        ctx.font = isCur
          ? "bold 10px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
          : "9px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
        ctx.fillStyle = isCur ? activeColor : "#52525b";
        ctx.fillText(str, element.x, element.y - 2);
        ctx.restore();
      });
    }
  };

  charts[canvasId] = new Chart(el, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          data: data,
          backgroundColor: data.map((_, i) => (i === curIndex ? activeColor : themeColor)),
          borderRadius: 3,
          maxBarThickness: 32
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (item) => `${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { font: { size: 9 }, color: "#71717a" }
        },
        y: {
          grace: "15%",
          grid: { color: "rgba(0,0,0,.04)" },
          beginAtZero: true,
          ticks: {
            font: { size: 8 },
            color: "#a1a1aa",
            maxTicksLimit: 3,
            callback: (v) => Number(v).toLocaleString()
          }
        }
      }
    },
    plugins: [miniDataLabelsPlugin]
  });
}

function getCategoryMemos(category, period) {
  const catData = loadCatInsights();
  if (!period || !period.key) return [];
  // 사용자의 명확한 원칙: 코멘트는 해당 시점(선택된 기간)에만 독립적으로 귀속되며, 상위 기간에 임의 합산되지 않음
  const list = (catData[period.key] && Array.isArray(catData[period.key][category])) ? catData[period.key][category] : [];
  return list.slice().sort((a, b) => (a.at || "").localeCompare(b.at || ""));
}

function renderReportThreePillars(period, prev, buckets, pb, recent) {
  const container = document.getElementById("reportThreePillars");
  if (!container) return;

  const rawShipments = E.rawShipments ? E.rawShipments(period) : [];
  const prevShipments = prev && E.rawShipments ? E.rawShipments(prev) : [];
  const curShipCount = rawShipments.length > 0 ? rawShipments.length : buckets.delivery.length;
  const prevShipCount = rawShipments.length > 0 ? (prevShipments.length || 0) : (pb?.delivery.length || 0);

  const recentLabels = recent.map((p) => formatPeriodDisplayLabel(p, E.state.mode));
  const curIdx = recent.findIndex((p) => p.key === period.key);

  const qHighCount = buckets.quality.filter((c) => c.risk === "HIGH").length;
  const qTopBrand = claimDetail(buckets.quality, "brand")[0]?.label || "물티슈";

  const dBoxDmg = rawShipments.length > 0
    ? rawShipments.filter((s) => (s.type || "").includes("파손")).length
    : buckets.delivery.filter((c) => (c.sub || "").includes("박스파손") || (c.sub || "").includes("파손")).length;
  const dDelay = rawShipments.length > 0
    ? rawShipments.filter((s) => (s.type || "").includes("오배송") || (s.type || "").includes("지연")).length
    : buckets.delivery.filter((c) => (c.sub || "").includes("지연")).length;

  const sEscCount = buckets.service.filter((c) => E.getServiceCategory(c) === "상급자통화" || c.risk === "HIGH").length;
  const sHuman = buckets.service.filter((c) => E.getServiceCategory(c) === "휴먼에러").length;

  const pbQDetail = pb ? claimDetail(pb.quality, "sub") : [];
  const pbQMap = Object.fromEntries(pbQDetail.map((x) => [x.label, x.count]));

  const pbShipList = pb && E.rawShipments && prev ? E.rawShipments(prev) : [];
  const pbShipDetail = pbShipList.length > 0
    ? E.groupCount(pbShipList, "type").filter((x) => x[0]).map(([label, count]) => ({ label, count }))
    : (pb ? claimDetail(pb.delivery, "sub") : []);
  const pbShipMap = Object.fromEntries(pbShipDetail.map((x) => [x.label, x.count]));

  const pbSvcDetail = pb ? E.groupCount(pb.service, "mid").filter((x) => x[0] !== "").map(([label, count]) => ({ label: label || "기타", count })) : [];
  const pbSvcMap = Object.fromEntries(pbSvcDetail.map((x) => [x.label, x.count]));

  const pillars = [
    {
      id: "quality",
      name: "품질 클레임",
      subName: "Quality Claims",
      icon: "🔬",
      color: "rgba(217, 119, 6, 0.45)",
      activeColor: "#b45309",
      bgClass: "bg-amber-50/40",
      borderClass: "border-amber-200/80",
      accentBadgeClass: "bg-amber-100 text-amber-900 border-amber-300",
      curCount: buckets.quality.length,
      prevCount: pb?.quality.length,
      historyCounts: recent.map((p) => E.claimBuckets(E.rawChats(p).filter((c) => c.valid)).quality.length),
      prevMap: pbQMap,
      topItems: claimDetail(buckets.quality, "sub").slice(0, 5),
      focusBadge: `<span class="inline-flex items-center gap-1 rounded bg-amber-100 text-amber-900 px-2 py-0.5 text-[11px] font-semibold border border-amber-300">고위험 ${qHighCount}건 · 주불만: ${qTopBrand}</span>`,
      memos: getCategoryMemos("quality", period),
      defaultComment: buckets.quality.length
        ? `• ${claimDetail(buckets.quality, "sub")[0]?.label || "포장/용액"} 불만(${Number(claimDetail(buckets.quality, "sub")[0]?.count || 0).toLocaleString()}건) 비중이 높으며, 변질/이물 등 주요 품질 리스크 클레임에 대해 공정 분석 및 고객 안심 케어 진행 중.`
        : "• 선택 기간 접수된 품질 클레임이 없습니다."
    },
    {
      id: "delivery",
      name: "배송 클레임",
      subName: "Delivery Claims",
      icon: "🚚",
      color: "rgba(220, 38, 38, 0.45)",
      activeColor: "#dc2626",
      bgClass: "bg-rose-50/40",
      borderClass: "border-rose-200/80",
      accentBadgeClass: "bg-rose-100 text-rose-900 border-rose-300",
      curCount: curShipCount,
      prevCount: prevShipCount,
      historyCounts: recent.map((p) => {
        const sList = E.rawShipments ? E.rawShipments(p) : [];
        return sList.length > 0 ? sList.length : E.claimBuckets(E.rawChats(p).filter((c) => c.valid)).delivery.length;
      }),
      prevMap: pbShipMap,
      topItems: rawShipments.length > 0
        ? E.groupCount(rawShipments, "type").filter((x) => x[0]).map(([label, count]) => ({ label, count })).slice(0, 5)
        : claimDetail(buckets.delivery, "sub").slice(0, 5),
      focusBadge: rawShipments.length > 0
        ? `<span class="inline-flex items-center gap-1 rounded bg-rose-100 text-rose-900 px-2 py-0.5 text-[11px] font-semibold border border-rose-300">물류원장 ${curShipCount}건 (상담접수 ${buckets.delivery.length}건)</span>`
        : `<span class="inline-flex items-center gap-1 rounded bg-rose-100 text-rose-900 px-2 py-0.5 text-[11px] font-semibold border border-rose-300">파손 ${dBoxDmg}건 · 지연 ${dDelay}건</span>`,
      memos: getCategoryMemos("delivery", period),
      defaultComment: curShipCount
        ? (rawShipments.length > 0
          ? `• 물류 벤더사(풀필먼트 및 CJ초저온) 원장 기준 ${curShipCount}건 (채널톡 배송상담 ${buckets.delivery.length}건). 오출고 재발 방지 및 택배 파손 맞교환 조치 완료.`
          : `• ${claimDetail(buckets.delivery, "sub")[0]?.label || "오배송/지연"} 접수(${Number(claimDetail(buckets.delivery, "sub")[0]?.count || 0).toLocaleString()}건) 중심. 물류 벤더사 오출고 재발 방지 및 당일 맞교환 조치 완료.`)
        : "• 선택 기간 접수된 배송 클레임이 없습니다."
    },
    {
      id: "service",
      name: "서비스 클레임",
      subName: "Service Claims",
      icon: "💬",
      color: "rgba(13, 148, 136, 0.45)",
      activeColor: "#0f766e",
      bgClass: "bg-teal-50/40",
      borderClass: "border-teal-200/80",
      accentBadgeClass: "bg-teal-100 text-teal-900 border-teal-300",
      curCount: buckets.service.length,
      prevCount: pb?.service.length,
      historyCounts: recent.map((p) => E.claimBuckets(E.rawChats(p).filter((c) => c.valid)).service.length),
      prevMap: pbSvcMap,
      topItems: E.groupCount(buckets.service, "mid").filter((x) => x[0] !== "").map(([label, count]) => ({ label: label || "기타", count })).slice(0, 5),
      focusBadge: `<span class="inline-flex items-center gap-1 rounded bg-teal-100 text-teal-900 px-2 py-0.5 text-[11px] font-semibold border border-teal-300">에스컬레이션 ${sEscCount}건 · 휴먼에러 ${sHuman}건</span>`,
      memos: getCategoryMemos("service", period),
      defaultComment: buckets.service.length
        ? `• ${E.groupCount(buckets.service, "mid")[0]?.[0] || "상담/시스템"} 문의(${Number(E.groupCount(buckets.service, "mid")[0]?.[1] || 0).toLocaleString()}건) 중심. 에스컬레이션 방지 및 첫 통화/채팅 해결율 집중 관리 중.`
        : "• 선택 기간 접수된 서비스 클레임이 없습니다."
    }
  ];

  container.innerHTML = pillars.map((p) => {
    const diff = p.prevCount != null ? p.curCount - p.prevCount : null;
    let diffBadge = "";
    if (diff != null && diff !== 0) {
      const isUp = diff > 0;
      const arrow = isUp ? "▲" : "▼";
      const diffColor = isUp ? "text-rose-600 bg-rose-50 border-rose-200" : "text-teal-700 bg-teal-50 border-teal-200";
      const pct = p.prevCount > 0 ? ` (${isUp ? "+" : ""}${((diff / p.prevCount) * 100).toFixed(1)}%)` : "";
      diffBadge = `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10.5px] font-bold border ${diffColor} tnum whitespace-nowrap">${arrow}${Math.abs(diff).toLocaleString()}건${pct}</span>`;
    } else if (diff === 0) {
      diffBadge = `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10.5px] font-medium bg-zinc-100 text-zinc-600 border border-zinc-200 tnum whitespace-nowrap">변동 없음</span>`;
    }

    const totalTop = p.curCount || 1;
    const tableRows = p.topItems.length ? p.topItems.map((it, idx) => {
      const pctNum = totalTop > 0 ? ((it.count / totalTop) * 100) : 0;
      const pct = pctNum.toFixed(1);
      const prvCnt = p.prevMap ? (p.prevMap[it.label] || 0) : null;
      let itDiffBadge = '<span class="text-zinc-400 text-[10px]">-</span>';
      if (prvCnt != null) {
        const d = it.count - prvCnt;
        if (d > 0) {
          const pStr = prvCnt > 0 ? ` (+${Math.round((d / prvCnt) * 100)}%)` : " (신규)";
          itDiffBadge = `<span class="inline-flex items-center text-[9.5px] font-bold text-rose-600 bg-rose-50 px-1 py-0.5 rounded border border-rose-200 whitespace-nowrap">▲${d}${pStr}</span>`;
        } else if (d < 0) {
          const pStr = prvCnt > 0 ? ` (${Math.round((d / prvCnt) * 100)}%)` : "";
          itDiffBadge = `<span class="inline-flex items-center text-[9.5px] font-bold text-teal-700 bg-teal-50 px-1 py-0.5 rounded border border-teal-200 whitespace-nowrap">▼${Math.abs(d)}${pStr}</span>`;
        } else {
          itDiffBadge = `<span class="text-zinc-400 text-[9.5px] font-medium whitespace-nowrap">- (0%)</span>`;
        }
      }

      return `<tr class="hover:bg-zinc-50/60 transition">
        <td class="py-1.5 px-2 font-medium text-zinc-800 min-w-0">
          <div class="flex items-center gap-1 min-w-0">
            <span class="inline-block w-3.5 shrink-0 text-[10px] text-zinc-400 font-bold text-center">${idx + 1}</span>
            <span class="truncate text-[11.5px]" title="${it.label}">${it.label}</span>
          </div>
          <div class="w-full bg-zinc-100 rounded-full h-1 mt-1 overflow-hidden">
            <div class="h-1 rounded-full transition-all duration-500" style="width:${Math.min(100, Math.max(5, pctNum))}%; background-color:${p.activeColor}"></div>
          </div>
        </td>
        <td class="py-1.5 px-1 text-right font-semibold text-zinc-800 tnum align-middle whitespace-nowrap text-[11px]">${Number(it.count).toLocaleString()}건</td>
        <td class="py-1.5 px-1 text-center tnum align-middle whitespace-nowrap">${itDiffBadge}</td>
        <td class="py-1.5 px-2 text-right text-zinc-500 tnum align-middle whitespace-nowrap text-[11px]">${pct}%</td>
      </tr>`;
    }).join("") : `<tr><td colspan="4" class="py-3 text-center text-zinc-400 text-xs">접수 내역 없음</td></tr>`;

    let commentsHtml = "";
    if (p.memos.length) {
      commentsHtml = `
        <div class="space-y-2 max-h-56 overflow-y-auto pr-0.5">
          ${p.memos.map((m, mIdx) => {
            const safeText = (m.text || "").replace(/</g, "&lt;");
            const isLong = safeText.length > 120 || safeText.split("\n").length > 3;
            const memoElId = `pillarMemo_${p.id}_${mIdx}`;
            return `
            <div class="rounded-lg bg-white p-2.5 ring-1 ring-black/5 shadow-xs text-xs">
              <div class="flex items-center justify-between text-[11px] text-zinc-400 mb-1">
                <span class="font-medium text-zinc-600 bg-zinc-100 px-1.5 py-0.2 rounded">${m.snapshot?.filterLabel || m.tag || "전체"}</span>
                <span class="tnum">${m.at || ""}</span>
              </div>
              <p id="${memoElId}" class="text-zinc-800 whitespace-pre-wrap leading-relaxed ${isLong ? 'line-clamp-3' : ''}">${safeText}</p>
              ${isLong ? `
                <div class="mt-1 text-right">
                  <button type="button" class="text-[11px] text-teal-700 font-semibold hover:underline cursor-pointer" onclick="
                    const el = document.getElementById('${memoElId}');
                    if (el.classList.contains('line-clamp-3')) {
                      el.classList.remove('line-clamp-3');
                      this.textContent = '접기 ▲';
                    } else {
                      el.classList.add('line-clamp-3');
                      this.textContent = '더보기 ▼';
                    }
                  ">더보기 ▼</button>
                </div>
              ` : ''}
            </div>
          `;
          }).join("")}
        </div>
      `;
    } else {
      commentsHtml = `
        <div class="rounded-lg bg-white/80 p-2.5 ring-1 ring-black/5 text-xs">
          <p class="text-zinc-700 leading-relaxed">${p.defaultComment}</p>
          <div class="mt-1.5 text-[10px] text-zinc-400 flex items-center gap-1">
            <span>💡 [${p.name.slice(0, 2)} 상세] 화면에서 작성한 인사이트 코멘트가 실시간 자동 연동됩니다.</span>
          </div>
        </div>
      `;
    }

    return `
      <div class="flex flex-col rounded-xl border ${p.borderClass} ${p.bgClass} p-4 shadow-2xs">
        <!-- 1. 카드 헤더 -->
        <div class="border-b border-zinc-200/60 pb-2.5">
          <div class="flex items-center justify-between gap-1.5">
            <div class="flex items-center gap-1.5 min-w-0">
              <span class="text-base shrink-0">${p.icon}</span>
              <span class="font-bold text-sm text-zinc-900 whitespace-nowrap">${p.name}</span>
              <span class="tnum text-base font-extrabold text-zinc-900 whitespace-nowrap ml-1">${p.curCount.toLocaleString()}건</span>
            </div>
            <div class="shrink-0 text-right">
              ${diffBadge}
            </div>
          </div>
          <div class="mt-2 flex items-center justify-between">
            ${p.focusBadge}
          </div>
        </div>

        <!-- 2. 최근 기간 발생 추이 미니 그래프 -->
        <div class="mt-3">
          <div class="flex items-center justify-between text-[11px] text-zinc-500 mb-1">
            <span class="font-semibold text-zinc-700">발생 건수 추이</span>
            <span class="text-[10px] text-zinc-400">막대 상단: 접수량</span>
          </div>
          <div class="h-28 w-full relative bg-white/60 rounded-lg p-2 ring-1 ring-black/5">
            <canvas id="report${p.id}MiniChart"></canvas>
          </div>
        </div>

        <!-- 3. 주요 클레임 유형 순위 테이블 -->
        <div class="mt-3 flex-1">
          <div class="flex items-center justify-between text-[11px] text-zinc-500 mb-1">
            <span class="font-semibold text-zinc-700">주요 클레임 유형 TOP 5</span>
            <span class="text-[10px] text-zinc-400">현재 기준 · 이전 대비</span>
          </div>
          <div class="rounded-lg bg-white ring-1 ring-black/5 overflow-hidden">
            <table class="w-full text-left text-xs table-fixed">
              <colgroup>
                <col style="width: 38%;">
                <col style="width: 19%;">
                <col style="width: 28%;">
                <col style="width: 15%;">
              </colgroup>
              <thead class="bg-zinc-50/80 text-zinc-500 border-b border-black/5">
                <tr>
                  <th class="py-1.5 px-2 font-medium">유형</th>
                  <th class="py-1.5 px-1 font-medium text-right whitespace-nowrap">현재</th>
                  <th class="py-1.5 px-1 font-medium text-center whitespace-nowrap">이전대비</th>
                  <th class="py-1.5 px-2 font-medium text-right whitespace-nowrap">비중</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-black/5">
                ${tableRows}
              </tbody>
            </table>
          </div>
        </div>

        <!-- 4. 하단 이슈 코멘트 -->
        <div class="mt-3.5 pt-2.5 border-t border-zinc-200/80">
          <div class="flex items-center justify-between text-[11px] text-zinc-600 font-semibold mb-1.5">
            <span class="flex items-center gap-1">
              <span>📌</span>
              <span>이슈 코멘트 &amp; 인사이트</span>
            </span>
            ${p.memos.length ? `<span class="rounded bg-teal-100 text-teal-800 px-1.5 py-0.2 text-[10px] font-bold">${p.memos.length}건 등록</span>` : ""}
          </div>
          ${commentsHtml}
        </div>
      </div>
    `;
  }).join("");

  // 미니 차트 생성
  pillars.forEach((p) => {
    renderMiniClaimChart(
      `report${p.id}MiniChart`,
      recentLabels,
      p.historyCounts,
      p.color,
      p.activeColor,
      curIdx !== -1 ? curIdx : p.historyCounts.length - 1
    );
  });
}

let reportRiskSectionEnabled = false;
let reportRiskExpanded = false;
let reportRiskSubFilter = "all"; // "all" | "claim" | "inquiry"

function captureChartCanvasToPng(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !canvas.width || !canvas.height) return null;
  try {
    const tmp = document.createElement("canvas");
    tmp.width = canvas.width;
    tmp.height = canvas.height;
    const ctx = tmp.getContext("2d");
    // 순백색 불투명 배경 채우기 (격자선 비침 완벽 차단)
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, tmp.width, tmp.height);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(canvas, 0, 0);
    return tmp.toDataURL("image/png", 1.0);
  } catch (e) {
    console.warn("차트 캔버스 이미지 추출 실패:", canvasId, e);
    return null;
  }
}

function prepareAndCaptureChart(viewId, canvasId, renderFn) {
  const viewEl = document.getElementById(viewId);
  const canvasEl = document.getElementById(canvasId);
  if (!canvasEl) return null;

  let cleanup = null;
  if (viewEl && viewEl.classList.contains("hidden")) {
    const origCss = viewEl.style.cssText;
    viewEl.classList.remove("hidden");
    viewEl.style.position = "fixed";
    viewEl.style.left = "-9999px";
    viewEl.style.top = "0";
    viewEl.style.width = "1024px";
    viewEl.style.opacity = "0";
    viewEl.style.pointerEvents = "none";
    viewEl.style.zIndex = "-9999";
    cleanup = () => {
      viewEl.classList.add("hidden");
      viewEl.style.cssText = origCss;
    };
  }

  // Chart.js 애니메이션 일시 비활성화 -> 즉각 100% 완성된 선명한 캔버스 확보!
  const hasChart = typeof Chart !== "undefined";
  const origAnim = hasChart && Chart.defaults ? Chart.defaults.animation : undefined;
  if (hasChart && Chart.defaults) {
    Chart.defaults.animation = false;
  }

  try {
    if (typeof renderFn === "function") {
      renderFn();
    }
    if (typeof charts !== "undefined" && charts[canvasId]) {
      charts[canvasId].update("none");
    }
  } catch (err) {
    console.warn("차트 렌더링 중 오류:", canvasId, err);
  } finally {
    if (hasChart && Chart.defaults && origAnim !== undefined) {
      Chart.defaults.animation = origAnim;
    }
  }

  const imgData = captureChartCanvasToPng(canvasId);

  if (cleanup) {
    cleanup();
  }

  return imgData;
}

function renderReportRiskActions(period, chats, prevChats) {
  const container = document.getElementById("reportRiskActions");
  const sec = document.getElementById("reportRiskSection");
  const toggle = document.getElementById("toggleReportRiskSection");
  const toggleLbl = document.getElementById("reportRiskToggleLabel");
  const memoH = document.getElementById("reportMemoHeading");

  if (toggle) {
    toggle.checked = reportRiskSectionEnabled;
  }
  if (toggleLbl) {
    toggleLbl.textContent = reportRiskSectionEnabled ? "ON" : "OFF";
    toggleLbl.className = reportRiskSectionEnabled
      ? "ml-1.5 text-xs font-bold text-teal-700"
      : "ml-1.5 text-xs font-bold text-zinc-400";
  }

  if (memoH) {
    memoH.textContent = reportRiskSectionEnabled ? "5. CX팀 종합 코멘트" : "4. CX팀 종합 코멘트";
  }

  if (!container) return;

  if (!reportRiskSectionEnabled) {
    if (sec) sec.classList.add("print:hidden");
    container.innerHTML = `
      <div class="rounded-xl border border-dashed border-zinc-300 bg-zinc-50/80 p-3.5 text-center text-xs text-zinc-500 flex items-center justify-between shadow-2xs">
        <div class="flex items-center gap-2">
          <span class="text-base">⏸</span>
          <span>핵심 리스크 &amp; 이상징후 이슈업 섹션이 <strong>OFF (비표시)</strong> 상태입니다. 리포트 인쇄(PDF) 및 엑셀 추출에서 제외됩니다.</span>
        </div>
        <button id="btnTurnOnRisk" type="button" class="rounded-md bg-white px-2.5 py-1 text-xs font-semibold text-teal-700 ring-1 ring-black/10 hover:bg-teal-50 transition shadow-2xs cursor-pointer">다시 켜기 (ON)</button>
      </div>
    `;
    const btnOn = document.getElementById("btnTurnOnRisk");
    if (btnOn) {
      btnOn.addEventListener("click", () => {
        reportRiskSectionEnabled = true;
        localStorage.setItem("voc_report_risk_enabled", "true");
        renderReport();
      });
    }
    return;
  }

  if (sec) sec.classList.remove("print:hidden");

  // 1. 고위험 클레임 추출 (품질, 배송, 서비스)
  const validChats = chats.filter((c) => c.valid);
  const qHigh = validChats.filter((c) => c.nature === "클레임" && c.risk === "HIGH" && ["물티슈", "스킨케어", "패밀리", "헬로", "홈"].includes(c.brand) && c.mid !== "배송");
  const dHigh = validChats.filter((c) => (c.mid === "배송" || (c.brand && c.brand.startsWith("배송"))) && c.risk === "HIGH");
  const sHigh = validChats.filter((c) => E.getServiceCategory(c) === "상급자통화" || (c.nature === "클레임" && c.risk === "HIGH" && !["물티슈", "스킨케어", "패밀리", "헬로", "홈"].includes(c.brand) && c.mid !== "배송"));
  const claimHighList = [...qHigh, ...dHigh, ...sHigh];

  // 2. 단순문의 중 전기간 대비 급증(+40%↑ 또는 신규 >= 3건) 이상징후 감지 (이슈업 대상)
  const curInqChats = validChats.filter((c) => c.nature === "문의");
  const prevInqChats = prevChats ? prevChats.filter((c) => c.valid && c.nature === "문의") : [];
  const curInqCounts = Object.fromEntries(E.groupCount(curInqChats, "tag"));
  const prevInqCounts = Object.fromEntries(E.groupCount(prevInqChats, "tag"));

  const surgedInqTags = [];
  for (const [tag, count] of Object.entries(curInqCounts)) {
    const prevCount = prevInqCounts[tag] || 0;
    if (count >= 3 && (prevCount === 0 || (count - prevCount) / prevCount >= 0.4)) {
      const pct = prevCount === 0 ? "신규" : `+${Math.round(((count - prevCount) / prevCount) * 100)}%`;
      surgedInqTags.push({ tag, count, prevCount, pct });
    }
  }
  surgedInqTags.sort((a, b) => b.count - a.count);
  const surgedTagMap = new Map(surgedInqTags.map((s) => [s.tag, s]));
  const surgedInqChats = curInqChats.filter((c) => surgedTagMap.has(c.tag));

  // 종합 이슈업 목록 (고위험 클레임 + 단순문의 급증)
  const allIssueList = [...claimHighList, ...surgedInqChats];

  if (allIssueList.length === 0) {
    container.innerHTML = `
      <div class="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4 text-xs text-emerald-800 flex items-center justify-between shadow-2xs">
        <div class="flex items-center gap-3">
          <span class="text-xl">✅</span>
          <div>
            <p class="font-bold text-sm text-emerald-900">현재 고위험(HIGH) 리스크 및 단순문의 급증 이상징후가 0건입니다.</p>
            <p class="text-emerald-700 text-xs mt-0.5">품질 변질/이물, 배송 대량 파손, 서비스 관리자 이관 및 단순문의 폭증 없이 안정적으로 운영 관리되고 있습니다.</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <span class="rounded-full bg-emerald-100 border border-emerald-300 text-emerald-800 px-3 py-1 text-xs font-bold">안심 관리 중 ✓</span>
          <button id="btnTurnOffZeroRisk" type="button" class="text-xs text-zinc-400 hover:text-zinc-600 underline ml-2 cursor-pointer" title="이 기간 동안 리포트에서 본 섹션 숨기기">섹션 숨기기(OFF)</button>
        </div>
      </div>
    `;
    const btnOff = document.getElementById("btnTurnOffZeroRisk");
    if (btnOff) {
      btnOff.addEventListener("click", () => {
        reportRiskSectionEnabled = false;
        localStorage.setItem("voc_report_risk_enabled", "false");
        renderReport();
      });
    }
    return;
  }

  // 4대 요약 배지
  const summaryBadges = `
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-3">
      <div class="rounded-lg bg-amber-50 border border-amber-200/80 p-2.5 flex items-center justify-between">
        <span class="text-xs font-semibold text-amber-900 flex items-center gap-1.5"><span>🔬</span>품질 리스크</span>
        <span class="tnum font-extrabold text-sm text-amber-950">${qHigh.length.toLocaleString()}건</span>
      </div>
      <div class="rounded-lg bg-rose-50 border border-rose-200/80 p-2.5 flex items-center justify-between">
        <span class="text-xs font-semibold text-rose-900 flex items-center gap-1.5"><span>🚚</span>배송 리스크</span>
        <span class="tnum font-extrabold text-sm text-rose-950">${dHigh.length.toLocaleString()}건</span>
      </div>
      <div class="rounded-lg bg-teal-50 border border-teal-200/80 p-2.5 flex items-center justify-between">
        <span class="text-xs font-semibold text-teal-900 flex items-center gap-1.5"><span>💬</span>서비스 리스크</span>
        <span class="tnum font-extrabold text-sm text-teal-950">${sHigh.length.toLocaleString()}건</span>
      </div>
      <div class="rounded-lg bg-indigo-50 border border-indigo-200/80 p-2.5 flex items-center justify-between">
        <span class="text-xs font-semibold text-indigo-900 flex items-center gap-1.5" title="단순 문의 중 전기간 대비 +40% 이상 폭증한 이상징후 태그"><span>⚡</span>단순문의 급증</span>
        <span class="tnum font-extrabold text-sm text-indigo-950">${surgedInqChats.length.toLocaleString()}건 <span class="text-[10px] font-normal text-indigo-600">(${surgedInqTags.length}개태그)</span></span>
      </div>
    </div>
  `;

  // Filter list based on reportRiskSubFilter
  let targetList = allIssueList;
  if (reportRiskSubFilter === "claim") targetList = claimHighList;
  else if (reportRiskSubFilter === "inquiry") targetList = surgedInqChats;

  const displayList = reportRiskExpanded ? targetList : targetList.slice(0, 6);

  const rows = displayList.map((c) => {
    let catBadge = "";
    if (c.nature === "문의") {
      const sInfo = surgedTagMap.get(c.tag);
      const pctText = sInfo ? sInfo.pct : "+40%↑";
      catBadge = `<span class="rounded bg-indigo-100 text-indigo-900 border border-indigo-300 px-1.5 py-0.5 text-[10px] font-bold">단순 급증 ${pctText}</span>`;
    } else if (qHigh.includes(c)) {
      catBadge = '<span class="rounded bg-amber-100 text-amber-800 border border-amber-300 px-1.5 py-0.5 text-[10px] font-bold">품질 HIGH</span>';
    } else if (dHigh.includes(c)) {
      catBadge = '<span class="rounded bg-rose-100 text-rose-800 border border-rose-300 px-1.5 py-0.5 text-[10px] font-bold">배송 파손</span>';
    } else {
      catBadge = '<span class="rounded bg-teal-100 text-teal-800 border border-teal-300 px-1.5 py-0.5 text-[10px] font-bold">상급자/강성</span>';
    }

    const custName = getChatCustomerName(c);
    const tagPrefix = c.nature === "문의" ? `<span class="text-indigo-900 font-semibold">[${(c.tag || "").replace(/^단순\//, "")}]</span> ` : "";
    const issueText = (c.issue || c.tag || "접수 내용 미기재").replace(/</g, "&lt;");
    const actText = (c.act || (c.nature === "문의" ? "단순 문의 신속 안내 및 급증 원인 유관부서(마케팅/물류) 공유" : "담당부서 즉시 전달 및 맞교환/환불 조치 완료")).replace(/</g, "&lt;");

    return `
      <tr class="hover:bg-zinc-50/70 transition">
        <td class="py-2 px-2 whitespace-nowrap">${catBadge}</td>
        <td class="py-2 px-2 text-zinc-600 whitespace-nowrap tnum text-[11px]">${c.channel || "채널톡"}</td>
        <td class="py-2 px-2 font-medium text-zinc-900 whitespace-nowrap">${custName}</td>
        <td class="py-2 px-2 text-zinc-700 font-medium truncate max-w-[120px]" title="${c.prod || c.brand || ""}">${c.prod || c.brand || "–"}</td>
        <td class="py-2 px-3 text-zinc-800 break-words max-w-xs text-xs">${tagPrefix}${issueText}</td>
        <td class="py-2 px-3 text-emerald-800 font-medium break-words max-w-xs text-xs flex items-center gap-1.5">
          <span class="text-emerald-600 font-bold">✓</span>
          <span>${actText}</span>
        </td>
      </tr>
    `;
  }).join("");

  let subFilterBar = `
    <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5 text-xs border-b border-black/5 pb-2">
      <div class="flex items-center gap-1">
        <span class="text-zinc-400 font-medium mr-1">보기 필터:</span>
        <button type="button" data-rfilter="all" class="risk-sub-btn px-2 py-0.5 rounded text-xs transition cursor-pointer ${reportRiskSubFilter === 'all' ? 'bg-zinc-900 text-white font-semibold' : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'}">전체 이슈업 (${allIssueList.length}건)</button>
        <button type="button" data-rfilter="claim" class="risk-sub-btn px-2 py-0.5 rounded text-xs transition cursor-pointer ${reportRiskSubFilter === 'claim' ? 'bg-zinc-900 text-white font-semibold' : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'}">⚠️ 고위험 클레임 (${claimHighList.length}건)</button>
        <button type="button" data-rfilter="inquiry" class="risk-sub-btn px-2 py-0.5 rounded text-xs transition cursor-pointer ${reportRiskSubFilter === 'inquiry' ? 'bg-zinc-900 text-white font-semibold' : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'}">⚡ 단순문의 급증 (${surgedInqChats.length}건)</button>
      </div>
      ${surgedInqTags.length ? `<span class="text-[11px] text-indigo-700 font-medium bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200/60">주요 급증: ${surgedInqTags.slice(0, 2).map((s) => s.tag.replace(/^단순\//, "") + " " + s.pct).join(", ")}</span>` : ""}
    </div>
  `;

  let expandControl = "";
  if (targetList.length > 6) {
    expandControl = `
      <div class="mt-2.5 flex items-center justify-between text-[11px] text-zinc-400 border-t border-zinc-100 pt-2">
        <span>선택 조건 <strong>${targetList.length}건</strong> 중 ${displayList.length}건 표시 중</span>
        <button id="btnToggleRiskExpand" type="button" class="font-semibold text-teal-700 hover:text-teal-900 transition flex items-center gap-1 cursor-pointer">
          ${reportRiskExpanded ? "▲ 6건만 간략히 보기" : `▼ 외 ${targetList.length - 6}건 전체 펼쳐보기`}
        </button>
      </div>
    `;
  }

  container.innerHTML = `
    <div class="rounded-xl border border-zinc-200 bg-white p-3.5 shadow-2xs">
      ${summaryBadges}
      ${subFilterBar}
      <div class="rounded-lg border border-black/5 overflow-hidden">
        <table class="w-full text-left text-xs">
          <thead class="bg-zinc-50 text-zinc-600 border-b border-black/5 font-medium">
            <tr>
              <th class="py-2 px-2 w-28">부문 / 이슈 구분</th>
              <th class="py-2 px-2 w-16">채널</th>
              <th class="py-2 px-2 w-16">고객명</th>
              <th class="py-2 px-2 w-28">관련 제품 / 브랜드</th>
              <th class="py-2 px-3">고객 불만 / 문의 핵심 원문</th>
              <th class="py-2 px-3">CS 조치 결과 및 개선점</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-black/5">
            ${rows || '<tr><td colspan="6" class="py-6 text-center text-zinc-400">해당 조건의 이슈 건이 없습니다.</td></tr>'}
          </tbody>
        </table>
      </div>
      ${expandControl}
    </div>
  `;

  // Sub filter click listeners
  container.querySelectorAll(".risk-sub-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      reportRiskSubFilter = btn.dataset.rfilter;
      reportRiskExpanded = false;
      renderReportRiskActions(period, chats, prevChats);
    });
  });

  const btnExp = document.getElementById("btnToggleRiskExpand");
  if (btnExp) {
    btnExp.addEventListener("click", () => {
      reportRiskExpanded = !reportRiskExpanded;
      renderReportRiskActions(period, chats, prevChats);
    });
  }
}

function renderReport() {
  const period = E.getPeriod();
  const prev = E.prevPeriod();
  const chats = E.rawChats(period).filter((c) => c.valid && c.channel !== "배송접수");
  const prevChats = prev ? E.rawChats(prev).filter((c) => c.valid && c.channel !== "배송접수") : null;
  const board = E.boardCount(period);
  const prevBoard = prev ? E.boardCount(prev) : null;

  const curRaw = E.getRawSummary ? E.getRawSummary(period) : null;
  const prevRaw = prev && E.getRawSummary ? E.getRawSummary(prev) : null;
  const total = curRaw && curRaw.total_offered_raw ? curRaw.total_offered_raw : (chats.length + board);
  const prevTotal = prevRaw && prevRaw.total_offered_raw ? prevRaw.total_offered_raw : (prevChats ? prevChats.length + prevBoard : null);

  const rawShipments = E.rawShipments ? E.rawShipments(period) : [];
  const prevShipments = prev && E.rawShipments ? E.rawShipments(prev) : [];
  const shipCount = rawShipments.length;
  const prevShipCount = prevShipments.length;

  const curCti = E.aggregateCti ? E.aggregateCti(period) : null;
  const callsCount = curRaw?.raw_call != null ? curRaw.raw_call : (curCti ? curCti.totalCalls : chats.filter((c) => c.channel === "전화").length);
  const chatsCount = curRaw?.raw_chat != null ? curRaw.raw_chat : chats.filter((c) => c.channel === "상담사챗" || c.channel === "챗봇(ALF)").length;
  const curOp = E.getOperationalKpi ? E.getOperationalKpi(period) : null;
  const handledTotal = curOp?.handled_contacts != null ? curOp.handled_contacts : (chats.filter((c) => c.channel === "전화").length + chatsCount + board);

  const periodDisp = formatPeriodDisplayLabel(period, E.state.mode);
  const dateRange = period.label ? period.label.replace(/202[56]년\s*/, "") : "";
  const repModeName = E.state.mode === "weekly" ? "주간" : (E.state.mode === "monthly" ? "월간" : (E.state.mode === "quarterly" ? "분기" : "연간"));
  document.getElementById("reportTitle").textContent = `${periodDisp} (${dateRange || period.label}) ${repModeName} VOC 종합 리포트`;

  const buckets = E.claimBuckets(chats);
  const pb = prevChats ? E.claimBuckets(prevChats) : null;

  const dCount = shipCount > 0 ? shipCount : buckets.delivery.length;
  const prevDCount = shipCount > 0 ? (prevShipCount || null) : (pb ? pb.delivery.length : null);
  const qWipes = buckets.quality.filter((c) => c.brand === "물티슈").length;
  const qOthers = buckets.quality.length - qWipes;

  // 1. VOC 요약 KPI
  document.getElementById("reportKpi").innerHTML =
    reportKpiBox("총 인입 (전수)", total.toLocaleString(), prevTotal != null ? total - prevTotal : null, {
      subText: `실응대 ${handledTotal.toLocaleString()}건 (콜 ${callsCount.toLocaleString()} · 채팅 ${chatsCount.toLocaleString()} · 게시판 ${board.toLocaleString()})`
    }) +
    reportKpiBox("품질 클레임", buckets.quality.length, pb ? buckets.quality.length - pb.quality.length : null, {
      inverse: true,
      subText: `물티슈 ${qWipes}건 · 홈/공통 ${qOthers}건`
    }) +
    reportKpiBox("배송 클레임", dCount, prevDCount != null ? dCount - prevDCount : null, {
      inverse: true,
      subText: shipCount > 0 ? `물류 원장 ${shipCount}건 (상담접수 ${buckets.delivery.length}건)` : `상담접수 ${buckets.delivery.length}건`
    }) +
    reportKpiBox("서비스 클레임", buckets.service.length, pb ? buckets.service.length - pb.service.length : null, {
      inverse: true,
      subText: `상급자통화 · 휴먼에러 · 시스템`
    });

  // 2. 채널별 추이 (4주, 4개월, 4분기, 2년)
  const recent = reportRecentPeriods();
  const periodUnitText = E.state.mode === "weekly" ? "최근 4주" : (E.state.mode === "monthly" ? "최근 4개월" : (E.state.mode === "quarterly" ? "최근 4분기" : "최근 2년"));
  const repBadge = document.getElementById("reportChannelPeriodBadge");
  if (repBadge) repBadge.textContent = `(${periodUnitText} 추이)`;
  renderReportChannelChart(recent, period);

  // 3. 부문별 클레임 현황 & 이슈 인사이트 (품질 · 배송 · 서비스 3대 부문 통합)
  renderReportThreePillars(period, prev, buckets, pb, recent);

  // 4. 핵심 리스크 & 긴급 조치 현황 (Risk & Action Summary - 단순문의 급증 포함)
  renderReportRiskActions(period, chats, prevChats);

  // 5. CX팀 코멘트 (해당 선택 기간에 작성된 독립 코멘트만 노출)
  const memos = loadMemos();
  const memoList = (period && period.key && Array.isArray(memos[period.key])) ? memos[period.key] : [];
  document.getElementById("reportMemo").innerHTML = memoList.length
    ? memoList.map((m) => `<div class="rounded-lg bg-zinc-50 p-3 text-sm text-zinc-700 ring-1 ring-black/5"><p class="whitespace-pre-wrap">${m.text.replace(/</g, "&lt;")}</p></div>`).join("")
    : `<p class="text-xs text-zinc-400">대시보드 '이슈 메모'에 작성한 ${period.label} 코멘트가 이 리포트에 표시됩니다.</p>`;

  if (typeof applyUserRolePermissions === "function") {
    applyUserRolePermissions(window.getCurrentUser());
  }
}

async function exportReportExcel() {
  if (typeof window.isUserAdmin === "function" && !window.isUserAdmin()) {
    alert("리포트 엑셀 다운로드는 관리자(cx) 계정만 가능합니다.");
    return;
  }

  const period = E.getPeriod();
  if (!period) return;

  const repExcelBtn = document.getElementById("reportExportExcel");
  const origBtnHtml = repExcelBtn ? repExcelBtn.innerHTML : "";
  if (repExcelBtn) {
    repExcelBtn.innerHTML = `
      <span class="inline-flex items-center gap-1.5">
        <svg class="animate-spin h-3.5 w-3.5 text-teal-700 inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
        </svg>
        <span>엑셀 생성 중...</span>
      </span>
    `;
    repExcelBtn.disabled = true;
  }

  const periodDisp = formatPeriodDisplayLabel(period, E.state.mode);
  const safePeriod = periodDisp.replace(/[\s\(\)\/\:\-]/g, "_");
  const downloadFileName = `[CX팀]_VOC_분석종합리포트_${safePeriod}.xlsx`;

  // 프로그레스 게이지 모달 초기화
  const progressModal = document.getElementById("exportProgressModal");
  const progressStatus = document.getElementById("exportProgressStatus");
  const progressPct = document.getElementById("exportProgressPct");
  const progressBar = document.getElementById("exportProgressBar");
  const progressSub = document.getElementById("exportProgressSub");
  const progressPeriod = document.getElementById("exportProgressPeriod");

  if (progressPeriod) progressPeriod.textContent = `[CX팀] ${periodDisp} VOC 분석 종합 리포트 및 전수 원장(품질/배송)`;
  if (progressModal) progressModal.classList.remove("hidden");

  function setProgress(pct, statusText, subText) {
    if (progressPct) progressPct.textContent = `${pct}%`;
    if (progressBar) progressBar.style.width = `${pct}%`;
    if (progressStatus) progressStatus.textContent = statusText;
    if (subText && progressSub) progressSub.textContent = subText;
  }

  setProgress(10, "1. 분석 메타데이터 및 코멘트 취합 중...", "네이티브 차트, 품질raw, 배송raw, 사진 및 보상내역서를 정합 중입니다.");

  let curProg = 10;
  const progTimer = setInterval(() => {
    if (curProg < 30) {
      curProg += 5;
      setProgress(curProg, "2. VOC 종합 요약 및 채널 추이 차트 렌더링 중...");
    } else if (curProg < 55) {
      curProg += 4;
      setProgress(curProg, "3. 품질raw 및 신규 배송raw 원장 작성 중...");
    } else if (curProg < 78) {
      curProg += 3;
      setProgress(curProg, "4. 클레임 사진 및 보상내역서(월간/전체) 정합 중...");
    } else if (curProg < 92) {
      curProg += 2;
      setProgress(curProg, "5. 워크북 서식 패키징 및 최종 정합성 검증 중...");
    } else if (curProg < 98) {
      curProg += 1;
      setProgress(curProg, "5. 대용량 파일 압축 및 다운로드 전송 대기 중...", "데이터 분량이 많아 정합 패키징을 마무리하고 있습니다.");
    }
  }, 700);

  try {
    // 1. 파이썬 서버 API 호출 (선택된 기간 전용 독립 코멘트만 추출 및 전송)
    const allMemos = loadMemos();
    const memoList = (period && period.key && Array.isArray(allMemos[period.key])) ? allMemos[period.key] : [];
    const curInsights = {};
    ["quality", "delivery", "service"].forEach((cat) => {
      const catMemos = getCategoryMemos(cat, period);
      if (catMemos.length > 0) {
        curInsights[cat] = catMemos.map((m) => m.text).join("\n");
      }
    });

    const payload = {
      period: period.key,
      memos: memoList,
      insights: curInsights
    };

    let res;
    try {
      res = await fetch("/api/export_report_excel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    } catch (postErr) {
      const url = `/api/export_report_excel?period=${encodeURIComponent(period.key)}`;
      res = await fetch(url);
    }

    if (!res.ok) throw new Error("서버 엑셀 생성 응답 실패 (" + res.status + ")");

    const blob = await res.blob();
    clearInterval(progTimer);
    setProgress(100, "✓ 완료! 엑셀 파일 다운로드를 시작합니다.", `브라우저 다운로드 창을 확인하세요 (${downloadFileName})`);
    if (progressBar) {
      progressBar.classList.remove("from-teal-500", "to-teal-700");
      progressBar.classList.add("bg-emerald-500");
    }

    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = downloadFileName;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    }, 1500);

    setTimeout(() => {
      if (progressModal) progressModal.classList.add("hidden");
    }, 2000);
    return;
  } catch (err) {
    clearInterval(progTimer);
    console.error("서버 네이티브 엑셀 생성 실패, 클라이언트 백업 생성 시도:", err);
    setProgress(95, "클라이언트 백업 모드로 전환 중...", err.message);
    try {
      await exportReportExcelClientFallback(period, periodDisp, downloadFileName);
      setProgress(100, "✓ 백업 완료! 다운로드를 시작합니다.");
      setTimeout(() => {
        if (progressModal) progressModal.classList.add("hidden");
      }, 800);
    } catch (fallbackErr) {
      console.error("클라이언트 엑셀 생성도 실패:", fallbackErr);
      setProgress(100, "❌ 리포트 엑셀 생성 실패", err.message || fallbackErr.message);
      if (progressBar) progressBar.classList.add("bg-rose-500");
      setTimeout(() => {
        if (progressModal) progressModal.classList.add("hidden");
      }, 3500);
    }
  } finally {
    if (repExcelBtn) {
      repExcelBtn.innerHTML = origBtnHtml;
      repExcelBtn.disabled = false;
    }
  }
}

async function exportReportExcelClientFallback(period, periodDisp, downloadFileName) {
  if (typeof ExcelJS === "undefined") {
    alert("ExcelJS 라이브러리를 불러오지 못했습니다.");
    return;
  }

  const prev = E.prevPeriod();
  const chats = E.rawChats(period).filter((c) => c.valid && c.channel !== "배송접수");
  const prevChats = prev ? E.rawChats(prev).filter((c) => c.valid && c.channel !== "배송접수") : null;
  const board = E.boardCount(period);
  const prevBoard = prev ? E.boardCount(prev) : null;

  const curRaw = E.getRawSummary ? E.getRawSummary(period) : null;
  const prevRaw = prev && E.getRawSummary ? E.getRawSummary(prev) : null;
  const total = curRaw && curRaw.total_offered_raw ? curRaw.total_offered_raw : (chats.length + board);
  const prevTotal = prevRaw && prevRaw.total_offered_raw ? prevRaw.total_offered_raw : (prevChats ? prevChats.length + prevBoard : null);
  const buckets = E.claimBuckets(chats);
  const pb = prevChats ? E.claimBuckets(prevChats) : null;

  const rawShipments = E.rawShipments ? E.rawShipments(period) : [];
  const prevShipments = prev && E.rawShipments ? E.rawShipments(prev) : [];
  const deliveryCount = rawShipments.length > 0 ? rawShipments.length : buckets.delivery.length;
  const prevDeliveryCount = rawShipments.length > 0 ? (prevShipments.length || null) : (pb ? pb.delivery.length : null);

  const dateRange = period.label ? period.label.replace(/202[56]년\s*/, "") : "";
  const recent = reportRecentPeriods();

  const wb = new ExcelJS.Workbook();
  wb.creator = "CX팀 VOC 분석 시스템";
  wb.created = new Date();

  const ws = wb.addWorksheet("VOC_분석종합리포트", {
    views: [{ showGridLines: true }]
  });

  // Column definitions (A~F)
  ws.columns = [
    { key: "colA", width: 16 },
    { key: "colB", width: 24 },
    { key: "colC", width: 16 },
    { key: "colD", width: 20 },
    { key: "colE", width: 32 },
    { key: "colF", width: 36 }
  ];

  // Helper styles
  const fontTitle = { name: "맑은 고딕", size: 15, bold: true, color: { argb: "FF0F766E" } };
  const fontSecHeader = { name: "맑은 고딕", size: 11, bold: true, color: { argb: "FF111827" } };
  const fontTblHeader = { name: "맑은 고딕", size: 9.5, bold: true, color: { argb: "FFFFFFFF" } };
  const fontRegular = { name: "맑은 고딕", size: 9.5, color: { argb: "FF1F2937" } };
  const fontBold = { name: "맑은 고딕", size: 9.5, bold: true, color: { argb: "FF1F2937" } };
  const fontMeta = { name: "맑은 고딕", size: 9.5, color: { argb: "FF4B5563" } };
  const fontMuted = { name: "맑은 고딕", size: 9, color: { argb: "FF6B7280" } };

  const borderThin = {
    top: { style: "thin", color: { argb: "FFD4D4D4" } },
    left: { style: "thin", color: { argb: "FFD4D4D4" } },
    bottom: { style: "thin", color: { argb: "FFD4D4D4" } },
    right: { style: "thin", color: { argb: "FFD4D4D4" } }
  };

  const fillHeader = { type: "pattern", pattern: "solid", fgColor: { argb: "FF0F766E" } }; // Teal-700
  const fillZebra = { type: "pattern", pattern: "solid", fgColor: { argb: "FFF8FAFC" } };
  const fillTotal = { type: "pattern", pattern: "solid", fgColor: { argb: "FFF1F5F9" } };

  function applyBox(startR, startC, endR, endC, fill, border) {
    for (let r = startR; r <= endR; r++) {
      for (let c = startC; c <= endC; c++) {
        const cell = ws.getCell(r, c);
        if (fill) cell.fill = fill;
        if (border) cell.border = border;
      }
    }
  }

  // Row 1: Spacer
  ws.getRow(1).height = 12;

  // Row 2: Title Banner (Merged A2:F2)
  ws.mergeCells("A2:F2");
  const r2 = ws.getRow(2);
  r2.height = 38;
  applyBox(2, 1, 2, 6,
    { type: "pattern", pattern: "solid", fgColor: { argb: "FFF0FDFA" } },
    {
      top: { style: "medium", color: { argb: "FF0F766E" } },
      left: { style: "thin", color: { argb: "FF0F766E" } },
      bottom: { style: "double", color: { argb: "FF0F766E" } },
      right: { style: "thin", color: { argb: "FF0F766E" } }
    }
  );
  const tCell = ws.getCell("A2");
  tCell.value = `[CX팀] VOC 분석 종합 리포트 (${periodDisp})`;
  tCell.font = fontTitle;
  tCell.alignment = { vertical: "middle", horizontal: "center" };

  // Row 3: Spacer
  ws.getRow(3).height = 8;

  // Row 4-6: Metadata
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const nowStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`;

  ws.getCell("A4").value = `● 분석 대상 기간 : ${periodDisp} (${dateRange || period.label})`;
  ws.getCell("A4").font = fontMeta;
  ws.getRow(4).height = 18;

  ws.getCell("A5").value = `● 데이터 연동 기준 : 채널톡 채팅 / CTI 전화 / 자사몰 및 스토어 게시판 전수 (작성부서: CX팀)`;
  ws.getCell("A5").font = fontMeta;
  ws.getRow(5).height = 18;

  ws.getCell("A6").value = `● 보고서 추출 일시 : ${nowStr}`;
  ws.getCell("A6").font = fontMeta;
  ws.getRow(6).height = 18;

  let rowIdx = 8;

  // ==========================================
  // [1. VOC 요약 (KPI)]
  // ==========================================
  ws.getCell(rowIdx, 1).value = "1. VOC 요약 (인입 및 3대 클레임 총괄)";
  ws.getCell(rowIdx, 1).font = fontSecHeader;
  ws.getRow(rowIdx).height = 24;
  rowIdx++;

  const kpiHeaders = ["구분", "현재 건수", "이전 건수", "이전 대비 증감", "증감율", "비중 (전체 대비)"];
  const rKpiH = ws.getRow(rowIdx);
  rKpiH.height = 24;
  kpiHeaders.forEach((h, i) => {
    const c = ws.getCell(rowIdx, i + 1);
    c.value = h;
    c.font = fontTblHeader;
    c.fill = fillHeader;
    c.alignment = { vertical: "middle", horizontal: "center" };
    c.border = borderThin;
  });
  rowIdx++;

  function calcDiffStr(cur, prv) {
    if (prv == null) return "-";
    const diff = cur - prv;
    if (diff === 0) return "0";
    return diff > 0 ? `▲ +${diff.toLocaleString()}` : `▼ -${Math.abs(diff).toLocaleString()}`;
  }
  function calcPctStr(cur, prv) {
    if (prv == null || prv === 0) return "-";
    const pct = ((cur - prv) / prv) * 100;
    return `${pct > 0 ? "+" : ""}${pct.toFixed(1)}%`;
  }

  const kpiData = [
    {
      name: "총 인입 전수 (공식 Total)",
      cur: total,
      prv: prevTotal,
      share: "100.0%"
    },
    {
      name: "품질 클레임 (Quality)",
      cur: buckets.quality.length,
      prv: pb ? pb.quality.length : null,
      share: total > 0 ? `${((buckets.quality.length / total) * 100).toFixed(1)}%` : "0%"
    },
    {
      name: "배송 클레임 (Delivery)",
      cur: deliveryCount,
      prv: prevDeliveryCount,
      share: total > 0 ? `${((deliveryCount / total) * 100).toFixed(1)}%` : "0%"
    },
    {
      name: "서비스 클레임 (Service)",
      cur: buckets.service.length,
      prv: pb ? pb.service.length : null,
      share: total > 0 ? `${((buckets.service.length / total) * 100).toFixed(1)}%` : "0%"
    }
  ];

  kpiData.forEach((item, idx) => {
    const row = ws.getRow(rowIdx);
    row.height = 21;
    const isTotal = idx === 0;

    const c1 = ws.getCell(rowIdx, 1);
    c1.value = item.name;
    c1.font = isTotal ? fontBold : fontRegular;
    c1.alignment = { vertical: "middle", horizontal: "left", indent: 1 };
    c1.border = borderThin;

    const c2 = ws.getCell(rowIdx, 2);
    c2.value = item.cur;
    c2.numFmt = "#,##0";
    c2.font = isTotal ? fontBold : fontRegular;
    c2.alignment = { vertical: "middle", horizontal: "right" };
    c2.border = borderThin;

    const c3 = ws.getCell(rowIdx, 3);
    c3.value = item.prv != null ? item.prv : "-";
    if (item.prv != null) c3.numFmt = "#,##0";
    c3.font = fontRegular;
    c3.alignment = { vertical: "middle", horizontal: "right" };
    c3.border = borderThin;

    const c4 = ws.getCell(rowIdx, 4);
    c4.value = calcDiffStr(item.cur, item.prv);
    c4.font = fontRegular;
    c4.alignment = { vertical: "middle", horizontal: "center" };
    c4.border = borderThin;

    const c5 = ws.getCell(rowIdx, 5);
    c5.value = calcPctStr(item.cur, item.prv);
    c5.font = fontRegular;
    c5.alignment = { vertical: "middle", horizontal: "center" };
    c5.border = borderThin;

    const c6 = ws.getCell(rowIdx, 6);
    c6.value = item.share;
    c6.font = fontRegular;
    c6.alignment = { vertical: "middle", horizontal: "center" };
    c6.border = borderThin;

    if (isTotal) {
      applyBox(rowIdx, 1, rowIdx, 6, fillTotal, null);
    }
    rowIdx++;
  });

  rowIdx++; // Spacer

  // ==========================================
  // [2. 채널별 인입 실적 & 최근 추이]
  // ==========================================
  const periodUnitText = E.state.mode === "weekly" ? "최근 4주" : (E.state.mode === "monthly" ? "최근 4개월" : (E.state.mode === "quarterly" ? "최근 4분기" : "최근 2년"));
  ws.getCell(rowIdx, 1).value = `2. 채널별 인입 실적 & 최근 추이 (${periodUnitText})`;
  ws.getCell(rowIdx, 1).font = fontSecHeader;
  ws.getRow(rowIdx).height = 24;
  rowIdx++;

  // ★ [고품격 시각화] 웹 화면의 Chart.js 채널별 추이 차트 이미지 그대로 임베딩
  if (chanChartImg) {
    const imgId = wb.addImage({
      base64: chanChartImg,
      extension: "png"
    });
    ws.addImage(imgId, {
      tl: { col: 0, row: rowIdx - 1 },
      ext: { width: 800, height: 260 }
    });
    for (let r = 0; r < 13; r++) {
      ws.getRow(rowIdx + r).height = 20;
    }
    rowIdx += 13;
    rowIdx++; // Spacer
  }

  const recentHeaders = ["채널 구분", ...recent.map((p) => formatPeriodDisplayLabel(p, E.state.mode) + (p.key === period.key ? " (현재)" : "")), "현재 점유율"];
  const rChanH = ws.getRow(rowIdx);
  rChanH.height = 24;
  recentHeaders.forEach((h, i) => {
    const c = ws.getCell(rowIdx, i + 1);
    c.value = h;
    c.font = fontTblHeader;
    c.fill = fillHeader;
    c.alignment = { vertical: "middle", horizontal: "center" };
    c.border = borderThin;
  });
  rowIdx++;

  const channelRows = [
    {
      name: "전화 (인바운드)",
      counts: recent.map((p) => E.rawChats(p).filter((c) => c.valid && c.channel === "전화" && (c.direction || "INBOUND") === "INBOUND").length)
    },
    {
      name: "채팅 (인 & 아웃)",
      counts: recent.map((p) => E.rawChats(p).filter((c) => c.valid && (c.channel === "상담사챗" || c.channel === "챗봇(ALF)")).length)
    },
    {
      name: "게시판 (스토어/자사몰)",
      counts: recent.map((p) => E.boardCount(p))
    }
  ];

  const recentTotals = recent.map((p, idx) => {
    return channelRows.reduce((sum, r) => sum + r.counts[idx], 0);
  });
  const curTot = recentTotals[recentTotals.length - 1] || 1;

  channelRows.forEach((ch) => {
    const row = ws.getRow(rowIdx);
    row.height = 20;

    const c1 = ws.getCell(rowIdx, 1);
    c1.value = ch.name;
    c1.font = fontRegular;
    c1.alignment = { vertical: "middle", horizontal: "left", indent: 1 };
    c1.border = borderThin;

    ch.counts.forEach((val, i) => {
      const c = ws.getCell(rowIdx, i + 2);
      c.value = val;
      c.numFmt = "#,##0";
      c.font = fontRegular;
      c.alignment = { vertical: "middle", horizontal: "right" };
      c.border = borderThin;
    });

    const lastVal = ch.counts[ch.counts.length - 1] || 0;
    const cShare = ws.getCell(rowIdx, ch.counts.length + 2);
    cShare.value = `${((lastVal / curTot) * 100).toFixed(1)}%`;
    cShare.font = fontRegular;
    cShare.alignment = { vertical: "middle", horizontal: "center" };
    cShare.border = borderThin;

    rowIdx++;
  });

  // Channel Total Row
  const rChanTot = ws.getRow(rowIdx);
  rChanTot.height = 22;
  const cT1 = ws.getCell(rowIdx, 1);
  cT1.value = "인입 총합계";
  cT1.font = fontBold;
  cT1.alignment = { vertical: "middle", horizontal: "center" };
  cT1.border = borderThin;

  recentTotals.forEach((val, i) => {
    const c = ws.getCell(rowIdx, i + 2);
    c.value = val;
    c.numFmt = "#,##0";
    c.font = fontBold;
    c.alignment = { vertical: "middle", horizontal: "right" };
    c.border = borderThin;
  });

  const cTShare = ws.getCell(rowIdx, recentTotals.length + 2);
  cTShare.value = "100.0%";
  cTShare.font = fontBold;
  cTShare.alignment = { vertical: "middle", horizontal: "center" };
  cTShare.border = borderThin;

  applyBox(rowIdx, 1, rowIdx, recentHeaders.length, fillTotal, null);
  rowIdx += 2; // Spacer

  // ==========================================
  // [3. 부문별 클레임 현황 & 이슈 인사이트 (품질 · 배송 · 서비스)]
  // ==========================================
  ws.getCell(rowIdx, 1).value = `3. 부문별 클레임 현황 & 이슈 인사이트 (품질 · 배송 · 서비스 3대 부문)`;
  ws.getCell(rowIdx, 1).font = fontSecHeader;
  ws.getRow(rowIdx).height = 24;
  rowIdx++;

  const qHighCount = buckets.quality.filter((c) => c.risk === "HIGH").length;
  const qTopBrand = claimDetail(buckets.quality, "brand")[0]?.label || "물티슈";
  const dBoxDmg = buckets.delivery.filter((c) => (c.sub || "").includes("박스파손") || (c.sub || "").includes("파손")).length;
  const dDelay = buckets.delivery.filter((c) => (c.sub || "").includes("지연")).length;
  const sEscCount = buckets.service.filter((c) => E.getServiceCategory(c) === "상급자통화" || c.risk === "HIGH").length;
  const sHuman = buckets.service.filter((c) => E.getServiceCategory(c) === "휴먼에러").length;

  const excelPillars = [
    {
      id: "quality",
      name: "품질 클레임 (Quality)",
      total: buckets.quality.length,
      prevTotal: pb ? pb.quality.length : null,
      focusSummary: `고위험 리스크: ${qHighCount}건 · 최다 불만 브랜드: ${qTopBrand}`,
      subBg: { type: "pattern", pattern: "solid", fgColor: { argb: "FFFEF3C7" } }, // Amber-100
      subBorder: {
        top: { style: "medium", color: { argb: "FFD97706" } },
        left: { style: "thin", color: { argb: "FFD97706" } },
        bottom: { style: "thin", color: { argb: "FFD97706" } },
        right: { style: "thin", color: { argb: "FFD97706" } }
      },
      items: claimDetail(buckets.quality, "sub").slice(0, 4),
      memos: getCategoryMemos("quality", period),
      defaultComment: buckets.quality.length
        ? `• ${claimDetail(buckets.quality, "sub")[0]?.label || "포장/용액"} 불만(${Number(claimDetail(buckets.quality, "sub")[0]?.count || 0).toLocaleString()}건) 비중이 높으며, 변질/이물 등 주요 품질 리스크 클레임에 대해 공정 분석 및 고객 안심 케어 진행 중.`
        : "• 선택 기간 접수된 품질 클레임이 없습니다."
    },
    {
      id: "delivery",
      name: "배송 클레임 (Delivery)",
      total: deliveryCount,
      prevTotal: prevDeliveryCount,
      focusSummary: rawShipments.length > 0
        ? `물류원장: 파손 ${rawShipments.filter((s) => (s.type || "").includes("파손")).length}건 · 오배송 ${rawShipments.filter((s) => (s.type || "").includes("오배송")).length}건 (상담접수 ${buckets.delivery.length}건)`
        : `파손/박스불만: ${dBoxDmg}건 · 배송지연: ${dDelay}건`,
      subBg: { type: "pattern", pattern: "solid", fgColor: { argb: "FFFFE4E6" } }, // Rose-100
      subBorder: {
        top: { style: "medium", color: { argb: "FFE11D48" } },
        left: { style: "thin", color: { argb: "FFE11D48" } },
        bottom: { style: "thin", color: { argb: "FFE11D48" } },
        right: { style: "thin", color: { argb: "FFE11D48" } }
      },
      items: rawShipments.length > 0
        ? E.groupCount(rawShipments, "type").filter((x) => x[0]).map(([label, count]) => ({ label, count })).slice(0, 5)
        : claimDetail(buckets.delivery, "sub").slice(0, 5),
      prevMap: pbShipMap,
      memos: getCategoryMemos("delivery", period),
      defaultComment: deliveryCount
        ? (rawShipments.length > 0
          ? `• 물류 벤더사(풀필먼트 및 CJ초저온) 원장 ${deliveryCount}건 (채널톡 배송상담 ${buckets.delivery.length}건). 오출고 재발 방지 및 택배 파손 맞교환 조치 완료.`
          : `• ${claimDetail(buckets.delivery, "sub")[0]?.label || "오배송/지연"} 접수(${Number(claimDetail(buckets.delivery, "sub")[0]?.count || 0).toLocaleString()}건) 중심. 물류 벤더사(풀필먼트 및 CJ초저온) 오출고 재발 방지 및 당일 맞교환 조치 완료.`)
        : "• 선택 기간 접수된 배송 클레임이 없습니다."
    },
    {
      id: "service",
      name: "서비스 클레임 (Service)",
      total: buckets.service.length,
      prevTotal: pb ? pb.service.length : null,
      focusSummary: `상급자/에스컬레이션: ${sEscCount}건 · 상담/휴먼에러: ${sHuman}건`,
      subBg: { type: "pattern", pattern: "solid", fgColor: { argb: "FFCCFBF1" } }, // Teal-100
      subBorder: {
        top: { style: "medium", color: { argb: "FF0D9488" } },
        left: { style: "thin", color: { argb: "FF0D9488" } },
        bottom: { style: "thin", color: { argb: "FF0D9488" } },
        right: { style: "thin", color: { argb: "FF0D9488" } }
      },
      items: E.groupCount(buckets.service, "mid").filter((x) => x[0] !== "").map(([label, count]) => ({ label: label || "기타", count })).slice(0, 5),
      prevMap: pbSvcMap,
      memos: getCategoryMemos("service", period),
      defaultComment: buckets.service.length
        ? `• ${E.groupCount(buckets.service, "mid")[0]?.[0] || "상담/시스템"} 문의(${Number(E.groupCount(buckets.service, "mid")[0]?.[1] || 0).toLocaleString()}건) 중심. 에스컬레이션 방지 및 첫 통화/채팅 해결율 집중 관리 중.`
        : "• 선택 기간 접수된 서비스 클레임이 없습니다."
    }
  ];

  excelPillars.forEach((ep) => {
    // 1) Pillar Banner Row
    ws.mergeCells(rowIdx, 1, rowIdx, 6);
    applyBox(rowIdx, 1, rowIdx, 6, ep.subBg, ep.subBorder);
    const rBanner = ws.getRow(rowIdx);
    rBanner.height = 24;
    const diffStr = calcDiffStr(ep.total, ep.prevTotal);
    const pctStr = calcPctStr(ep.total, ep.prevTotal);
    const bannerCell = ws.getCell(rowIdx, 1);
    bannerCell.value = `■ [${ep.name}] 현재 ${ep.total.toLocaleString()}건 (이전 대비 ${diffStr}, ${pctStr})  |  ${ep.focusSummary}`;
    bannerCell.font = fontBold;
    bannerCell.alignment = { vertical: "middle", horizontal: "left", indent: 1 };
    rowIdx++;

    // ★ [사용자 요청 완벽 반영] 각 부문 최상단에 배치된 대표 랭킹 차트(HiDPI 고해상도) 삽입
    let chartImg = null;
    if (ep.id === "quality") chartImg = qualityChartImg;
    else if (ep.id === "delivery") chartImg = deliveryChartImg;
    else if (ep.id === "service") chartImg = serviceChartImg;

    if (chartImg) {
      const mImgId = wb.addImage({
        base64: chartImg,
        extension: "png"
      });
      ws.addImage(mImgId, {
        tl: { col: 0, row: rowIdx - 1 },
        ext: { width: 800, height: 260 }
      });
      for (let r = 0; r < 13; r++) {
        ws.getRow(rowIdx + r).height = 20;
      }
      rowIdx += 13;
      rowIdx++; // Spacer
    }

    // 2) TOP 5 Header Row
    const topHeaders = ["순위", "주요 세부 클레임 유형", "현재 건수", "이전 대비 증감", "부문 내 비중", "비고 (특이사항)"];
    const rTopH = ws.getRow(rowIdx);
    rTopH.height = 22;
    for (let c = 1; c <= 6; c++) {
      const cell = ws.getCell(rowIdx, c);
      cell.value = topHeaders[c - 1];
      cell.font = { name: "맑은 고딕", size: 9, bold: true, color: { argb: "FF374151" } };
      cell.fill = fillTotal;
      cell.alignment = { vertical: "middle", horizontal: "center" };
      cell.border = borderThin;
    }
    rowIdx++;

    // 3) TOP 5 Data Rows
    const items = ep.items.length ? ep.items : [{ label: "선택 기간 접수 내역 없음", count: 0 }];
    items.forEach((it, idx) => {
      const row = ws.getRow(rowIdx);
      row.height = 20;

      const c1 = ws.getCell(rowIdx, 1);
      c1.value = ep.items.length ? idx + 1 : "-";
      c1.font = fontRegular;
      c1.alignment = { vertical: "middle", horizontal: "center" };
      c1.border = borderThin;

      const c2 = ws.getCell(rowIdx, 2);
      c2.value = it.label;
      c2.font = fontRegular;
      c2.alignment = { vertical: "middle", horizontal: "left", indent: 1 };
      c2.border = borderThin;

      const c3 = ws.getCell(rowIdx, 3);
      c3.value = it.count;
      c3.numFmt = "#,##0";
      c3.font = fontRegular;
      c3.alignment = { vertical: "middle", horizontal: "center" };
      c3.border = borderThin;

      const prvC = ep.prevMap ? (ep.prevMap[it.label] || 0) : null;
      let diffText = "-";
      let diffColor = "FF4B5563";
      if (prvC != null) {
        const d = it.count - prvC;
        if (d > 0) {
          const p = prvC > 0 ? ` (+${((d / prvC) * 100).toFixed(1)}%)` : " (신규)";
          diffText = `▲${d}${p}`;
          diffColor = "FFDC2626";
        } else if (d < 0) {
          const p = prvC > 0 ? ` (${((d / prvC) * 100).toFixed(1)}%)` : "";
          diffText = `▼${Math.abs(d)}${p}`;
          diffColor = "FF0F766E";
        } else {
          diffText = "- (0.0%)";
        }
      }

      const c4 = ws.getCell(rowIdx, 4);
      c4.value = diffText;
      c4.font = { name: "맑은 고딕", size: 9, bold: diffText !== "-", color: { argb: diffColor } };
      c4.alignment = { vertical: "middle", horizontal: "center" };
      c4.border = borderThin;

      const c5 = ws.getCell(rowIdx, 5);
      const pct = ep.total > 0 ? ((it.count / ep.total) * 100).toFixed(1) + "%" : "0.0%";
      c5.value = pct;
      c5.font = fontRegular;
      c5.alignment = { vertical: "middle", horizontal: "center" };
      c5.border = borderThin;

      const c6 = ws.getCell(rowIdx, 6);
      c6.value = idx === 0 && ep.total > 0 ? "최다 접수 유형 (집중 모니터링)" : "";
      c6.font = fontMuted;
      c6.alignment = { vertical: "middle", horizontal: "center" };
      c6.border = borderThin;

      rowIdx++;
    });

    // 4) Insight Comment Rows
    const memoList = ep.memos.length ? ep.memos : [{ tag: "자동 요약", at: "실시간", text: ep.defaultComment }];
    memoList.forEach((m) => {
      const row = ws.getRow(rowIdx);
      const text = `📌 [이슈 코멘트 & 액션 플랜] ${m.text || ""}`;
      const textLen = text.length;
      row.height = Math.max(26, Math.ceil(textLen / 60) * 18);

      ws.mergeCells(rowIdx, 1, rowIdx, 6);
      applyBox(rowIdx, 1, rowIdx, 6, fillZebra, borderThin);
      const cell = ws.getCell(rowIdx, 1);
      cell.value = text;
      cell.font = fontRegular;
      cell.alignment = { vertical: "middle", horizontal: "left", wrapText: true, indent: 1 };
      rowIdx++;
    });

    rowIdx++; // Spacer between pillars
  });

  // ==========================================
  // [4. 핵심 리스크 섹션: 기본 비노출 (사용자 요청 완벽 반영)]
  // 상세 원문 내역은 '품질raw' 시트에 모두 포함되어 있으므로, 
  // 리포트 종합 시트에서는 상세 테이블을 비노출하고 깔끔한 1줄 가이드 배너 제공 후 코멘트로 연결
  // ==========================================
  const validChatsForRisk = chats.filter((c) => c.valid);
  const qHighCheck = validChatsForRisk.filter((c) => c.nature === "클레임" && c.risk === "HIGH");
  if (qHighCheck.length > 0) {
    ws.mergeCells(rowIdx, 1, rowIdx, 6);
    applyBox(rowIdx, 1, rowIdx, 6,
      { type: "pattern", pattern: "solid", fgColor: { argb: "FFFFFBEB" } }, // Amber-50
      borderThin
    );
    const rGuide = ws.getRow(rowIdx);
    rGuide.height = 24;
    const cGuide = ws.getCell(rowIdx, 1);
    cGuide.value = `⚠️ [리스크 모니터링] 현재 고위험(HIGH) 클레임 ${qHighCheck.length}건이 감지되었습니다. 세부 원문 및 접수 내역은 '품질raw' 시트에서 상세 확인하실 수 있습니다.`;
    cGuide.font = { name: "맑은 고딕", size: 9, bold: true, color: { argb: "FFB45309" } };
    cGuide.alignment = { vertical: "middle", horizontal: "left", indent: 1 };
    rowIdx += 2;
  }

  // ==========================================
  // [4. CX팀 종합 코멘트]
  // ==========================================
  ws.getCell(rowIdx, 1).value = `4. CX팀 종합 코멘트 (대시보드 이슈 메모)`;
  ws.getCell(rowIdx, 1).font = fontSecHeader;
  ws.getRow(rowIdx).height = 24;
  rowIdx++;

  const allMemos = loadMemos();
  const memoList = (period && period.key && Array.isArray(allMemos[period.key])) ? allMemos[period.key] : [];

  const cxComments = memoList.length ? memoList : [{ text: "대시보드 '이슈 메모'에 작성된 추가 코멘트가 없습니다." }];
  cxComments.forEach((cm) => {
    const row = ws.getRow(rowIdx);
    const textLen = (cm.text || "").length;
    row.height = Math.max(26, Math.ceil(textLen / 55) * 18);

    ws.mergeCells(rowIdx, 1, rowIdx, 6);
    applyBox(rowIdx, 1, rowIdx, 6, fillZebra, borderThin);
    const cell = ws.getCell(rowIdx, 1);
    cell.value = cm.text || "";
    cell.font = fontRegular;
    cell.alignment = { vertical: "middle", horizontal: "left", wrapText: true, indent: 1 };
    rowIdx++;
  });

  rowIdx++; // Spacer

  // Footer Row
  const rFoot = ws.getRow(rowIdx);
  rFoot.height = 20;
  ws.mergeCells(rowIdx, 1, rowIdx, 6);
  const cFoot = ws.getCell(rowIdx, 1);
  cFoot.value = "베베숲 CX팀 주간 VOC 분석 시스템 · 채널톡 / 게시판 / CTI 전화 / 배송 DB 실시간 연동";
  cFoot.font = { name: "맑은 고딕", size: 8.5, color: { argb: "FF9CA3AF" } };
  cFoot.alignment = { vertical: "middle", horizontal: "center" };

  // ==========================================
  // [Sheet 2: 품질raw] (전체 노출 + 선택 기간 파스텔 음영)
  // ==========================================
  addQualityRawWorksheet(wb, period);

  // ==========================================
  // [Sheet 3: 보상내역서] (선택 기간 기준 제품별 보상 집계)
  // ==========================================
  addCompPeriodWorksheet(wb, period);

  // ==========================================
  // [Sheet 4: 보상내역서_전체] (연간 누적 주차/월 매트릭스)
  // ==========================================
  addCompFullMatrixWorksheet(wb, period);

  const buffer = await wb.xlsx.writeBuffer();
  const blob = new Blob([buffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  });
  const safePeriod = periodDisp.replace(/[\s\(\)\/\:\-]/g, "_");
  const fileName = `[CX팀]_VOC_분석종합리포트_${safePeriod}.xlsx`;

  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

function getOrSynthesizeQualityRaw() {
  if (E.getQualityRaw) {
    const list = E.getQualityRaw();
    if (list && list.length) return list;
  }
  if (window.VOC_DATA && Array.isArray(window.VOC_DATA.QUALITY_RAW) && window.VOC_DATA.QUALITY_RAW.length) {
    return window.VOC_DATA.QUALITY_RAW;
  }
  // 예비 폴백: WEEKS 루프에서 클레임 데이터 변환
  const results = [];
  if (Array.isArray(E.WEEKS)) {
    E.WEEKS.forEach((w) => {
      const chats = E.chatsForWeekKey(w.key).filter((c) => c && c.valid && c.nature === "클레임");
      chats.forEach((c) => {
        results.push({
          year: w.year || "2026",
          quarter: w.quarter || "4분기",
          month: w.month || "10월",
          week: w.label ? (w.label.match(/\d+주/) ? w.label.match(/\d+주/)[0] : "1주") : "1주",
          mw: formatPeriodDisplayLabel(w, "weekly"),
          id: c.id || "",
          cust: getChatCustomerName(c),
          date: w.week_start_date ? w.week_start_date.replace(/(\d{4})-(\d{2})-(\d{2})/, "$1년 $2월 $3일") : "",
          mgr: "CX팀",
          tagA: c.brand || "물티슈",
          tagB: c.mid || "",
          tagC: c.sub || "",
          prod: c.prod || "",
          mfg: c.mfg || "",
          issue: c.issue || "",
          qualitySend: isCompChat(c) ? "O" : "X",
          compMonth: "",
          compAll: "",
          mall: c.mall || "",
          orderNo: "",
          shipmentType: "",
          invoice: "",
          weekKey: w.key,
          rawDate: w.week_start_date || ""
        });
      });
    });
  }
  return results;
}

function addQualityRawWorksheet(wb, period) {
  const ws = wb.addWorksheet("품질raw", {
    views: [{ state: "frozen", ySplit: 1, showGridLines: true, activeCell: "A2" }]
  });

  const headers = [
    "연도", "분기", "MONTH", "WEEK", "M&W", "id", "고객명", "DATE", "담당자",
    "대분류", "중분류", "소분류", "제품명", "제조일자", "문의내용", "품질발송여부",
    "보상내역서(월)", "보상내역서_전체", "유통채널", "주문번호", "출고처", "송장번호"
  ];

  const colWidths = [
    { key: "year", width: 8 },
    { key: "quarter", width: 9 },
    { key: "month", width: 9 },
    { key: "week", width: 8 },
    { key: "mw", width: 12 },
    { key: "id", width: 22 },
    { key: "cust", width: 12 },
    { key: "date", width: 16 },
    { key: "mgr", width: 11 },
    { key: "tagA", width: 12 },
    { key: "tagB", width: 13 },
    { key: "tagC", width: 16 },
    { key: "prod", width: 34 },
    { key: "mfg", width: 22 },
    { key: "issue", width: 48 },
    { key: "qualitySend", width: 13 },
    { key: "compMonth", width: 15 },
    { key: "compAll", width: 15 },
    { key: "mall", width: 14 },
    { key: "orderNo", width: 18 },
    { key: "shipmentType", width: 12 },
    { key: "invoice", width: 16 }
  ];
  ws.columns = colWidths;
  ws.autoFilter = { from: "A1", to: "V1" };

  const fontHeader = { name: "맑은 고딕", size: 9.5, bold: true, color: { argb: "FFFFFFFF" } };
  const fillHeader = { type: "pattern", pattern: "solid", fgColor: { argb: "FF475569" } }; // Slate-600
  const borderThin = {
    top: { style: "thin", color: { argb: "FFD4D4D4" } },
    left: { style: "thin", color: { argb: "FFD4D4D4" } },
    bottom: { style: "thin", color: { argb: "FFD4D4D4" } },
    right: { style: "thin", color: { argb: "FFD4D4D4" } }
  };

  // Header row
  const rH = ws.getRow(1);
  rH.height = 25;
  headers.forEach((h, i) => {
    const c = ws.getCell(1, i + 1);
    c.value = h;
    c.font = fontHeader;
    c.fill = fillHeader;
    c.alignment = { vertical: "middle", horizontal: "center" };
    c.border = borderThin;
  });

  const rawRows = getOrSynthesizeQualityRaw();

  // 선택 기간 판별 기준
  const curPeriodDisp = formatPeriodDisplayLabel(period, E.state.mode);
  const curPeriodKey = period.key;
  const curWeekKeys = period.weekKeys || [curPeriodKey];
  const curStartDate = period.week_start_date;
  const curEndDate = period.week_end_date;

  // 파스텔 톤 음영 (예시 사진과 동일한 부드러운 살구/호박 파스텔 색상)
  const fillPastel = { type: "pattern", pattern: "solid", fgColor: { argb: "FFFFF3D6" } };
  const fontHighlight = { name: "맑은 고딕", size: 9, bold: true, color: { argb: "FF111827" } };
  const fontRegular = { name: "맑은 고딕", size: 9, color: { argb: "FF1F2937" } };

  // 선택 기간 데이터 및 직전 1달치 데이터 정렬 (당기 최상단+음영 -> 직전 1달 노출 -> 그 외 과거 숨김)
  const curPeriodIndex = Array.isArray(E.WEEKS) ? E.WEEKS.findIndex((w) => w.key === period.key) : -1;
  const monthWeeks = curPeriodIndex >= 0 ? E.WEEKS.slice(Math.max(0, curPeriodIndex - 4), curPeriodIndex) : [];
  const monthWeekKeys = monthWeeks.map((w) => w.key);

  const selectedRows = [];
  const monthRows = [];
  const otherRows = [];

  rawRows.forEach((r) => {
    let isSelected = false;
    let isMonth = false;
    if (r.weekKey && curWeekKeys.includes(r.weekKey)) {
      isSelected = true;
    } else if (r.mw && r.mw === curPeriodDisp) {
      isSelected = true;
    } else if (curStartDate && curEndDate && r.rawDate && r.rawDate >= curStartDate && r.rawDate <= curEndDate) {
      isSelected = true;
    } else if (r.weekKey && monthWeekKeys.includes(r.weekKey)) {
      isMonth = true;
    }

    if (isSelected) {
      selectedRows.push(r);
    } else if (isMonth) {
      monthRows.push(r);
    } else {
      otherRows.push(r);
    }
  });

  // 정렬 순서: 선택 기간 데이터(금주, 음영 O) -> 직전 1달 데이터(음영 X, 노출 O) -> 그 외 과거 데이터(숨김)
  const sortedRows = [
    ...selectedRows.map((r) => ({ ...r, isSelected: true, isMonth: false })),
    ...monthRows.map((r) => ({ ...r, isSelected: false, isMonth: true })),
    ...otherRows.map((r) => ({ ...r, isSelected: false, isMonth: false }))
  ];

  let curRowIdx = 2;
  sortedRows.forEach((r) => {
    const row = ws.getRow(curRowIdx);
    row.height = 20;

    // 선택 기간 + 직전 1달 데이터는 노출, 그 이전 과거 데이터만 숨김 처리
    if (!r.isSelected && !r.isMonth) {
      row.hidden = true;
    }

    const values = [
      r.year || "",
      r.quarter || "",
      r.month || "",
      r.week || "",
      r.mw || "",
      r.id || "",
      r.cust || "",
      r.date || "",
      r.mgr || "",
      r.tagA || "",
      r.tagB || "",
      r.tagC || "",
      r.prod || "",
      r.mfg || "",
      r.issue || "",
      r.qualitySend || "",
      r.compMonth || "",
      r.compAll || "",
      r.mall || "",
      r.orderNo || "",
      r.shipmentType || "",
      r.invoice || ""
    ];

    values.forEach((val, colIdx) => {
      const cell = ws.getCell(curRowIdx, colIdx + 1);
      cell.value = val;
      cell.font = r.isSelected ? fontHighlight : fontRegular;
      if (r.isSelected) {
        cell.fill = fillPastel;
      }
      cell.border = borderThin;

      // 좌측 정렬 컬럼: id(5), 제품명(12), 제조일자(13), 문의내용(14), 주문번호(19), 송장번호(21)
      const isLeft = [5, 12, 13, 14, 19, 21].includes(colIdx);
      cell.alignment = {
        vertical: "middle",
        horizontal: isLeft ? "left" : "center",
        indent: isLeft ? 1 : 0
      };
    });

    curRowIdx++;
  });
}

function addCompPeriodWorksheet(wb, period) {
  const ws = wb.addWorksheet("보상내역서", {
    views: [{ showGridLines: true }]
  });

  const periodName = formatPeriodDisplayLabel(period, E.state.mode);
  const dateRange = period.label;
  const targetChats = E.rawChats(period).filter(isCompChat);

  const famCounts = {};
  targetChats.forEach((c) => {
    const fam = getActualProductName(c.prod);
    famCounts[fam] = (famCounts[fam] || 0) + 1;
  });

  const sortedList = Object.entries(famCounts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "ko"));
  const totalCount = targetChats.length;

  ws.columns = [
    { key: "prod", width: 50 },
    { key: "count", width: 14 }
  ];

  ws.getRow(1).height = 14;

  // Title Banner
  ws.mergeCells("A2:B2");
  const r2 = ws.getRow(2);
  r2.height = 36;
  for (let c = 1; c <= 2; c++) {
    const cell = ws.getCell(2, c);
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFF2F2F2" } };
    cell.border = {
      top: { style: "thin", color: { argb: "FF000000" } },
      left: { style: "thin", color: { argb: "FF000000" } },
      bottom: { style: "double", color: { argb: "FF000000" } },
      right: { style: "thin", color: { argb: "FF000000" } }
    };
  }
  const tCell = ws.getCell("A2");
  tCell.value = "[CX팀] 품질 클레임 보상 내역";
  tCell.font = { name: "맑은 고딕", size: 15, bold: true, color: { argb: "FF000000" } };
  tCell.alignment = { vertical: "middle", horizontal: "center" };

  const cA4 = ws.getCell("A4");
  cA4.value = `● 데이터 추출기간 : ${dateRange}`;
  cA4.font = { name: "맑은 고딕", size: 10, color: { argb: "FF333333" } };
  cA4.alignment = { vertical: "middle", horizontal: "left" };

  const cA5 = ws.getCell("A5");
  cA5.value = `● 데이터 추출 기준 : 품질 클레임 (고객여정: 제품사용)`;
  cA5.font = { name: "맑은 고딕", size: 10, color: { argb: "FF333333" } };
  cA5.alignment = { vertical: "middle", horizontal: "left" };

  const cA6 = ws.getCell("A6");
  cA6.value = `보상내역서(${periodName})`;
  cA6.font = { name: "맑은 고딕", size: 11, bold: true, color: { argb: "FF111827" } };
  cA6.alignment = { vertical: "middle", horizontal: "left" };

  const hA = ws.getCell("A8");
  hA.value = "제품명";
  hA.alignment = { vertical: "middle", horizontal: "center" };

  const hB = ws.getCell("B8");
  hB.value = periodName;
  hB.alignment = { vertical: "middle", horizontal: "center" };

  [hA, hB].forEach((cell) => {
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF595959" } };
    cell.font = { name: "맑은 고딕", size: 10, bold: true, color: { argb: "FFFFFFFF" } };
    cell.border = {
      top: { style: "thin", color: { argb: "FF404040" } },
      left: { style: "thin", color: { argb: "FF404040" } },
      bottom: { style: "thin", color: { argb: "FF404040" } },
      right: { style: "thin", color: { argb: "FF404040" } }
    };
  });

  let curRow = 9;
  sortedList.forEach(([prodName, count]) => {
    const row = ws.getRow(curRow);
    row.height = 20;

    const c1 = ws.getCell(curRow, 1);
    c1.value = prodName;
    c1.font = { name: "맑은 고딕", size: 9.5, color: { argb: "FF1F2937" } };
    c1.alignment = { vertical: "middle", horizontal: "left", indent: 1 };
    c1.border = {
      top: { style: "thin", color: { argb: "FFD4D4D4" } },
      left: { style: "thin", color: { argb: "FFD4D4D4" } },
      bottom: { style: "thin", color: { argb: "FFD4D4D4" } },
      right: { style: "thin", color: { argb: "FFD4D4D4" } }
    };

    const c2 = ws.getCell(curRow, 2);
    c2.value = count;
    c2.numFmt = "#,##0";
    c2.font = { name: "맑은 고딕", size: 9.5, color: { argb: "FF1F2937" } };
    c2.alignment = { vertical: "middle", horizontal: "right" };
    c2.border = {
      top: { style: "thin", color: { argb: "FFD4D4D4" } },
      left: { style: "thin", color: { argb: "FFD4D4D4" } },
      bottom: { style: "thin", color: { argb: "FFD4D4D4" } },
      right: { style: "thin", color: { argb: "FFD4D4D4" } }
    };

    curRow++;
  });

  const fRow = ws.getRow(curRow);
  fRow.height = 24;

  const f1 = ws.getCell(curRow, 1);
  f1.value = "총합계";
  f1.font = { name: "맑은 고딕", size: 10, bold: true, color: { argb: "FF000000" } };
  f1.alignment = { vertical: "middle", horizontal: "center" };

  const f2 = ws.getCell(curRow, 2);
  f2.value = totalCount;
  f2.numFmt = "#,##0";
  f2.font = { name: "맑은 고딕", size: 10, bold: true, color: { argb: "FF000000" } };
  f2.alignment = { vertical: "middle", horizontal: "right" };

  [f1, f2].forEach((cell) => {
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFF9FAFB" } };
    cell.border = {
      top: { style: "thin", color: { argb: "FF000000" } },
      bottom: { style: "double", color: { argb: "FF000000" } },
      left: { style: "thin", color: { argb: "FFD4D4D4" } },
      right: { style: "thin", color: { argb: "FFD4D4D4" } }
    };
  });

  // Section 2: 보상 제외 내역 (수기 예외 관리)
  const rawTargetChats = E.rawChats(period).filter(isQualityClaimRaw);
  const curExSet = new Set((window.COMP_OVERRIDES?.excluded_ids || []).map(String));
  const excludedChats = rawTargetChats.filter((c) => curExSet.has(String(c.id)));

  curRow += 3;
  ws.getRow(curRow).height = 24;
  const s2Title = ws.getCell(curRow, 1);
  s2Title.value = `2. 보상 제외 내역 (수기 예외 관리 - 총 ${excludedChats.length}건)`;
  s2Title.font = { name: "맑은 고딕", size: 11, bold: true, color: { argb: "FF111827" } };

  curRow += 1;
  ws.getRow(curRow).height = 18;
  const s2Desc = ws.getCell(curRow, 1);
  s2Desc.value = "※ 단순 변심 교환, 고객 귀책 파손, 중복 접수, 정상 판정 등으로 보상 신청 목록에서 제외된 내역입니다.";
  s2Desc.font = { name: "맑은 고딕", size: 9, color: { argb: "FF6B7280" } };

  curRow += 2;
  const hRow = ws.getRow(curRow);
  hRow.height = 25;
  const exHeaders = ["대상 제품명", "고객명", "문의일자", "클레임 유형", "고객 불만 내용 원문", "보상 제외 사유"];
  exHeaders.forEach((htxt, idx) => {
    const c = ws.getCell(curRow, idx + 1);
    c.value = htxt;
    c.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF475569" } };
    c.font = { name: "맑은 고딕", size: 9.5, bold: true, color: { argb: "FFFFFFFF" } };
    c.alignment = { vertical: "middle", horizontal: "center" };
    c.border = {
      top: { style: "thin", color: { argb: "FF334155" } },
      left: { style: "thin", color: { argb: "FF334155" } },
      bottom: { style: "thin", color: { argb: "FF334155" } },
      right: { style: "thin", color: { argb: "FF334155" } }
    };
  });

  if (excludedChats.length > 0) {
    excludedChats.forEach((ex) => {
      curRow++;
      const row = ws.getRow(curRow);
      row.height = 22;
      const exReasonInfo = window.COMP_OVERRIDES?.excluded_reasons?.[String(ex.id)];
      const reasonText = exReasonInfo?.reason || "관리자 수기 제외";

      const vals = [
        getActualProductName(ex.prod),
        ex.cust || ex.name || "고객",
        ex.date || (ex.time ? ex.time.slice(0, 10) : "-"),
        ex.sub || ex.mid || "-",
        ex.issue || "-",
        reasonText
      ];

      vals.forEach((v, idx) => {
        const c = ws.getCell(curRow, idx + 1);
        c.value = v;
        c.font = { name: "맑은 고딕", size: 9.5, color: idx === 5 ? { argb: "FF9F1239" } : { argb: "FF1F2937" }, bold: idx === 1 || idx === 5 };
        c.alignment = { vertical: "middle", horizontal: (idx === 0 || idx === 4) ? "left" : "center" };
        if (idx === 5) {
          c.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFFFE4E6" } };
        }
        c.border = {
          top: { style: "thin", color: { argb: "FFD4D4D4" } },
          left: { style: "thin", color: { argb: "FFD4D4D4" } },
          bottom: { style: "thin", color: { argb: "FFD4D4D4" } },
          right: { style: "thin", color: { argb: "FFD4D4D4" } }
        };
      });
    });
  } else {
    curRow++;
    ws.getRow(curRow).height = 24;
    ws.mergeCells(curRow, 1, curRow, 6);
    const empC = ws.getCell(curRow, 1);
    empC.value = "※ 해당 기간 수기 보상 제외 내역 없음 (품질 클레임 전건 정상 보상 신청)";
    empC.font = { name: "맑은 고딕", size: 9.5, color: { argb: "FF4B5563" } };
    empC.alignment = { vertical: "middle", horizontal: "center" };
    empC.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFF1F5F9" } };
    for (let c = 1; c <= 6; c++) {
      ws.getCell(curRow, c).border = {
        top: { style: "thin", color: { argb: "FFD4D4D4" } },
        left: { style: "thin", color: { argb: "FFD4D4D4" } },
        bottom: { style: "thin", color: { argb: "FFD4D4D4" } },
        right: { style: "thin", color: { argb: "FFD4D4D4" } }
      };
    }
  }
}

function addCompFullMatrixWorksheet(wb, period) {
  const ws = wb.addWorksheet("보상내역서_전체", {
    views: [{ showGridLines: true }]
  });

  const list = E.getPeriodList();
  const year = period.key.slice(0, 4);
  const bucketList = getCompBucketList(period, year);

  const matrix = {};
  const bucketTotals = Array(bucketList.length).fill(0);
  let grandTotal = 0;

  bucketList.forEach((b, bIdx) => {
    b.chats.forEach((c) => {
      const fam = getActualProductName(c.prod);
      matrix[fam] = matrix[fam] || {};
      matrix[fam][b.key] = (matrix[fam][b.key] || 0) + 1;
      matrix[fam]["총합계"] = (matrix[fam]["총합계"] || 0) + 1;
      bucketTotals[bIdx]++;
      grandTotal++;
    });
  });

  const sortedList = Object.entries(matrix).sort((a, b) => (b[1]["총합계"] || 0) - (a[1]["총합계"] || 0) || a[0].localeCompare(b[0], "ko"));

  let dateRange = "";
  if (E.state.mode === "weekly") {
    const firstW = bucketList[0];
    const lastW = bucketList[bucketList.length - 1];
    const fObj = list.find((x) => x.key === firstW?.key);
    const lObj = list.find((x) => x.key === lastW?.key);
    if (fObj && fObj.week_start_date && lObj && lObj.week_end_date) {
      dateRange = `${fObj.week_start_date} ~ ${lObj.week_end_date}`;
    } else {
      dateRange = `${firstW?.label || ""} ~ ${lastW?.label || ""}`;
    }
  } else {
    dateRange = `${year}-01-01 ~ ${year}-12-31`;
  }

  const totalCols = 1 + bucketList.length + 1;

  ws.columns = [
    { key: "prod", width: 50 },
    ...bucketList.map((b, i) => ({ key: `b_${i}`, width: 11 })),
    { key: "total", width: 14 }
  ];

  ws.getRow(1).height = 14;

  // Title Banner
  ws.mergeCells(2, 1, 2, totalCols);
  const r2 = ws.getRow(2);
  r2.height = 36;
  for (let c = 1; c <= totalCols; c++) {
    const cell = ws.getCell(2, c);
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFF2F2F2" } };
    cell.border = {
      top: { style: "thin", color: { argb: "FF000000" } },
      left: { style: "thin", color: { argb: "FF000000" } },
      bottom: { style: "double", color: { argb: "FF000000" } },
      right: { style: "thin", color: { argb: "FF000000" } }
    };
  }
  const tCell = ws.getCell("A2");
  tCell.value = "[CX팀] 품질 클레임 보상 내역 (전체 누적 매트릭스)";
  tCell.font = { name: "맑은 고딕", size: 15, bold: true, color: { argb: "FF000000" } };
  tCell.alignment = { vertical: "middle", horizontal: "center" };

  const cA4 = ws.getCell("A4");
  cA4.value = `● 데이터 추출기간 : ${dateRange}`;
  cA4.font = { name: "맑은 고딕", size: 10, color: { argb: "FF333333" } };
  cA4.alignment = { vertical: "middle", horizontal: "left" };

  const cA5 = ws.getCell("A5");
  cA5.value = `● 데이터 추출 기준 : 품질 클레임 (고객여정: 제품사용)`;
  cA5.font = { name: "맑은 고딕", size: 10, color: { argb: "FF333333" } };
  cA5.alignment = { vertical: "middle", horizontal: "left" };

  const cA6 = ws.getCell("A6");
  cA6.value = `보상내역서_전체 (${year}년)`;
  cA6.font = { name: "맑은 고딕", size: 11, bold: true, color: { argb: "FF111827" } };
  cA6.alignment = { vertical: "middle", horizontal: "left" };

  const r8 = ws.getRow(8);
  r8.height = 26;
  const headerCells = [ws.getCell(8, 1)];
  ws.getCell(8, 1).value = "제품명";
  bucketList.forEach((b, i) => {
    const cell = ws.getCell(8, 2 + i);
    cell.value = b.label;
    headerCells.push(cell);
  });
  const lastCell = ws.getCell(8, totalCols);
  lastCell.value = "총합계";
  headerCells.push(lastCell);

  headerCells.forEach((cell) => {
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF595959" } };
    cell.font = { name: "맑은 고딕", size: 10, bold: true, color: { argb: "FFFFFFFF" } };
    cell.alignment = { vertical: "middle", horizontal: "center" };
    cell.border = {
      top: { style: "thin", color: { argb: "FF404040" } },
      left: { style: "thin", color: { argb: "FF404040" } },
      bottom: { style: "thin", color: { argb: "FF404040" } },
      right: { style: "thin", color: { argb: "FF404040" } }
    };
  });

  let curRow = 9;
  sortedList.forEach(([prodName, bucketMap]) => {
    const row = ws.getRow(curRow);
    row.height = 20;

    const c1 = ws.getCell(curRow, 1);
    c1.value = prodName;
    c1.font = { name: "맑은 고딕", size: 9.5, color: { argb: "FF1F2937" } };
    c1.alignment = { vertical: "middle", horizontal: "left", indent: 1 };
    c1.border = {
      top: { style: "thin", color: { argb: "FFD4D4D4" } },
      left: { style: "thin", color: { argb: "FFD4D4D4" } },
      bottom: { style: "thin", color: { argb: "FFD4D4D4" } },
      right: { style: "thin", color: { argb: "FFD4D4D4" } }
    };

    bucketList.forEach((b, i) => {
      const cell = ws.getCell(curRow, 2 + i);
      const val = bucketMap[b.key] || 0;
      cell.value = val;
      cell.numFmt = "#,##0";
      cell.font = { name: "맑은 고딕", size: 9.5, color: val > 0 ? { argb: "FF1F2937" } : { argb: "FF9CA3AF" } };
      cell.alignment = { vertical: "middle", horizontal: "right" };
      cell.border = {
        top: { style: "thin", color: { argb: "FFD4D4D4" } },
        left: { style: "thin", color: { argb: "FFD4D4D4" } },
        bottom: { style: "thin", color: { argb: "FFD4D4D4" } },
        right: { style: "thin", color: { argb: "FFD4D4D4" } }
      };
    });

    const cTot = ws.getCell(curRow, totalCols);
    cTot.value = bucketMap["총합계"] || 0;
    cTot.numFmt = "#,##0";
    cTot.font = { name: "맑은 고딕", size: 9.5, bold: true, color: { argb: "FF1F2937" } };
    cTot.alignment = { vertical: "middle", horizontal: "right" };
    cTot.border = {
      top: { style: "thin", color: { argb: "FFD4D4D4" } },
      left: { style: "thin", color: { argb: "FFD4D4D4" } },
      bottom: { style: "thin", color: { argb: "FFD4D4D4" } },
      right: { style: "thin", color: { argb: "FFD4D4D4" } }
    };

    curRow++;
  });

  const fRow = ws.getRow(curRow);
  fRow.height = 24;

  const f1 = ws.getCell(curRow, 1);
  f1.value = "총합계";
  f1.font = { name: "맑은 고딕", size: 10, bold: true, color: { argb: "FF000000" } };
  f1.alignment = { vertical: "middle", horizontal: "center" };

  bucketList.forEach((b, i) => {
    const cell = ws.getCell(curRow, 2 + i);
    cell.value = bucketTotals[i] || 0;
    cell.numFmt = "#,##0";
    cell.font = { name: "맑은 고딕", size: 10, bold: true, color: { argb: "FF000000" } };
    cell.alignment = { vertical: "middle", horizontal: "right" };
  });

  const fTot = ws.getCell(curRow, totalCols);
  fTot.value = grandTotal;
  fTot.numFmt = "#,##0";
  fTot.font = { name: "맑은 고딕", size: 10, bold: true, color: { argb: "FF000000" } };
  fTot.alignment = { vertical: "middle", horizontal: "right" };

    for (let c = 1; c <= totalCols; c++) {
    const cell = ws.getCell(curRow, c);
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFF9FAFB" } };
    cell.border = {
      top: { style: "thin", color: { argb: "FF000000" } },
      bottom: { style: "double", color: { argb: "FF000000" } },
      left: { style: "thin", color: { argb: "FFD4D4D4" } },
      right: { style: "thin", color: { argb: "FFD4D4D4" } }
    };
  }

  // Section 2: 연간 수기 보상 제외 내역 상세 리스트 전수
  const excludedReasons = window.COMP_OVERRIDES?.excluded_reasons || {};
  const allYearExcludedChats = [];
  const seenExcludedIds = new Set();

  bucketList.forEach((b) => {
    (b.rawChats || []).forEach((c) => {
      const cidStr = String(c.id);
      if (!isCompChat(c) && !seenExcludedIds.has(cidStr)) {
        seenExcludedIds.add(cidStr);
        allYearExcludedChats.push(c);
      }
    });
  });

  curRow += 3;
  ws.getRow(curRow).height = 24;
  const s2Title = ws.getCell(curRow, 1);
  s2Title.value = `2. ${year}년 연간 수기 보상 제외 내역 상세 리스트 (총 ${allYearExcludedChats.length}건)`;
  s2Title.font = { name: "맑은 고딕", size: 11, bold: true, color: { argb: "FF111827" } };

  curRow += 1;
  ws.getRow(curRow).height = 18;
  const s2Desc = ws.getCell(curRow, 1);
  s2Desc.value = "※ 연간 피벗 매트릭스에서 제외 처리된 건들의 상세 명단입니다. (단순 변심 교환, 고객 귀책 파손, 중복 접수, 정상 판정 등)";
  s2Desc.font = { name: "맑은 고딕", size: 9.5, color: { argb: "FF6B7280" } };

  curRow += 2;
  ws.getRow(curRow).height = 25;
  const exHeaders = ["대상 제품명", "고객명", "문의일자", "클레임 유형", "고객 불만 내용 원문", "보상 제외 사유"];
  exHeaders.forEach((h, idx) => {
    const cell = ws.getCell(curRow, idx + 1);
    cell.value = h;
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF475569" } };
    cell.font = { name: "맑은 고딕", size: 9.5, bold: true, color: { argb: "FFFFFFFF" } };
    cell.alignment = { vertical: "middle", horizontal: "center" };
    cell.border = {
      top: { style: "thin", color: { argb: "FF334155" } },
      left: { style: "thin", color: { argb: "FF334155" } },
      bottom: { style: "thin", color: { argb: "FF334155" } },
      right: { style: "thin", color: { argb: "FF334155" } }
    };
  });

  if (allYearExcludedChats.length > 0) {
    allYearExcludedChats.forEach((ex_r) => {
      curRow++;
      ws.getRow(curRow).height = 20;
      const cidStr = String(ex_r.id);
      const exInfo = excludedReasons[cidStr];
      const exReason = exInfo?.reason || "관리자 수기 제외";
      const exDate = ex_r.date || (ex_r.time ? ex_r.time.slice(0, 10) : "-");
      const cName = getChatCustomerName(ex_r);

      const rowVals = [
        getActualProductName(ex_r.prod),
        cName,
        exDate,
        ex_r.sub || ex_r.mid || "-",
        ex_r.issue || "-",
        exReason
      ];

      rowVals.forEach((v, idx) => {
        const cell = ws.getCell(curRow, idx + 1);
        cell.value = v;
        cell.font = { name: "맑은 고딕", size: 9, color: { argb: "FF1F2937" } };
        cell.border = {
          top: { style: "thin", color: { argb: "FFE5E7EB" } },
          left: { style: "thin", color: { argb: "FFE5E7EB" } },
          bottom: { style: "thin", color: { argb: "FFE5E7EB" } },
          right: { style: "thin", color: { argb: "FFE5E7EB" } }
        };
        if (idx === 0) cell.alignment = { vertical: "middle", horizontal: "left", indent: 1 };
        else if (idx === 4) cell.alignment = { vertical: "middle", horizontal: "left" };
        else if (idx === 5) {
          cell.alignment = { vertical: "middle", horizontal: "center" };
          cell.font = { name: "맑은 고딕", size: 9, bold: true, color: { argb: "FF9F1239" } };
          cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFFFE4E6" } };
        } else {
          cell.alignment = { vertical: "middle", horizontal: "center" };
        }
      });
    });
  } else {
    curRow++;
    ws.getRow(curRow).height = 24;
    ws.mergeCells(curRow, 1, curRow, 6);
    const emptyCell = ws.getCell(curRow, 1);
    emptyCell.value = `※ ${year}년 연간 수기 보상 제외 내역 없음 (품질 클레임 전건 정상 보상 신청)`;
    emptyCell.font = { name: "맑은 고딕", size: 9.5, color: { argb: "FF6B7280" } };
    emptyCell.alignment = { vertical: "middle", horizontal: "center" };
    emptyCell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFF9FAFB" } };
  }
}

let qualitySearchTerm = "";
let qualitySelectedTag = null;
let qualityCategoryFilter = "all";
let qualityViewLevel = "mid"; // "mid" (주요 유형별 - 기본값/권장) 또는 "sub" (세부 소분류별)

function isQualityClaim(c) {
  if (!c || !c.valid) return false;
  // 고객 여정(journey)이 '제품사용'인 건만 추출 (재통화 태그 제외 - 사용자 절대 기준)
  if (c.journey !== "제품사용") return false;
  if (c.sub === "재통화") return false;
  return true;
}

function matchQualityCategory(c, cat) {
  if (!cat || cat === "all") return true;
  const brand = c.brand || "";
  const tag = c.tag || "";
  const prod = c.prod || "";

  if (cat === "물티슈") {
    return brand === "물티슈" || tag.startsWith("물티슈") || /물티슈|시그니처|프리미어|네이처|아쿠아|센시|카밍|휴대|캡/i.test(prod);
  }
  if (cat === "스킨케어") {
    return brand === "스킨케어" || tag.startsWith("스킨케어") || /스킨케어|Z-SK|로션|크림|선스틱|선크림|바스|샴푸|수딩젤/i.test(prod);
  }
  if (cat === "홈") {
    return brand === "패밀리" || brand === "홈" || tag.startsWith("패밀리") || tag.startsWith("홈") || /Z-홈|세제|유연제|식기세척기|버그프리|주방세제|젖병/i.test(prod);
  }
  return true;
}

function renderQualityTypeTrendChart() {
  const el = document.getElementById("qualityTypeTrendChart");
  if (!el) return;
  destroyChart("qualityTypeTrendChart");

  const list = E.getPeriodList();
  const curPeriod = E.getPeriod();
  const pIdx = E.state.periodIndex;
  // 최근 4개 기간 가져오기 (주간/월간 모드)
  const recent = list.slice(Math.max(0, pIdx - 3), pIdx + 1);

  // 최근 4주간 발생한 품질 클레임 수집 (제품군 카테고리 필터 적용)
  const recentChatsByPeriod = recent.map((p) =>
    E.rawChats(p).filter((c) => isQualityClaim(c) && matchQualityCategory(c, qualityCategoryFilter))
  );
  const curChats = recentChatsByPeriod[recentChatsByPeriod.length - 1] || [];
  const prevChats = recentChatsByPeriod.length >= 2 ? recentChatsByPeriod[recentChatsByPeriod.length - 2] : [];

  // 0. Toggle 버튼 스타일 동기화 및 이벤트 바인딩
  const btnMid = document.getElementById("btnQualityViewMid");
  const btnSub = document.getElementById("btnQualityViewSub");
  if (btnMid && btnSub) {
    if (qualityViewLevel === "mid") {
      btnMid.className = "rounded-md px-2.5 py-1 text-zinc-900 bg-white font-bold shadow-xs transition cursor-pointer";
      btnSub.className = "rounded-md px-2.5 py-1 text-zinc-500 hover:text-zinc-800 font-medium transition cursor-pointer";
    } else {
      btnMid.className = "rounded-md px-2.5 py-1 text-zinc-500 hover:text-zinc-800 font-medium transition cursor-pointer";
      btnSub.className = "rounded-md px-2.5 py-1 text-zinc-900 bg-white font-bold shadow-xs transition cursor-pointer";
    }
    btnMid.onclick = () => {
      if (qualityViewLevel !== "mid") {
        qualityViewLevel = "mid";
        renderQualityTypeTrendChart();
      }
    };
    btnSub.onclick = () => {
      if (qualityViewLevel !== "sub") {
        qualityViewLevel = "sub";
        renderQualityTypeTrendChart();
      }
    };
  }

  let items = []; // { key, label, mid, curCount, prevCount }

  if (qualityViewLevel === "mid") {
    // [기본/권장] 주요 불만 유형(중분류)별 추이: 포장공정, 용액, 피부이상, 원단(공정)이물, 원단면, 이취 등
    const curMidCounts = Object.fromEntries(E.groupCount(curChats, "mid"));
    const prevMidCounts = Object.fromEntries(E.groupCount(prevChats, "mid"));
    const allRecentChats = recentChatsByPeriod.flat();
    const recentMidCounts = Object.fromEntries(E.groupCount(allRecentChats, "mid"));

    // 대표 중분류 순서 + 최근 4주 등장 중분류
    const baseMids = ["포장공정", "용액", "피부이상", "원단(공정)이물", "원단면", "이취"];
    const allMids = Array.from(new Set([...baseMids, ...Object.keys(recentMidCounts)]))
      .filter((m) => m && m !== "(미지정)" && (recentMidCounts[m] || 0) > 0);

    // ★ 핵심: 금주(선택 주차) 발생건수 내림차순 정렬 (가장 많이 발생한 유형을 맨 왼쪽에 배치!)
    allMids.sort((a, b) => {
      const diff = (curMidCounts[b] || 0) - (curMidCounts[a] || 0);
      if (diff !== 0) return diff;
      return (recentMidCounts[b] || 0) - (recentMidCounts[a] || 0);
    });

    items = allMids.map((mid) => ({
      key: mid,
      label: mid,
      mid: mid,
      curCount: curMidCounts[mid] || 0,
      prevCount: prevMidCounts[mid] || 0
    }));
  } else {
    // [세부 소분류별] 추이: 소분류도 금주 발생건수 내림차순 정렬
    const curSubCounts = Object.fromEntries(E.groupCount(curChats, "sub"));
    const prevSubCounts = Object.fromEntries(E.groupCount(prevChats, "sub"));
    const allRecentChats = recentChatsByPeriod.flat();
    const recentSubCounts = Object.fromEntries(E.groupCount(allRecentChats, "sub"));

    const subToMid = {};
    allRecentChats.forEach((c) => {
      if (c.sub && c.mid) subToMid[c.sub] = c.mid;
    });

    const allSubs = Object.keys(recentSubCounts).filter((s) => s && s !== "(미지정)" && recentSubCounts[s] > 0);

    // ★ 핵심: 금주 발생건수 내림차순 정렬 (가장 많이 발생한 소분류가 맨 왼쪽!)
    allSubs.sort((a, b) => {
      const diff = (curSubCounts[b] || 0) - (curSubCounts[a] || 0);
      if (diff !== 0) return diff;
      return (recentSubCounts[b] || 0) - (recentSubCounts[a] || 0);
    });

    items = allSubs.slice(0, 14).map((sub) => ({
      key: sub,
      label: sub,
      mid: subToMid[sub] || "",
      curCount: curSubCounts[sub] || 0,
      prevCount: prevSubCounts[sub] || 0
    }));
  }

  const labels = items.map((x) => x.label);
  const colors = ["#bae6fd", "#7dd3fc", "#38bdf8", "#0f766e"];

  const datasets = recent.map((p, pIndex) => {
    const isCur = p.key === curPeriod.key;
    const chats = recentChatsByPeriod[pIndex];
    const counts = qualityViewLevel === "mid"
      ? Object.fromEntries(E.groupCount(chats, "mid"))
      : Object.fromEntries(E.groupCount(chats, "sub"));

    const data = items.map((item) => counts[item.key] || 0);
    const periodShortLabel = formatPeriodDisplayLabel(p, E.state.mode);

    return {
      label: isCur ? `${periodShortLabel} (선택)` : periodShortLabel,
      data: data,
      backgroundColor: colors[pIndex % colors.length],
      hoverBackgroundColor: isCur ? "#115e59" : colors[pIndex % colors.length],
      borderRadius: 4,
      borderWidth: isCur ? 1.5 : 0,
      borderColor: isCur ? "#0d9488" : "transparent",
      barPercentage: 0.8,
      categoryPercentage: 0.75
    };
  });

  // 데이터 레이블 플러그인 (막대 상단 숫자 및 금주 증감 표시)
  const qualityTrendLabelsPlugin = {
    id: "qualityTrendLabels",
    afterDatasetsDraw(chart) {
      const ctx = chart.ctx;

      chart.data.datasets.forEach((dataset, datasetIndex) => {
        const meta = chart.getDatasetMeta(datasetIndex);
        if (!meta || !meta.visible) return;
        const isCurDataset = datasetIndex === chart.data.datasets.length - 1;

        meta.data.forEach((element, index) => {
          const val = dataset.data[index];
          if (!val || val <= 0) return;
          const str = Number(val).toLocaleString();

          ctx.save();
          ctx.font = isCurDataset
            ? "bold 11px -apple-system, BlinkMacSystemFont, sans-serif"
            : "9.5px -apple-system, BlinkMacSystemFont, sans-serif";
          ctx.textAlign = "center";
          ctx.textBaseline = "bottom";
          ctx.fillStyle = isCurDataset ? "#0f766e" : "#52525b";
          ctx.fillText(str, element.x, element.y - 2);

          // 선택 주차(맨 오른쪽 막대)인 경우 직전 주차 대비 증감 태그 표시
          if (isCurDataset && items[index]) {
            const curVal = items[index].curCount;
            const prevVal = items[index].prevCount;
            if (prevVal != null && curVal > 0) {
              const diff = curVal - prevVal;
              if (diff !== 0) {
                const diffStr = diff > 0 ? `▲+${diff}` : `▼${diff}`;
                ctx.font = "bold 9px sans-serif";
                ctx.fillStyle = diff > 0 ? "#b91c1c" : "#0d9488";
                ctx.fillText(diffStr, element.x, element.y - 14);
              }
            }
          }
          ctx.restore();
        });
      });
    }
  };

  charts["qualityTypeTrendChart"] = new Chart(el, {
    type: "bar",
    data: { labels, datasets },
    options: {
      layout: {
        padding: { top: 22, left: 6, right: 6, bottom: 4 }
      },
      plugins: {
        datalabels: { display: false },
        legend: {
          position: "top",
          labels: { font: { size: 11, weight: "500" }, boxWidth: 12, usePointStyle: true, pointStyle: "rectRounded" }
        },
        tooltip: {
          callbacks: {
            title: (tItems) => {
              if (!tItems.length) return "";
              const idx = tItems[0].dataIndex;
              const it = items[idx];
              if (!it) return "";
              return qualityViewLevel === "mid"
                ? `[불만 유형] ${it.label}`
                : `[${it.mid}] ${it.label} (소분류)`;
            },
            label: (item) => `${item.dataset.label}: ${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`,
            afterLabel: (item) => {
              const idx = item.dataIndex;
              const it = items[idx];
              if (it && it.curCount > 0 && it.prevCount != null) {
                const diff = it.curCount - it.prevCount;
                const sign = diff >= 0 ? "+" : "";
                return `(전주: ${it.prevCount}건 | 증감: ${sign}${diff}건)`;
              }
              return "";
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: true, color: "rgba(0,0,0,0.03)" },
          ticks: {
            font: { size: qualityViewLevel === "mid" ? 11 : 10, weight: "600" },
            maxRotation: qualityViewLevel === "mid" ? 0 : 45,
            minRotation: 0,
            autoSkip: false
          }
        },
        y: {
          beginAtZero: true,
          grace: "18%",
          grid: { color: "rgba(0,0,0,0.05)" },
          ticks: {
            font: { size: 10 },
            precision: 0,
            maxTicksLimit: 4,
            callback: (v) => Number(v).toLocaleString()
          }
        }
      },
      onClick: (_evt, els) => {
        if (els.length) {
          const idx = els[0].index;
          const clicked = items[idx]?.key;
          if (clicked) {
            qualitySelectedTag = (qualitySelectedTag === clicked) ? null : clicked;
            renderQuality();
          }
        }
      },
      responsive: true,
      maintainAspectRatio: false
    },
    plugins: [qualityTrendLabelsPlugin]
  });

  // 하단 요약/필터 바 렌더링
  const groupBar = document.getElementById("qualityCategoryGroupBar");
  if (groupBar) {
    if (qualityViewLevel === "mid") {
      groupBar.innerHTML = items.map((it) => {
        const isSel = qualitySelectedTag === it.key;
        const curBadge = it.curCount > 0 ? `<span class="ml-1 rounded px-1.5 py-0.2 text-[10px] font-bold ${isSel ? 'bg-white text-teal-800' : 'bg-teal-100 text-teal-800'}">${it.curCount}건</span>` : `<span class="ml-1 text-[10px] text-zinc-400">0건</span>`;
        return `<button type="button" data-key="${it.key}" class="quality-bar-btn inline-flex items-center justify-center rounded-lg px-2.5 py-1 text-xs font-semibold transition cursor-pointer ${isSel ? 'bg-teal-700 text-white shadow-xs' : 'bg-zinc-100 text-zinc-700 hover:bg-zinc-200'}">
          <span>${it.label}</span>
          ${curBadge}
        </button>`;
      }).join("");

      groupBar.querySelectorAll(".quality-bar-btn").forEach((btn) => {
        btn.onclick = () => {
          const k = btn.getAttribute("data-key");
          qualitySelectedTag = (qualitySelectedTag === k) ? null : k;
          renderQuality();
        };
      });
    } else {
      groupBar.innerHTML = `<div class="w-full text-center text-xs text-zinc-400 py-0.5">금주 발생건수 상위 소분류 노출 중 · 상단 '주요 유형별' 버튼을 누르면 중분류 총괄로 복귀합니다.</div>`;
    }
  }
}

function renderQuality() {
  const period = E.getPeriod();
  if (!period) return;
  const prev = E.prevPeriod();
  const allChats = E.rawChats(period).filter((c) => c.valid);
  const prevAllChats = prev ? E.rawChats(prev).filter((c) => c.valid) : [];

  // 품질 클레임 전수 수집 (물티슈, 스킨케어, 패밀리, 헬로, 홈 및 공통 제품 클레임)
  const baseQChats = allChats.filter(isQualityClaim);
  const prevBaseQChats = prevAllChats.filter(isQualityClaim);

  // 제품군 카테고리별 건수 배지 업데이트
  const countAll = baseQChats.length;
  const countWipes = baseQChats.filter((c) => matchQualityCategory(c, "물티슈")).length;
  const countSkin = baseQChats.filter((c) => matchQualityCategory(c, "스킨케어")).length;
  const countHome = baseQChats.filter((c) => matchQualityCategory(c, "홈")).length;

  const elAll = document.getElementById("catCountAll");
  if (elAll) elAll.textContent = countAll.toLocaleString();
  const elWipes = document.getElementById("catCountWipes");
  if (elWipes) elWipes.textContent = countWipes.toLocaleString();
  const elSkin = document.getElementById("catCountSkin");
  if (elSkin) elSkin.textContent = countSkin.toLocaleString();
  const elHome = document.getElementById("catCountHome");
  if (elHome) elHome.textContent = countHome.toLocaleString();

  // 제품군 카테고리 필터 적용
  const qChats = baseQChats.filter((c) => matchQualityCategory(c, qualityCategoryFilter));
  const prevQChats = prevBaseQChats.filter((c) => matchQualityCategory(c, qualityCategoryFilter));

  // 카테고리 버튼 UI 활성화 상태 동기화
  document.querySelectorAll(".quality-cat-btn").forEach((btn) => {
    const cat = btn.getAttribute("data-cat");
    if (cat === qualityCategoryFilter) {
      btn.className = "quality-cat-btn rounded-md px-3 py-1.5 text-zinc-900 bg-white shadow-xs font-bold ring-1 ring-black/5 transition cursor-pointer";
    } else {
      btn.className = "quality-cat-btn rounded-md px-3 py-1.5 text-zinc-500 hover:text-zinc-800 font-medium transition cursor-pointer";
    }
  });
  const catNotice = document.getElementById("qualityCatNotice");
  if (catNotice) {
    catNotice.textContent = qualityCategoryFilter === "all" ? "품질 클레임 전수 분석" : `[${qualityCategoryFilter}] 부문 집중 분석 중`;
  }

  const curTotal = qChats.length;
  const prevTotal = prevQChats.length;
  const pctOfAll = allChats.length > 0 ? ((curTotal / allChats.length) * 100).toFixed(1) : 0;
  const highCount = qChats.filter((c) => c.risk === "HIGH").length;

  // If a quality tag is selected, filter data for charts; otherwise use full qChats
  const chartChats = qualitySelectedTag ? qChats.filter((c) => c.sub === qualitySelectedTag || c.mid === qualitySelectedTag) : qChats;

  const prods = E.groupCount(chartChats, "prod").filter((x) => x[0] && x[0] !== "(미지정)");
  const top1Prod = prods.length ? `${prods[0][0]} (${Number(prods[0][1] || 0).toLocaleString()}건)` : "–";

  // 1. KPI Cards (dynamically reflects selected tag or overall claims)
  const kpiEl = document.getElementById("qualityKpiRow");
  if (kpiEl) {
    if (qualitySelectedTag) {
      const typeHigh = chartChats.filter((c) => c.risk === "HIGH").length;
      const typeShare = curTotal > 0 ? ((chartChats.length / curTotal) * 100).toFixed(1) : 0;
      kpiEl.innerHTML =
        kpiCard(`[${qualitySelectedTag}] 접수`, `${chartChats.length.toLocaleString()}건`, null, { subText: `전체 품질 접수의 ${typeShare}%` }) +
        kpiCard("선택 유형 점유율", `${typeShare}%`, null, { subText: `전체 ${curTotal.toLocaleString()}건 중` }) +
        kpiCard("고위험(HIGH) 건수", `${typeHigh.toLocaleString()}건`, null, { alert: typeHigh > 0 }) +
        kpiCard("해당 유형 최다 제품", top1Prod, null);
    } else {
      kpiEl.innerHTML =
        kpiCard("품질 클레임 총 접수", `${curTotal.toLocaleString()}건`, E.delta(curTotal, prevTotal), { inverse: true }) +
        kpiCard("전체 VOC 중 비중", `${pctOfAll}%`, null) +
        kpiCard("고위험(HIGH) 클레임", `${highCount.toLocaleString()}건`, null, { alert: highCount > 5 }) +
        kpiCard("최다 접수 제품", top1Prod, null);
    }
  }

  // 1.1 불만유형 필터 적용 시 안내 배너
  const noticeEl = document.getElementById("qualityActiveFilterNotice");
  if (noticeEl) {
    if (qualitySelectedTag) {
      noticeEl.hidden = false;
      noticeEl.innerHTML = `
        <div class="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-teal-50 px-4 py-2.5 ring-1 ring-teal-600/30">
          <div class="flex items-center gap-2">
            <span class="inline-block w-2 h-2 rounded-full bg-teal-600 animate-pulse"></span>
            <span class="text-xs font-semibold text-teal-900">
              불만 유형 필터 연동 중: <span class="rounded bg-teal-600 px-2 py-0.5 text-white font-bold text-xs">${qualitySelectedTag}</span> (${chartChats.length.toLocaleString()}건)
            </span>
            <span class="text-xs text-teal-700 hidden sm:inline">· 제품별 순위, 구매처, 제조일자/Lot, 상세 내역이 모두 '${qualitySelectedTag}' 기준으로 연동되었습니다.</span>
          </div>
          <button id="btnResetQualityFilter" type="button" class="inline-flex items-center gap-1 rounded-lg bg-white px-2.5 py-1 text-xs font-semibold text-teal-800 ring-1 ring-black/10 hover:bg-zinc-50 shadow-sm transition">
            <span>✕ 전체 품질 불만으로 복귀</span>
          </button>
        </div>
      `;
      document.getElementById("btnResetQualityFilter")?.addEventListener("click", () => {
        qualitySelectedTag = null;
        renderQuality();
      });
    } else {
      noticeEl.hidden = true;
      noticeEl.innerHTML = "";
    }
  }

  // 1.5 [신규] 품질 불만 유형별 다주차 인입 추이 막대 그래프 렌더링
  renderQualityTypeTrendChart();

  // Update subtitles
  const prodSub = document.getElementById("qualityProductSubtitle");
  if (prodSub) prodSub.textContent = qualitySelectedTag ? `'${qualitySelectedTag}' 발생 제품 순위 (${chartChats.length.toLocaleString()}건)` : "선택 기간 접수 건수";
  const mallSub = document.getElementById("qualityMallSubtitle");
  if (mallSub) mallSub.textContent = qualitySelectedTag ? `'${qualitySelectedTag}' 접수 구매처 비중` : "자사몰, 스마트스토어, 쿠팡 등";
  const mfgSub = document.getElementById("qualityMfgSubtitle");
  if (mfgSub) mfgSub.textContent = qualitySelectedTag ? `'${qualitySelectedTag}' 발생 Lot 집중 감지` : "특정 로트 불만 집중 감지";

  // 2. 제품별 접수 랭킹 Top 10 (Bar Chart) - 연동 반영
  const top10Prods = prods.slice(0, 10);
  barChart("qualityProductChart", top10Prods.map((x) => x[0]), top10Prods.map((x) => x[1]), {
    horizontal: true,
    colors: qualitySelectedTag ? "#0d9488" : "#0f766e"
  });

  // 3. 구매처(유통채널)별 품질 접수 현황 (Doughnut Chart) - 연동 반영
  const malls = E.groupCount(chartChats, "mall").filter((x) => x[0] && x[0] !== "(미지정)").slice(0, 6);
  doughnutChart("qualityMallChart", malls.map((x) => x[0]), malls.map((x) => x[1]));

  // 4. 품질 불만 소분류별 증감 피벗 테이블 (전체 목록 유지로 자유로운 전환 보장)
  const curTagMap = Object.fromEntries(E.groupCount(qChats, "sub"));
  const prevTagMap = Object.fromEntries(E.groupCount(prevQChats, "sub"));
  const allSubTags = Array.from(new Set([...Object.keys(curTagMap), ...Object.keys(prevTagMap)]))
    .filter((s) => s && s !== "(미지정)")
    .sort((a, b) => (curTagMap[b] || 0) - (curTagMap[a] || 0));

  const tableBody = document.getElementById("qualityTagTableBody");
  if (tableBody) {
    tableBody.innerHTML = allSubTags.map((sub) => {
      const cCnt = curTagMap[sub] || 0;
      const pCnt = prevTagMap[sub] || 0;
      const diff = cCnt - pCnt;
      const share = curTotal > 0 ? ((cCnt / curTotal) * 100).toFixed(1) : 0;
      let diffBadge = "–";
      if (diff > 0) diffBadge = `<span class="tnum text-red-600 font-semibold">▲ ${diff.toLocaleString()}</span>`;
      else if (diff < 0) diffBadge = `<span class="tnum text-teal-700 font-semibold">▼ ${Math.abs(diff).toLocaleString()}</span>`;

      const isSelected = qualitySelectedTag === sub;
      const rowClass = isSelected
        ? "bg-teal-50 ring-2 ring-inset ring-teal-600 font-semibold cursor-pointer transition shadow-sm"
        : "hover:bg-zinc-100/80 cursor-pointer transition";

      return `<tr class="${rowClass}" data-sub="${sub}">
        <td class="py-2 px-3 font-medium text-zinc-900 flex items-center justify-between">
          <span class="truncate">${sub}</span>
          ${isSelected ? '<span class="ml-1.5 shrink-0 rounded bg-teal-600 px-1.5 py-0.5 text-[10px] font-semibold text-white">필터 중 ✓</span>' : '<span class="ml-1.5 shrink-0 text-[10px] text-zinc-400">클릭 상세</span>'}
        </td>
        <td class="py-2 px-2 text-right tnum text-zinc-500">${pCnt.toLocaleString()}</td>
        <td class="py-2 px-2 text-right tnum font-semibold text-zinc-900">${cCnt.toLocaleString()}</td>
        <td class="py-2 px-2 text-right">${diffBadge}</td>
        <td class="py-2 px-2 text-right tnum text-zinc-500">${share}%</td>
      </tr>`;
    }).join("") || `<tr><td colspan="5" class="py-4 text-center text-zinc-400">품질 클레임 접수 내역이 없습니다.</td></tr>`;

    tableBody.querySelectorAll("tr[data-sub]").forEach((row) => {
      row.addEventListener("click", () => {
        const sub = row.getAttribute("data-sub");
        qualitySelectedTag = (qualitySelectedTag === sub) ? null : sub;
        renderQuality();
      });
    });
  }

  // Update qualityFilterBadgeContainer
  const badgeContainer = document.getElementById("qualityFilterBadgeContainer");
  if (badgeContainer) {
    if (qualitySelectedTag) {
      badgeContainer.innerHTML = `
        <span class="inline-flex items-center gap-1.5 rounded-full bg-teal-100 px-2.5 py-0.5 text-xs font-semibold text-teal-800 shadow-sm">
          <span>불만유형: <strong>${qualitySelectedTag}</strong></span>
          <button id="clearQualityTagFilter" type="button" class="ml-1 rounded-full p-0.5 text-teal-700 hover:bg-teal-200 hover:text-teal-950 transition" title="필터 해제">✕</button>
        </span>
      `;
      const clearBtn = document.getElementById("clearQualityTagFilter");
      if (clearBtn) {
        clearBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          qualitySelectedTag = null;
          renderQuality();
        });
      }
    } else {
      badgeContainer.innerHTML = "";
    }
  }

  // 5. 제조일자 / Lot별 불만 인입 건수 (Bar Chart) - YYYYMMDD 통합 집계 적용
  const mfgMapped = chartChats
    .filter((c) => c.mfg && c.mfg.trim())
    .map((c) => ({ ...c, mfgFormatted: formatMfgDate(c.mfg) }));
  const mfgs = E.groupCount(mfgMapped.filter((c) => c.mfgFormatted && c.mfgFormatted.length >= 4), "mfgFormatted").slice(0, 10);

  // 세련된 로열 인디고 그라데이션 컬러 팔레트 (최다 접수 Lot 시각적 강조)
  const mfgColors = mfgs.map((_, idx) => {
    if (idx === 0) return "#4338ca"; // 1위 Lot: Deep Royal Indigo
    if (idx < 3) return "#6366f1";  // 2~3위: Vibrant Indigo
    if (idx < 6) return "#818cf8";  // 4~6위: Soft Indigo
    return "#a5b4fc";               // 7위 이하: Light Indigo
  });

  barChart("qualityMfgChart", mfgs.map((x) => x[0]), mfgs.map((x) => x[1]), {
    horizontal: false,
    colors: mfgColors
  });

  // 6. 품질 클레임 실시간 접수 상세 테이블 - 연동 반영
  renderQualityDetailTable(chartChats);

  // 7. 품질 이슈 & 인사이트 메모 및 데이터 스냅샷 렌더링
  renderCategoryInsights("quality");
  initCategoryInsightHandlers("quality");

  // 8. 주차별 클레임 실물 사진 갤러리 렌더링
  renderClaimPhotos(period);
}

let curClaimPhotos = [];
let curModalPhotoIdx = -1;
let claimPhotoDisplayLimit = 30;

function renderClaimPhotoCards() {
  const gridEl = document.getElementById("claimPhotoGrid");
  if (!gridEl) return;
  const visiblePhotos = curClaimPhotos.slice(0, claimPhotoDisplayLimit);

  const cardsHtml = visiblePhotos.map((p, idx) => {
    const parts = (p.label || "").split("_");
    let causeBadge = "";
    if (parts.length >= 3) {
      causeBadge = `<span class="inline-block mt-0.5 px-1 py-0.2 rounded text-[9.5px] font-semibold bg-amber-50 text-amber-800 border border-amber-200 truncate max-w-full">${parts.slice(2).join("_")}</span>`;
    } else if (parts.length === 2) {
      causeBadge = `<span class="inline-block mt-0.5 px-1 py-0.2 rounded text-[9.5px] font-medium bg-zinc-100 text-zinc-600 truncate max-w-full">${parts[1]}</span>`;
    }

    const folderTag = p.folder ? `<span class="text-[9px] text-zinc-400 truncate block mt-0.5" title="${p.folder}">${p.folder}</span>` : "";

    return `
      <div class="group relative rounded-lg border border-zinc-200/90 bg-white p-1.5 shadow-xs hover:shadow-md hover:border-teal-500/50 transition cursor-pointer flex flex-col justify-between" onclick="window.VOC_RENDER.openClaimPhotoModal(${idx})">
        <div class="aspect-square w-full overflow-hidden rounded bg-zinc-100 flex items-center justify-center relative">
          <img src="${p.thumb_url || p.url}" alt="${p.label}" loading="lazy" class="h-full w-full object-cover group-hover:scale-105 transition duration-300">
          <div class="absolute inset-0 bg-black/0 group-hover:bg-black/25 transition flex items-center justify-center">
            <span class="opacity-0 group-hover:opacity-100 transition px-1.5 py-0.5 rounded bg-black/75 text-white text-[10px] font-medium">🔍 확대</span>
          </div>
        </div>
        <div class="mt-1 text-center px-0.5">
          <p class="text-[11px] font-semibold text-zinc-800 truncate" title="${p.label}">${p.label}</p>
          ${causeBadge}
          ${folderTag}
        </div>
      </div>
    `;
  }).join("");

  let moreButtonHtml = "";
  if (curClaimPhotos.length > claimPhotoDisplayLimit) {
    const remaining = curClaimPhotos.length - claimPhotoDisplayLimit;
    const nextBatch = Math.min(30, remaining);
    moreButtonHtml = `
      <div class="col-span-full py-4 flex items-center justify-center">
        <button type="button" onclick="window.VOC_RENDER.loadMoreClaimPhotos()" class="px-5 py-2 text-xs font-semibold text-teal-700 bg-teal-50 hover:bg-teal-100 border border-teal-200 rounded-lg shadow-xs transition flex items-center gap-1.5 cursor-pointer">
          <span>사진 더보기 (+${nextBatch}건)</span>
          <span class="text-[11px] font-normal text-teal-600">(${claimPhotoDisplayLimit} / ${curClaimPhotos.length}건)</span>
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
        </button>
      </div>
    `;
  }

  gridEl.innerHTML = cardsHtml + moreButtonHtml;
}

function loadMoreClaimPhotos() {
  claimPhotoDisplayLimit += 30;
  renderClaimPhotoCards();
}

async function renderClaimPhotos(period) {
  const gridEl = document.getElementById("claimPhotoGrid");
  const tagEl = document.getElementById("claimPhotoPeriodTag");
  const badgeEl = document.getElementById("claimPhotoCountBadge");
  if (!gridEl) return;

  const periodName = formatPeriodDisplayLabel(period, E.state.mode);
  if (tagEl) tagEl.textContent = periodName;

  gridEl.innerHTML = `<div class="col-span-full py-6 text-center text-xs text-zinc-400">클레임 실물 사진을 불러오는 중입니다...</div>`;

  try {
    claimPhotoDisplayLimit = 30;
    const res = await fetch(`/api/claim_photos?week=${encodeURIComponent(period.key)}`);
    if (!res.ok) throw new Error("API response error");
    const data = await res.json();
    const photos = data.photos || [];
    curClaimPhotos = photos;

    if (badgeEl) {
      badgeEl.textContent = photos.length > 0 ? `${photos.length}건 등록` : "사진 없음";
      badgeEl.className = photos.length > 0
        ? "rounded bg-teal-100 px-2 py-0.5 text-[11px] font-semibold text-teal-800"
        : "rounded bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-500";
    }

    if (!photos.length) {
      gridEl.innerHTML = `
        <div class="col-span-full py-8 text-center text-xs text-zinc-400 bg-zinc-50/70 rounded-xl border border-dashed border-zinc-200">
          <p class="font-medium text-zinc-500">${periodName}에 등록된 클레임 사진이 없습니다.</p>
          <p class="mt-1 text-[11px] text-zinc-400">(X 드라이브 연동: X:\\9. 클레임 사진\\2026)</p>
        </div>
      `;
      return;
    }

    renderClaimPhotoCards();
  } catch (err) {
    console.warn("Failed to load claim photos:", err);
    if (badgeEl) badgeEl.textContent = "연동 대기";
    gridEl.innerHTML = `
      <div class="col-span-full py-6 text-center text-xs text-zinc-400 bg-zinc-50 rounded-xl">
        클레임 사진 정보를 불러오지 못했습니다.
      </div>
    `;
  }
}

function openClaimPhotoModal(idx) {
  const photo = curClaimPhotos[idx];
  if (!photo) return;
  curModalPhotoIdx = idx;
  const modal = document.getElementById("claimPhotoModal");
  const title = document.getElementById("claimPhotoModalTitle");
  const img = document.getElementById("claimPhotoModalImg");
  if (!modal || !img) return;

  const fldText = photo.folder ? ` [${photo.folder}]` : "";
  if (title) title.textContent = `[클레임 사진] ${photo.label}${fldText} (${idx + 1} / ${curClaimPhotos.length})`;
  img.src = photo.url;
  modal.classList.remove("hidden");
}

function prevClaimPhotoModal() {
  if (curModalPhotoIdx > 0) {
    openClaimPhotoModal(curModalPhotoIdx - 1);
  }
}

function nextClaimPhotoModal() {
  if (curModalPhotoIdx >= 0 && curModalPhotoIdx < curClaimPhotos.length - 1) {
    openClaimPhotoModal(curModalPhotoIdx + 1);
  }
}

function closeClaimPhotoModal() {
  const modal = document.getElementById("claimPhotoModal");
  if (modal) modal.classList.add("hidden");
}

function renderQualityDetailTable(qChats) {
  const tbody = document.getElementById("qualityDetailTableBody");
  if (!tbody) return;
  const term = (qualitySearchTerm || "").trim().toLowerCase();
  const filtered = qChats.filter((c) => {
    if (qualitySelectedTag && c.sub !== qualitySelectedTag) return false;
    if (!term) return true;
    const custName = getChatCustomerName(c);
    return (
      (custName || "").toLowerCase().includes(term) ||
      (c.prod || "").toLowerCase().includes(term) ||
      (c.sub || "").toLowerCase().includes(term) ||
      (c.issue || "").toLowerCase().includes(term) ||
      (c.act || "").toLowerCase().includes(term) ||
      (c.mall || "").toLowerCase().includes(term) ||
      (c.mfg || "").toLowerCase().includes(term)
    );
  });

  if (!filtered.length) {
    const emptyMsg = qualitySelectedTag
      ? `선택된 불만 유형 [${qualitySelectedTag}]에 해당하는 접수 내역이 없습니다.`
      : "검색 조건에 맞는 품질 클레임 건이 없습니다.";
    tbody.innerHTML = `<tr><td colspan="9" class="py-6 text-center text-zinc-400">${emptyMsg}</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.slice(0, 60).map((c) => {
    const riskBadge =
      c.risk === "HIGH"
        ? '<span class="rounded bg-red-600 px-1.5 py-0.5 text-[10px] font-semibold text-white">HIGH</span>'
        : c.risk === "MEDIUM"
        ? '<span class="rounded bg-amber-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">MED</span>'
        : '<span class="rounded bg-zinc-200 px-1.5 py-0.5 text-[10px] font-medium text-zinc-700">LOW</span>';

    const custName = getChatCustomerName(c);
    const dateStr = c.date || (c.time ? c.time.slice(0, 10) : "–");

    return `<tr class="hover:bg-zinc-50">
      <td class="py-2.5 px-2">${riskBadge}</td>
      <td class="py-2.5 px-2 tnum text-zinc-600 whitespace-nowrap">${dateStr}</td>
      <td class="py-2.5 px-2 font-medium text-zinc-700">${c.mid || ""} / ${c.sub || ""}</td>
      <td class="py-2.5 px-3 font-medium text-zinc-900">${c.prod || "–"}</td>
      <td class="py-2.5 px-2 font-medium text-zinc-900 whitespace-nowrap">${custName}</td>
      <td class="py-2.5 px-2 tnum text-zinc-500">${formatMfgDate(c.mfg)}</td>
      <td class="py-2.5 px-2 text-zinc-600">${c.mall || "–"}</td>
      <td class="py-2.5 px-4 text-zinc-800 break-words max-w-xs">${(c.issue || "–").replace(/</g, "&lt;")}</td>
      <td class="py-2.5 px-4 text-zinc-600 break-words max-w-xs">${(c.act || "–").replace(/</g, "&lt;")}</td>
    </tr>`;
  }).join("");
}

const CAT_INSIGHT_KEY = "voc_cat_insights_v2";

function loadCatInsights() {
  try {
    const data = JSON.parse(localStorage.getItem(CAT_INSIGHT_KEY)) || {};
    // Legacy migration if any
    const legacy = JSON.parse(localStorage.getItem("voc_quality_insights_v1")) || {};
    let migrated = false;
    for (const [k, list] of Object.entries(legacy)) {
      if (Array.isArray(list) && list.length) {
        if (!data[k]) data[k] = {};
        if (!data[k].quality) data[k].quality = [];
        list.forEach((item) => {
          if (!data[k].quality.some((existing) => existing.id === item.id)) {
            data[k].quality.push({
              id: item.id || "qi_" + Math.random().toString(36).slice(2),
              category: "quality",
              tag: item.tag || "전체",
              at: item.at || "",
              text: item.text || "",
              snapshot: {
                periodLabel: k,
                filterLabel: item.tag ? `불만: ${item.tag}` : "전체 품질",
                bullets: ["기존 데이터 마이그레이션"]
              }
            });
            migrated = true;
          }
        });
      }
    }
    if (migrated) {
      localStorage.setItem(CAT_INSIGHT_KEY, JSON.stringify(data));
    }
    return data;
  } catch (err) {
    console.error("loadCatInsights error:", err);
    return {};
  }
}

function saveCatInsights(data) {
  try {
    localStorage.setItem(CAT_INSIGHT_KEY, JSON.stringify(data));
  } catch (err) {
    console.error("saveCatInsights error:", err);
  }
}

// Fallback compatibility functions
function loadQualityInsights() {
  const all = loadCatInsights();
  const res = {};
  for (const [k, v] of Object.entries(all)) {
    if (v && v.quality) res[k] = v.quality;
  }
  return res;
}

function saveQualityInsights(data) {
  const all = loadCatInsights();
  for (const [k, v] of Object.entries(data)) {
    if (!all[k]) all[k] = {};
    all[k].quality = v;
  }
  saveCatInsights(all);
}

function buildCategorySnapshot(category) {
  const period = E.getPeriod();
  const prevP = E.prevPeriod();

  if (category === "quality") {
    const allChats = E.rawChats(period).filter((c) => c.valid);
    const prevChats = prevP ? E.rawChats(prevP).filter((c) => c.valid) : [];
    const qChats = allChats.filter(
      (c) => c.nature === "클레임" && ["물티슈", "스킨케어", "패밀리", "헬로", "홈"].includes(c.brand) && c.mid !== "배송"
    );
    const prevQ = prevChats.filter(
      (c) => c.nature === "클레임" && ["물티슈", "스킨케어", "패밀리", "헬로", "홈"].includes(c.brand) && c.mid !== "배송"
    );
    const targetChats = qualitySelectedTag ? qChats.filter((c) => c.sub === qualitySelectedTag) : qChats;
    const prevTarget = qualitySelectedTag ? prevQ.filter((c) => c.sub === qualitySelectedTag) : prevQ;

    const curCnt = targetChats.length;
    const prevCnt = prevTarget.length;
    const diff = curCnt - prevCnt;
    const diffText = diff > 0 ? `▲ ${diff.toLocaleString()}건 증가` : (diff < 0 ? `▼ ${Math.abs(diff).toLocaleString()}건 감소` : "전기 대비 변동 없음 (0건)");

    // Top types
    const typeCounts = E.groupCount(targetChats, "sub").slice(0, 3);
    const topTypesText = typeCounts.map(([name, cnt]) => `${name} (${Number(cnt || 0).toLocaleString()}건)`).join(", ") || "내역 없음";

    // Top products
    const prodCounts = E.groupCount(targetChats, "prod").slice(0, 2);
    const topProdsText = prodCounts.map(([name, cnt]) => `${name} (${Number(cnt || 0).toLocaleString()}건)`).join(", ") || "내역 없음";

    // Top Lot / Mfg
    const mfgMapped = targetChats.filter((c) => c.mfg && c.mfg.trim()).map((c) => ({ ...c, mfgFormatted: formatMfgDate(c.mfg) }));
    const mfgCounts = E.groupCount(mfgMapped.filter((c) => c.mfgFormatted && c.mfgFormatted.length >= 4), "mfgFormatted").slice(0, 1);
    const topMfgText = mfgCounts.length ? `${mfgCounts[0][0]} (${Number(mfgCounts[0][1] || 0).toLocaleString()}건)` : "–";

    return {
      periodLabel: period.label,
      filterLabel: qualitySelectedTag ? `불만: ${qualitySelectedTag}` : "전체 품질",
      curCount: curCnt,
      diffText: diffText,
      bullets: [
        `접수 규모: 총 ${curCnt.toLocaleString()}건 (${diffText})`,
        `주요 불만 유형: ${topTypesText}`,
        `최다 인입 제품: ${topProdsText}`,
        `최다 발생 제조일/Lot: ${topMfgText}`
      ]
    };
  } else if (category === "delivery") {
    const curShipments = E.rawShipments(period);
    const prevShipments = prevP ? E.rawShipments(prevP) : [];
    const vFilter = deliveryVendorFilterVal || "all";
    const targetShipments = vFilter === "all" ? curShipments : curShipments.filter((s) => s.vendor === vFilter);
    const prevTarget = vFilter === "all" ? prevShipments : prevShipments.filter((s) => s.vendor === vFilter);

    const curCnt = targetShipments.length;
    const prevCnt = prevTarget.length;
    const diff = curCnt - prevCnt;
    const diffText = diff > 0 ? `▲ ${diff.toLocaleString()}건 증가` : (diff < 0 ? `▼ ${Math.abs(diff).toLocaleString()}건 감소` : "전기 대비 변동 없음 (0건)");

    const curCold = targetShipments.filter((s) => s.vendor === "초저온").length;
    const curFul = targetShipments.filter((s) => s.vendor === "풀필먼트").length;
    const coldPct = curCnt > 0 ? ((curCold / curCnt) * 100).toFixed(0) : 0;
    const fulPct = curCnt > 0 ? ((curFul / curCnt) * 100).toFixed(0) : 0;

    const typeCounts = E.groupCount(targetShipments, "type").slice(0, 3);
    const topTypesText = typeCounts.map(([name, cnt]) => `${name} (${Number(cnt || 0).toLocaleString()}건)`).join(", ") || "내역 없음";

    return {
      periodLabel: period.label,
      filterLabel: vFilter === "all" ? "전체 벤더" : `벤더: ${vFilter}`,
      curCount: curCnt,
      diffText: diffText,
      bullets: [
        `접수 규모: 총 ${curCnt.toLocaleString()}건 (${diffText})`,
        `벤더별 비중: 초저온(CJ) ${curCold.toLocaleString()}건 (${coldPct}%) / 풀필먼트 ${curFul.toLocaleString()}건 (${fulPct}%)`,
        `주요 클레임 유형: ${topTypesText}`
      ]
    };
  } else if (category === "service") {
    const curChats = E.rawChats(period).filter((c) => c.valid);
    const prevChats = prevP ? E.rawChats(prevP).filter((c) => c.valid) : [];
    const curBuckets = E.claimBuckets(curChats);
    const prevBuckets = prevP ? E.claimBuckets(prevChats) : { service: [] };
    const sChats = curBuckets.service;
    const prevSChats = prevBuckets.service;

    const catFilter = serviceCategoryFilterVal || "all";
    const targetChats = catFilter === "all" ? sChats : sChats.filter((c) => E.getServiceCategory(c) === catFilter);
    const prevTarget = catFilter === "all" ? prevSChats : prevSChats.filter((c) => E.getServiceCategory(c) === catFilter);

    const curCnt = targetChats.length;
    const prevCnt = prevTarget.length;
    const diff = curCnt - prevCnt;
    const diffText = diff > 0 ? `▲ ${diff.toLocaleString()}건 증가` : (diff < 0 ? `▼ ${Math.abs(diff).toLocaleString()}건 감소` : "전기 대비 변동 없음 (0건)");

    const subCounts = {};
    targetChats.forEach((c) => {
      const sub = E.getServiceSub(c);
      subCounts[sub] = (subCounts[sub] || 0) + 1;
    });
    const subEntries = Object.entries(subCounts).sort((a, b) => b[1] - a[1]).slice(0, 3);
    const topSubsText = subEntries.map(([name, cnt]) => `${name} (${Number(cnt || 0).toLocaleString()}건)`).join(", ") || "내역 없음";

    const curHuman = targetChats.filter((c) => E.getServiceCategory(c) === "휴먼에러").length;
    const curProd = targetChats.filter((c) => E.getServiceCategory(c) === "제품불만").length;

    return {
      periodLabel: period.label,
      filterLabel: catFilter === "all" ? "전체 서비스" : `유형: ${catFilter}`,
      curCount: curCnt,
      diffText: diffText,
      bullets: [
        `접수 규모: 총 ${curCnt.toLocaleString()}건 (${diffText})`,
        `분류별 발생: 휴먼에러 ${curHuman.toLocaleString()}건 / 품절·공급불만 ${curProd.toLocaleString()}건`,
        `주요 접수 상세: ${topSubsText}`
      ]
    };
  }
  return null;
}

function renderCategoryInsights(category) {
  const period = E.getPeriod();
  if (!period) return;

  const tagLabel = document.getElementById(`${category}InsightPeriodTag`);
  if (tagLabel) tagLabel.textContent = period.label;

  const data = loadCatInsights();
  const catList = (data[period.key] && data[period.key][category]) || [];
  const container = document.getElementById(`${category}InsightHistory`);
  if (!container) return;

  const catNames = { quality: "품질", delivery: "배송", service: "서비스" };
  const catName = catNames[category] || category;

  if (!catList.length) {
    container.innerHTML = `<p class="text-xs text-zinc-400">등록된 ${catName} 이슈 &amp; 인사이트가 없습니다.</p>`;
    return;
  }

  container.innerHTML = catList.slice().reverse().map((item, revIdx) => {
    const origIdx = catList.length - 1 - revIdx;
    const filterBadgeText = item.snapshot?.filterLabel || (item.tag ? `${catName}: ${item.tag}` : `전체 ${catName}`);
    const filterBadge = `<span class="rounded bg-teal-100 px-1.5 py-0.5 text-[10px] font-semibold text-teal-800">${filterBadgeText}</span>`;

    const snapshotHtml = item.snapshot && Array.isArray(item.snapshot.bullets) && item.snapshot.bullets.length ? `
      <div class="mt-2.5 rounded-lg border border-teal-100 bg-teal-50/40 p-2.5 text-xs">
        <div class="flex items-center gap-1.5 font-semibold text-teal-900 mb-1.5">
          <span>📊</span>
          <span>작성 시점 데이터 스냅샷 (${item.snapshot.periodLabel || period.label})</span>
        </div>
        <ul class="space-y-1 text-zinc-700 pl-1">
          ${item.snapshot.bullets.map((b) => `<li class="flex items-start gap-1.5 text-[11px]"><span class="text-teal-600 font-bold">•</span><span>${b}</span></li>`).join("")}
        </ul>
      </div>
    ` : "";

    return `<div class="rounded-xl bg-white p-3.5 ring-1 ring-black/5 shadow-xs">
      <div class="flex items-start justify-between gap-2 border-b border-black/5 pb-2">
        <div class="flex items-center gap-1.5">
          ${filterBadge}
          <span class="text-xs text-zinc-400 tnum">${item.at}</span>
        </div>
        <button data-del-cat-insight="${category}" data-idx="${origIdx}" type="button" class="text-xs text-zinc-400 hover:text-red-600 font-medium transition">삭제</button>
      </div>
      <p class="mt-2 whitespace-pre-wrap text-sm text-zinc-800 leading-relaxed">${(item.text || "").replace(/</g, "&lt;")}</p>
      ${snapshotHtml}
    </div>`;
  }).join("");

  container.querySelectorAll(`[data-del-cat-insight="${category}"]`).forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = +btn.dataset.idx;
      const allData = loadCatInsights();
      if (allData[period.key] && allData[period.key][category]) {
        allData[period.key][category].splice(idx, 1);
        saveCatInsights(allData);
        renderCategoryInsights(category);
        if (currentView === "report") renderReport();
      }
    });
  });
}

function initCategoryInsightHandlers(category) {
  const saveBtn = document.getElementById(`${category}InsightSave`);
  const input = document.getElementById(`${category}InsightInput`);
  const statusEl = document.getElementById(`${category}InsightStatus`);

  if (!saveBtn || saveBtn.dataset.bound) return;
  saveBtn.dataset.bound = "true";

  saveBtn.addEventListener("click", () => {
    const text = (input?.value || "").trim();
    if (!text) {
      if (statusEl) {
        statusEl.textContent = "코멘트 내용을 입력해 주세요.";
        statusEl.className = "text-xs text-amber-600 font-medium";
      }
      input?.focus();
      return;
    }

    try {
      const period = E.getPeriod();
      const allData = loadCatInsights();
      if (!allData[period.key]) allData[period.key] = {};
      if (!allData[period.key][category]) allData[period.key][category] = [];

      const now = new Date();
      const pad = (n) => String(n).padStart(2, "0");
      const atStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`;

      const snapshot = buildCategorySnapshot(category);

      let tagVal = "전체";
      if (category === "quality") tagVal = qualitySelectedTag || "전체";
      else if (category === "delivery") tagVal = deliveryVendorFilterVal !== "all" ? deliveryVendorFilterVal : "전체";
      else if (category === "service") tagVal = serviceCategoryFilterVal !== "all" ? serviceCategoryFilterVal : "전체";

      allData[period.key][category].push({
        id: `${category}_${Date.now()}`,
        category: category,
        text: text,
        tag: tagVal,
        at: atStr,
        snapshot: snapshot
      });

      saveCatInsights(allData);
      if (input) input.value = "";
      if (statusEl) {
        statusEl.textContent = "저장되었습니다! (데이터 스냅샷 포함)";
        statusEl.className = "text-xs text-emerald-600 font-semibold";
        setTimeout(() => { if (statusEl) statusEl.textContent = ""; }, 3000);
      }
      renderCategoryInsights(category);
      if (currentView === "report") renderReport();
    } catch (err) {
      console.error(`Save ${category} insight error:`, err);
      if (statusEl) {
        statusEl.textContent = "저장 중 오류가 발생했습니다.";
        statusEl.className = "text-xs text-red-600 font-medium";
      }
    }
  });
}

let deliverySearchTerm = "";
let deliveryVendorFilterVal = "all";
let deliverySelectedType = null;

function getDeliveryRisk(s) {
  const type = (s.type || "").trim();
  const text = (s.text || "").toLowerCase();

  // 1. HIGH: 분실, 오배송(타인수령/오출고), 제품 오염/이물, 고객 강성/폐기/환불
  if (type === "분실" || type === "오배송" || type.includes("벌레") || type.includes("이물")) return "HIGH";
  if (text.includes("폐기") || text.includes("환불") || text.includes("강성") || (text.includes("미수령") && type === "오배송")) return "HIGH";

  // 2. MEDIUM: 상품파손, 파손반송, 물류오발송, 이중출고
  if (type === "상품파손" || type === "파손반송" || type === "물류오발송" || type === "이중출고" || type === "파손") return "MEDIUM";

  // 3. LOW: 박스파손(단순 외박스 찌그러짐), 배송지연, 배송완료미수취, 송장탈거, 주소오류 등 일반 배송 이슈
  return "LOW";
}

function renderDeliveryTypeTrendChart() {
  const el = document.getElementById("deliveryTypeTrendChart");
  if (!el) return;
  destroyChart("deliveryTypeTrendChart");

  const list = E.getPeriodList();
  const curPeriod = E.getPeriod();
  const pIdx = E.state.periodIndex;
  // 최근 4개 기간 가져오기 (주간/월간 모드)
  const recent = list.slice(Math.max(0, pIdx - 3), pIdx + 1);

  const vFilter = deliveryVendorFilterVal || "all";

  // 최근 4개 기간 배송 데이터 수집 (벤더 필터 반영)
  const recentShipmentsByPeriod = recent.map((p) => {
    let sList = E.rawShipments(p);
    if (vFilter !== "all") sList = sList.filter((s) => s.vendor === vFilter);
    return sList;
  });

  // 1. 선택 기간(금주) 및 최근 4개 기간 유형별 건수 집계
  const curPeriodIdx = recent.findIndex((p) => p.key === curPeriod.key);
  const curShipments = recentShipmentsByPeriod[curPeriodIdx !== -1 ? curPeriodIdx : recent.length - 1] || [];
  const curTypeCounts = Object.fromEntries(E.groupCount(curShipments, "type"));

  const allRecentShipments = recentShipmentsByPeriod.flat();
  const allTypeCounts = Object.fromEntries(E.groupCount(allRecentShipments, "type"));

  // 2. 전체 배송 클레임 유형 목록 추출 (유효 항목만)
  const allTypes = Object.keys(allTypeCounts).filter((t) => t && t !== "(미지정)" && allTypeCounts[t] > 0);

  // 3. ★ 핵심: 이번주(선택한 기간) 발생건수 내림차순 정렬 (가장 많이 발생한 유형을 맨 왼쪽에 배치!)
  allTypes.sort((a, b) => {
    const diff = (curTypeCounts[b] || 0) - (curTypeCounts[a] || 0);
    if (diff !== 0) return diff;
    return (allTypeCounts[b] || 0) - (allTypeCounts[a] || 0);
  });

  // 상위 8개 유형 채택
  const topTypes = allTypes.slice(0, 8);

  function getDeliveryCat(t) {
    if (["파손반송", "상품파손", "박스파손", "파손"].includes(t)) return "파손/훼손";
    if (["오배송", "분실", "물류오발송", "이중출고", "송장탈거", "송장분실", "분류오류"].includes(t)) return "배송오류/분실";
    if (["배송지연", "배송완료미수취", "출입불가", "출입불가반송", "주소오류"].includes(t)) return "지연/미수취";
    return "기타 물류";
  }

  const flatTypes = topTypes.map((t) => ({ type: t, cat: getDeliveryCat(t), curCount: curTypeCounts[t] || 0 }));
  const labels = flatTypes.map((x) => x.type);
  const colors = ["#99f6e4", "#5eead4", "#2dd4bf", "#0f766e"];

  const datasets = recent.map((p, pIndex) => {
    const isCur = p.key === curPeriod.key;
    const sList = recentShipmentsByPeriod[pIndex];
    const typeCounts = Object.fromEntries(E.groupCount(sList, "type"));
    const data = flatTypes.map((item) => typeCounts[item.type] || 0);

    const periodShortLabel = (p.label || "").replace(/202[56]년\s*/, "");
    return {
      label: isCur ? `${periodShortLabel} (선택)` : periodShortLabel,
      data: data,
      backgroundColor: colors[pIndex % colors.length],
      borderRadius: 2,
      borderWidth: isCur ? 1.5 : 0,
      borderColor: isCur ? "#0f766e" : "transparent",
      barPercentage: 0.85,
      categoryPercentage: 0.82
    };
  });

  // 데이터 레이블 플러그인 (막대 꼭대기 숫자 항상 표시)
  const deliveryTypeTrendLabelsPlugin = {
    id: "deliveryTypeTrendLabels",
    afterDatasetsDraw(chart) {
      const ctx = chart.ctx;
      chart.data.datasets.forEach((dataset, datasetIndex) => {
        const meta = chart.getDatasetMeta(datasetIndex);
        if (!meta.visible) return;
        const isCurDataset = datasetIndex === chart.data.datasets.length - 1;

        meta.data.forEach((element, index) => {
          const val = dataset.data[index];
          if (!val || val <= 0) return;
          const str = Number(val).toLocaleString();

          ctx.save();
          ctx.font = isCurDataset
            ? "bold 10px -apple-system, BlinkMacSystemFont, sans-serif"
            : "9px -apple-system, BlinkMacSystemFont, sans-serif";
          ctx.textAlign = "center";
          ctx.textBaseline = "bottom";
          ctx.fillStyle = isCurDataset ? "#0f766e" : "#52525b";
          ctx.fillText(str, element.x, element.y - 2);
          ctx.restore();
        });
      });
    }
  };

  charts["deliveryTypeTrendChart"] = new Chart(el, {
    type: "bar",
    data: { labels, datasets },
    options: {
      layout: {
        padding: { top: 18, left: 6, right: 6, bottom: 4 }
      },
      plugins: {
        datalabels: { display: false },
        legend: {
          position: "top",
          labels: { font: { size: 11, weight: "500" }, boxWidth: 12, usePointStyle: true, pointStyle: "rectRounded" }
        },
        tooltip: {
          callbacks: {
            title: (items) => {
              if (!items.length) return "";
              const idx = items[0].dataIndex;
              const item = flatTypes[idx];
              return `${item.type} (유형) · [${item.cat}]`;
            },
            label: (item) => `${item.dataset.label}: ${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`
          }
        }
      },
      scales: {
        x: {
          grid: { display: true, color: "rgba(0,0,0,0.03)" },
          ticks: {
            font: { size: 10, weight: "500" },
            maxRotation: 90,
            minRotation: 90,
            autoSkip: false
          }
        },
        y: {
          beginAtZero: true,
          grace: "15%",
          grid: { color: "rgba(0,0,0,0.05)" },
          ticks: {
            font: { size: 10 },
            precision: 0,
            maxTicksLimit: 4,
            callback: (v) => Number(v).toLocaleString()
          }
        }
      },
      onClick: (_evt, els) => {
        if (els.length) {
          const idx = els[0].index;
          const clickedType = flatTypes[idx]?.type;
          if (clickedType) {
            deliverySelectedType = (deliverySelectedType === clickedType) ? null : clickedType;
            renderDelivery();
          }
        }
      },
      responsive: true,
      maintainAspectRatio: false
    },
    plugins: [deliveryTypeTrendLabelsPlugin]
  });

  // 하단 안내 레이블 바 렌더링
  const groupBar = document.getElementById("deliveryCategoryGroupBar");
  if (groupBar) {
    groupBar.innerHTML = `<div class="w-full text-center text-xs text-zinc-500 py-0.5 font-medium">
      금주(선택 기간) 발생건수 상위 ${flatTypes.length}개 유형 내림차순 정렬 중 · 막대 클릭 시 해당 유형 상세 분석
    </div>`;
  }
}

function renderDelivery() {
  const period = E.getPeriod();
  const prevP = E.prevPeriod();
  const curShipments = E.rawShipments(period);
  const prevShipments = prevP ? E.rawShipments(prevP) : [];

  const vFilter = deliveryVendorFilterVal || "all";

  // 0. Update top vendor button group & active filter status badge
  document.querySelectorAll(".delivery-vendor-btn").forEach((btn) => {
    const isAct = btn.dataset.vendor === vFilter;
    btn.className = isAct
      ? "delivery-vendor-btn rounded-md px-3.5 py-1.5 text-xs font-semibold bg-white text-teal-800 shadow-xs ring-1 ring-black/10 transition"
      : "delivery-vendor-btn rounded-md px-3.5 py-1.5 text-xs font-medium text-zinc-600 hover:text-zinc-900 transition";
  });

  const filterBadgeEl = document.getElementById("deliveryActiveFilterBadge");
  if (filterBadgeEl) {
    if (vFilter === "초저온") {
      filterBadgeEl.textContent = "초저온 (CJ대한통운) 필터 적용 중";
      filterBadgeEl.className = "rounded bg-sky-100 px-2 py-0.5 text-xs font-semibold text-sky-800 ring-1 ring-sky-600/20";
    } else if (vFilter === "풀필먼트") {
      filterBadgeEl.textContent = "풀필먼트 (자사/외주) 필터 적용 중";
      filterBadgeEl.className = "rounded bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800 ring-1 ring-amber-600/20";
    } else {
      filterBadgeEl.textContent = "전체 벤더 집계 중";
      filterBadgeEl.className = "rounded bg-teal-50 px-2 py-0.5 text-xs font-semibold text-teal-800 ring-1 ring-teal-600/20";
    }
  }

  // Synchronize bottom table select filter
  const selEl = document.getElementById("deliveryVendorFilter");
  if (selEl && selEl.value !== vFilter) selEl.value = vFilter;

  const curTotal = curShipments.length;
  const prevTotal = prevShipments.length;

  const curCold = curShipments.filter((s) => s.vendor === "초저온").length;
  const prevCold = prevShipments.filter((s) => s.vendor === "초저온").length;
  const coldShare = curTotal > 0 ? ((curCold / curTotal) * 100).toFixed(0) : 0;

  const curFul = curShipments.filter((s) => s.vendor === "풀필먼트").length;
  const prevFul = prevShipments.filter((s) => s.vendor === "풀필먼트").length;
  const fulShare = curTotal > 0 ? ((curFul / curTotal) * 100).toFixed(0) : 0;

  // Active dataset according to selected vendor filter
  const activeShipments = vFilter === "all" ? curShipments : curShipments.filter((s) => s.vendor === vFilter);
  const activePrevShipments = vFilter === "all" ? prevShipments : prevShipments.filter((s) => s.vendor === vFilter);
  const activeTotal = activeShipments.length;
  const activePrevTotal = activePrevShipments.length;

  const typeCounts = E.groupCount(activeShipments, "type");
  const top1Type = typeCounts[0] ? `${typeCounts[0][0]} (${Number(typeCounts[0][1] || 0).toLocaleString()}건)` : "–";

  // 1. KPI Cards
  const kpiEl = document.getElementById("deliveryKpiRow");
  if (kpiEl) {
    if (vFilter === "all") {
      kpiEl.innerHTML =
        kpiCard("배송 클레임 총 접수", `${curTotal.toLocaleString()}건`, E.delta(curTotal, prevTotal), { inverse: true }) +
        kpiCard("초저온(CJ) 접수", `${curCold.toLocaleString()}건 (${coldShare}%)`, E.delta(curCold, prevCold), { inverse: true }) +
        kpiCard("풀필먼트 접수", `${curFul.toLocaleString()}건 (${fulShare}%)`, E.delta(curFul, prevFul), { inverse: true }) +
        kpiCard("최다 발생 유형", top1Type, null);
    } else if (vFilter === "초저온") {
      kpiEl.innerHTML =
        kpiCard("초저온(CJ) 클레임 접수", `${curCold.toLocaleString()}건`, E.delta(curCold, prevCold), { inverse: true }) +
        kpiCard("전체 배송 중 점유율", `${coldShare}%`, null, { subText: `전체 ${curTotal.toLocaleString()}건 중 ${curCold.toLocaleString()}건` }) +
        kpiCard("초저온 최다 발생 유형", top1Type, null) +
        kpiCard("초저온 전주 대비 증감", `${curCold - prevCold >= 0 ? "+" : ""}${(curCold - prevCold).toLocaleString()}건`, E.delta(curCold, prevCold), { inverse: true });
    } else if (vFilter === "풀필먼트") {
      kpiEl.innerHTML =
        kpiCard("풀필먼트 클레임 접수", `${curFul.toLocaleString()}건`, E.delta(curFul, prevFul), { inverse: true }) +
        kpiCard("전체 배송 중 점유율", `${fulShare}%`, null, { subText: `전체 ${curTotal.toLocaleString()}건 중 ${curFul.toLocaleString()}건` }) +
        kpiCard("풀필먼트 최다 발생 유형", top1Type, null) +
        kpiCard("풀필먼트 전주 대비 증감", `${curFul - prevFul >= 0 ? "+" : ""}${(curFul - prevFul).toLocaleString()}건`, E.delta(curFul, prevFul), { inverse: true });
    }
  }

  // 1.5 [신규] 배송 클레임 유형별 다주차 인입 추이 막대 그래프 렌더링
  renderDeliveryTypeTrendChart();

  // Update deliveryFilterBadgeContainer
  const badgeContainer = document.getElementById("deliveryFilterBadgeContainer");
  if (badgeContainer) {
    if (deliverySelectedType) {
      badgeContainer.innerHTML = `
        <span class="inline-flex items-center gap-1.5 rounded-full bg-teal-100 px-2.5 py-0.5 text-xs font-semibold text-teal-800 shadow-sm">
          <span>유형: <strong>${deliverySelectedType}</strong></span>
          <button id="clearDeliveryTypeFilter" type="button" class="ml-1 rounded-full p-0.5 text-teal-700 hover:bg-teal-200 hover:text-teal-950 transition" title="필터 해제">✕</button>
        </span>
      `;
      const clearBtn = document.getElementById("clearDeliveryTypeFilter");
      if (clearBtn) {
        clearBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          deliverySelectedType = null;
          renderDelivery();
        });
      }
    } else {
      badgeContainer.innerHTML = "";
    }
  }

  // 2. 벤더별 점유율 (Doughnut Chart)
  const vendorTotalEl = document.getElementById("deliveryVendorTotal");
  if (vendorTotalEl) {
    vendorTotalEl.textContent = `총 ${curTotal.toLocaleString()}건 (CJ ${curCold.toLocaleString()}건 / 풀필먼트 ${curFul.toLocaleString()}건)`;
  }
  doughnutChart("deliveryVendorChart", ["초저온 (CJ)", "풀필먼트"], [curCold, curFul]);

  // 3. 배송 클레임 유형별 접수 순위 (Bar Chart) - 벤더 필터 반영 및 전체 시 풀필/초저온 색상 구분 비교
  const topTypes = typeCounts.slice(0, 8);
  const typeLabels = topTypes.map((x) => x[0]);

  if (vFilter === "전체" || vFilter === "all") {
    destroyChart("deliveryTypeChart");
    const el = document.getElementById("deliveryTypeChart");
    if (el) {
      const coldData = typeLabels.map((t) => curShipments.filter((s) => s.type === t && s.vendor === "초저온").length);
      const fulData = typeLabels.map((t) => curShipments.filter((s) => s.type === t && s.vendor === "풀필먼트").length);
      const totalData = typeLabels.map((t) => curShipments.filter((s) => s.type === t).length);

      const deliveryStackedLabelsPlugin = {
        id: "deliveryStackedLabels",
        afterDatasetsDraw(chart) {
          const ctx = chart.ctx;
          const metaCold = chart.getDatasetMeta(0);
          const metaFul = chart.getDatasetMeta(1);
          if (!metaCold || !metaFul) return;

          typeLabels.forEach((_, index) => {
            const tot = totalData[index];
            const cold = coldData[index];
            const ful = fulData[index];
            if (!tot) return;

            // 스택의 오른쪽 끝 위치 계산 (두 메타 중 더 오른쪽에 있는 x)
            const elemCold = metaCold.data[index];
            const elemFul = metaFul.data[index];
            const rightX = Math.max(elemCold ? elemCold.x : 0, elemFul ? elemFul.x : 0);
            const y = (elemCold || elemFul).y;

            const grandTot = curShipments.length;
            const pct = grandTot > 0 ? ((tot / grandTot) * 100).toFixed(1) : "0.0";

            ctx.save();
            ctx.font = "bold 11px -apple-system, BlinkMacSystemFont, sans-serif";
            ctx.textAlign = "left";
            ctx.textBaseline = "middle";
            ctx.fillStyle = "#18181b";
            const mainLabel = ` 총 ${tot.toLocaleString()}건 (${pct}%)`;
            const mainWidth = ctx.measureText(mainLabel).width;
            ctx.fillText(mainLabel, rightX + 6, y);

            ctx.font = "10px -apple-system, BlinkMacSystemFont, sans-serif";
            ctx.fillStyle = "#71717a";
            ctx.fillText(` (초저온 ${cold} / 풀필 ${ful})`, rightX + 6 + mainWidth + 4, y);
            ctx.restore();
          });
        }
      };

      charts["deliveryTypeChart"] = new Chart(el, {
        type: "bar",
        data: {
          labels: typeLabels,
          datasets: [
            {
              label: "초저온",
              data: coldData,
              backgroundColor: "#0284c7",
              hoverBackgroundColor: "#0369a1",
              borderRadius: 4
            },
            {
              label: "풀필먼트",
              data: fulData,
              backgroundColor: "#f59e0b",
              hoverBackgroundColor: "#d97706",
              borderRadius: 4
            }
          ]
        },
        options: {
          indexAxis: "y",
          responsive: true,
          maintainAspectRatio: false,
          layout: {
            padding: { right: 210 }
          },
          scales: {
            x: {
              stacked: true,
              grid: { color: "rgba(0,0,0,.05)" },
              ticks: { font: { size: 10 }, precision: 0 },
              beginAtZero: true,
              grace: "25%"
            },
            y: {
              stacked: true,
              grid: { display: false },
              ticks: { font: { size: 11, weight: "bold" } }
            }
          },
          plugins: {
            legend: {
              position: "top",
              labels: { font: { size: 11 }, boxWidth: 10 }
            },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.dataset.label}: ${ctx.raw}건`,
                footer: (items) => {
                  const total = items.reduce((s, it) => s + (it.raw || 0), 0);
                  return `유형별 전체 접수: ${total}건`;
                }
              }
            }
          }
        },
        plugins: [deliveryStackedLabelsPlugin]
      });
    }
  } else {
    const barColor = vFilter === "초저온" ? "#0284c7" : "#f59e0b";
    barChart("deliveryTypeChart", typeLabels, topTypes.map((x) => x[1]), {
      horizontal: true,
      colors: barColor
    });
  }

  // 4. 최근 기간 배송 클레임 발생 추이 (Multi-line Chart) + 전체 건수 데이터레이블 상시 노출
  const list = E.getPeriodList();
  const lookback = E.state.mode === "weekly" ? 7 : (E.state.mode === "monthly" ? 5 : (E.state.mode === "quarterly" ? 3 : 1));
  const recentWeeks = list.slice(Math.max(0, E.state.periodIndex - lookback), E.state.periodIndex + 1);
  const trendLabels = recentWeeks.map((w) => (w.label || "").replace(/202[56]년\s*/, ""));
  const trendTotal = [];
  const trendCold = [];
  const trendFul = [];

  recentWeeks.forEach((w) => {
    const sList = E.rawShipments(w);
    trendTotal.push(sList.length);
    trendCold.push(sList.filter((s) => s.vendor === "초저온").length);
    trendFul.push(sList.filter((s) => s.vendor === "풀필먼트").length);
  });

  destroyChart("deliveryTrendChart");
  const dTrendEl = document.getElementById("deliveryTrendChart");
  if (dTrendEl) {
    const deliveryDataLabelsPlugin = {
      id: "deliveryTrendLabels",
      afterDatasetsDraw(chart) {
        const ctx = chart.ctx;
        // dataset 0: 전체 배송 데이터레이블 상시 노출
        const meta = chart.getDatasetMeta(0);
        if (!meta || !meta.visible) return;
        meta.data.forEach((element, index) => {
          const val = chart.data.datasets[0].data[index];
          if (val === null || val === undefined) return;
          const str = Number(val).toLocaleString();
          const isCur = (index === chart.data.labels.length - 1);

          ctx.save();
          ctx.font = isCur
            ? "bold 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
            : "bold 10px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          const textWidth = ctx.measureText(str).width;
          const x = element.x;
          const y = element.y - 13;

          ctx.fillStyle = isCur ? "#0f766e" : "rgba(24, 24, 27, 0.90)";
          const padX = isCur ? 6 : 5, padY = 2;
          const rx = x - textWidth / 2 - padX;
          const ry = y - 7 - padY;
          const rw = textWidth + padX * 2;
          const rh = 14 + padY * 2;
          if (ctx.roundRect) {
            ctx.beginPath();
            ctx.roundRect(rx, ry, rw, rh, 3.5);
            ctx.fill();
          } else {
            ctx.fillRect(rx, ry, rw, rh);
          }
          ctx.fillStyle = "#ffffff";
          ctx.fillText(str, x, y);
          ctx.restore();
        });
      }
    };

    charts["deliveryTrendChart"] = new Chart(dTrendEl, {
      type: "line",
      data: {
        labels: trendLabels,
        datasets: [
          { label: "전체 배송", data: trendTotal, borderColor: "#0f766e", backgroundColor: "#0f766e", tension: 0.3, borderWidth: 2.5, pointRadius: 4, pointHoverRadius: 6 },
          { label: "초저온(CJ)", data: trendCold, borderColor: "#0284c7", backgroundColor: "#0284c7", tension: 0.3, borderWidth: vFilter === "초저온" ? 2.5 : 1.5, pointRadius: 3 },
          { label: "풀필먼트", data: trendFul, borderColor: "#f59e0b", backgroundColor: "#f59e0b", tension: 0.3, borderWidth: vFilter === "풀필먼트" ? 2.5 : 1.5, pointRadius: 3 }
        ]
      },
      options: {
        plugins: {
          datalabels: { display: false },
          legend: { position: "top", labels: { font: { size: 11 }, boxWidth: 10 } },
          tooltip: {
            callbacks: {
              label: (item) => `${item.dataset.label}: ${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`
            }
          }
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 10 } } },
          y: {
            grid: { color: "rgba(0,0,0,.05)" },
            beginAtZero: true,
            ticks: {
              font: { size: 10 },
              precision: 0,
              maxTicksLimit: 4,
              callback: (v) => Number(v).toLocaleString()
            }
          }
        },
        responsive: true,
        maintainAspectRatio: false
      },
      plugins: [deliveryDataLabelsPlugin]
    });
  }

  // 5. 배송 클레임 유형별 증감 현황 (피벗 테이블) - 벤더 필터 반영
  const curTypeMap = Object.fromEntries(E.groupCount(activeShipments, "type"));
  const prevTypeMap = Object.fromEntries(E.groupCount(activePrevShipments, "type"));
  const allClaimTypes = Array.from(new Set([...Object.keys(curTypeMap), ...Object.keys(prevTypeMap)]))
    .filter((s) => s && s !== "(미지정)")
    .sort((a, b) => (curTypeMap[b] || 0) - (curTypeMap[a] || 0));

  const tableBody = document.getElementById("deliveryTagTableBody");
  if (tableBody) {
    tableBody.innerHTML = allClaimTypes.map((t) => {
      const cCnt = curTypeMap[t] || 0;
      const pCnt = prevTypeMap[t] || 0;
      const diff = cCnt - pCnt;
      const share = activeTotal > 0 ? ((cCnt / activeTotal) * 100).toFixed(1) : "0.0";
      let diffBadge = "–";
      if (diff > 0) diffBadge = `<span class="tnum text-red-600 font-semibold">▲ ${diff.toLocaleString()}</span>`;
      else if (diff < 0) diffBadge = `<span class="tnum text-teal-700 font-semibold">▼ ${Math.abs(diff).toLocaleString()}</span>`;

      const isSelected = deliverySelectedType === t;
      const rowClass = isSelected
        ? "bg-teal-50 ring-2 ring-inset ring-teal-600 font-semibold cursor-pointer transition shadow-sm"
        : "hover:bg-zinc-100/80 cursor-pointer transition";

      return `<tr class="${rowClass}" data-type="${t}">
        <td class="py-2 px-3 font-medium text-zinc-900 flex items-center justify-between">
          <span class="truncate">${t}</span>
          ${isSelected ? '<span class="ml-1.5 shrink-0 rounded bg-teal-600 px-1.5 py-0.5 text-[10px] font-semibold text-white">필터 중 ✓</span>' : '<span class="ml-1.5 shrink-0 text-[10px] text-zinc-400">클릭 상세</span>'}
        </td>
        <td class="py-2 px-2 text-right tnum text-zinc-500">${pCnt.toLocaleString()}</td>
        <td class="py-2 px-2 text-right tnum font-semibold text-zinc-900">${cCnt.toLocaleString()}</td>
        <td class="py-2 px-2 text-right">${diffBadge}</td>
        <td class="py-2 px-2 text-right tnum text-zinc-500">${share}%</td>
      </tr>`;
    }).join("") || `<tr><td colspan="5" class="py-4 text-center text-zinc-400">배송 클레임 접수 내역이 없습니다.</td></tr>`;

    tableBody.querySelectorAll("tr[data-type]").forEach((row) => {
      row.addEventListener("click", () => {
        const t = row.getAttribute("data-type");
        deliverySelectedType = (deliverySelectedType === t) ? null : t;
        renderDelivery();
      });
    });
  }

  // 6. 배송 클레임 접수 상세 내역 테이블
  renderDeliveryDetailTable(curShipments);

  // 7. 배송 이슈 & 인사이트 메모 및 데이터 스냅샷 렌더링
  renderCategoryInsights("delivery");
  initCategoryInsightHandlers("delivery");
}

function renderDeliveryDetailTable(shipments) {
  const tbody = document.getElementById("deliveryDetailTableBody");
  if (!tbody) return;
  const term = (deliverySearchTerm || "").trim().toLowerCase();
  const vFilter = deliveryVendorFilterVal || "all";

  const filtered = shipments.filter((s) => {
    if (vFilter !== "all" && s.vendor !== vFilter) return false;
    if (deliverySelectedType && s.type !== deliverySelectedType) return false;
    if (!term) return true;
    return (
      (s.vendor || "").toLowerCase().includes(term) ||
      (s.type || "").toLowerCase().includes(term) ||
      (s.cust || "").toLowerCase().includes(term) ||
      (s.invoice || "").toLowerCase().includes(term) ||
      (s.prod || "").toLowerCase().includes(term) ||
      (s.text || "").toLowerCase().includes(term) ||
      (s.action || "").toLowerCase().includes(term)
    );
  });

  if (!filtered.length) {
    const emptyMsg = deliverySelectedType
      ? `선택된 배송 유형 [${deliverySelectedType}]에 해당하는 배송 클레임 건이 없습니다.`
      : (vFilter !== "all" ? `선택된 벤더 [${vFilter}]에 해당하는 배송 클레임 건이 없습니다.` : "검색 조건에 맞는 배송 클레임 건이 없습니다.");
    tbody.innerHTML = `<tr><td colspan="9" class="py-6 text-center text-zinc-400">${emptyMsg}</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.slice(0, 80).map((s) => {
    const vBadge =
      s.vendor === "초저온"
        ? '<span class="rounded bg-sky-100 px-1.5 py-0.5 text-[10px] font-semibold text-sky-800">초저온</span>'
        : '<span class="rounded bg-teal-100 px-1.5 py-0.5 text-[10px] font-semibold text-teal-800">풀필먼트</span>';

    const risk = getDeliveryRisk(s);
    const riskBadge =
      risk === "HIGH"
        ? '<span class="rounded bg-red-600 px-1.5 py-0.5 text-[10px] font-semibold text-white">HIGH</span>'
        : risk === "MEDIUM"
        ? '<span class="rounded bg-amber-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">MED</span>'
        : '<span class="rounded bg-zinc-200 px-1.5 py-0.5 text-[10px] font-medium text-zinc-700">LOW</span>';

    const dateStr = s.date || (s.time ? s.time.slice(0, 10) : "–");

    return `<tr class="hover:bg-zinc-50">
      <td class="py-2.5 px-2">${vBadge}</td>
      <td class="py-2.5 px-2 tnum text-zinc-600 whitespace-nowrap">${dateStr}</td>
      <td class="py-2.5 px-2 font-medium text-zinc-800">${s.type || "–"}</td>
      <td class="py-2.5 px-2">${riskBadge}</td>
      <td class="py-2.5 px-2 text-zinc-700 whitespace-nowrap">${s.cust || "–"}</td>
      <td class="py-2.5 px-2 tnum font-mono text-zinc-600">${s.invoice || "–"}</td>
      <td class="py-2.5 px-3 font-medium text-zinc-900">${s.prod || "–"}</td>
      <td class="py-2.5 px-4 text-zinc-800 break-words max-w-xs">${(s.text || "–").replace(/</g, "&lt;")}</td>
      <td class="py-2.5 px-4 text-zinc-600 break-words max-w-xs">${(s.action || "–").replace(/</g, "&lt;")}</td>
    </tr>`;
  }).join("");
}

let serviceSearchTerm = "";
let serviceCategoryFilterVal = "all";
let serviceSelectedSub = null;

function renderServiceTypeTrendChart() {
  const el = document.getElementById("serviceTypeTrendChart");
  if (!el) return;
  destroyChart("serviceTypeTrendChart");

  const list = E.getPeriodList();
  const curPeriod = E.getPeriod();
  const pIdx = E.state.periodIndex;
  // 최근 4개 기간 가져오기 (주간/월간 모드)
  const recent = list.slice(Math.max(0, pIdx - 3), pIdx + 1);

  // 최근 4개 기간 서비스 클레임 수집
  const recentChatsByPeriod = recent.map((p) => {
    const chats = E.rawChats(p).filter((c) => c.valid);
    return E.claimBuckets(chats).service;
  });

  // 1. 선택 기간(금주) 및 최근 4개 기간 소분류별 건수 집계
  const curPeriodIdx = recent.findIndex((p) => p.key === curPeriod.key);
  const curServiceChats = recentChatsByPeriod[curPeriodIdx !== -1 ? curPeriodIdx : recent.length - 1] || [];
  const curSubCounts = {};
  curServiceChats.forEach((c) => {
    const sub = E.getServiceSub(c);
    if (sub && sub !== "(미지정)") curSubCounts[sub] = (curSubCounts[sub] || 0) + 1;
  });

  const allSubCounts = {};
  const subToCat = {};
  recentChatsByPeriod.flat().forEach((c) => {
    const sub = E.getServiceSub(c);
    if (sub && sub !== "(미지정)") {
      allSubCounts[sub] = (allSubCounts[sub] || 0) + 1;
      if (!subToCat[sub]) subToCat[sub] = E.getServiceCategory(c);
    }
  });

  const allSubs = Object.keys(allSubCounts).filter((s) => s && allSubCounts[s] > 0);

  // 2. ★ 핵심: 이번주(선택한 기간) 발생건수 내림차순 정렬 (가장 많이 발생한 소분류가 맨 왼쪽에 배치!)
  allSubs.sort((a, b) => {
    const diff = (curSubCounts[b] || 0) - (curSubCounts[a] || 0);
    if (diff !== 0) return diff;
    return (allSubCounts[b] || 0) - (allSubCounts[a] || 0);
  });

  // 상위 8개 소분류 채택
  const topSubs = allSubs.slice(0, 8);

  const flatSubs = topSubs.map((sub) => ({
    sub,
    cat: subToCat[sub] || "서비스",
    curCount: curSubCounts[sub] || 0
  }));

  const labels = flatSubs.map((x) => x.sub);
  const colors = ["#ddd6fe", "#c4b5fd", "#a78bfa", "#7c3aed"];

  const datasets = recent.map((p, pIndex) => {
    const isCur = p.key === curPeriod.key;
    const chats = recentChatsByPeriod[pIndex];
    const subCounts = {};
    chats.forEach((c) => {
      const sub = E.getServiceSub(c);
      subCounts[sub] = (subCounts[sub] || 0) + 1;
    });
    const data = flatSubs.map((item) => subCounts[item.sub] || 0);

    const periodShortLabel = formatPeriodDisplayLabel(p, E.state.mode);
    return {
      label: isCur ? `${periodShortLabel} (선택)` : periodShortLabel,
      data: data,
      backgroundColor: colors[pIndex % colors.length],
      borderRadius: 2,
      borderWidth: isCur ? 1.5 : 0,
      borderColor: isCur ? "#7c3aed" : "transparent",
      barPercentage: 0.85,
      categoryPercentage: 0.82
    };
  });

  // 데이터 레이블 플러그인 (막대 꼭대기 숫자 항상 표시)
  const serviceTypeTrendLabelsPlugin = {
    id: "serviceTypeTrendLabels",
    afterDatasetsDraw(chart) {
      const ctx = chart.ctx;
      chart.data.datasets.forEach((dataset, datasetIndex) => {
        const meta = chart.getDatasetMeta(datasetIndex);
        if (!meta.visible) return;
        const isCurDataset = datasetIndex === chart.data.datasets.length - 1;

        meta.data.forEach((element, index) => {
          const val = dataset.data[index];
          if (!val || val <= 0) return;
          const str = Number(val).toLocaleString();

          ctx.save();
          ctx.font = isCurDataset
            ? "bold 10px -apple-system, BlinkMacSystemFont, sans-serif"
            : "9px -apple-system, BlinkMacSystemFont, sans-serif";
          ctx.textAlign = "center";
          ctx.textBaseline = "bottom";
          ctx.fillStyle = isCurDataset ? "#7c3aed" : "#52525b";
          ctx.fillText(str, element.x, element.y - 2);
          ctx.restore();
        });
      });
    }
  };

  charts["serviceTypeTrendChart"] = new Chart(el, {
    type: "bar",
    data: { labels, datasets },
    options: {
      layout: {
        padding: { top: 18, left: 6, right: 6, bottom: 4 }
      },
      plugins: {
        datalabels: { display: false },
        legend: {
          position: "top",
          labels: { font: { size: 11, weight: "500" }, boxWidth: 12, usePointStyle: true, pointStyle: "rectRounded" }
        },
        tooltip: {
          callbacks: {
            title: (items) => {
              if (!items.length) return "";
              const idx = items[0].dataIndex;
              const item = flatSubs[idx];
              return `${item.sub} (소분류) · [${item.cat}]`;
            },
            label: (item) => `${item.dataset.label}: ${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`
          }
        }
      },
      scales: {
        x: {
          grid: { display: true, color: "rgba(0,0,0,0.03)" },
          ticks: {
            font: { size: 10, weight: "500" },
            maxRotation: 90,
            minRotation: 90,
            autoSkip: false
          }
        },
        y: {
          beginAtZero: true,
          grace: "15%",
          grid: { color: "rgba(0,0,0,0.05)" },
          ticks: {
            font: { size: 10 },
            precision: 0,
            maxTicksLimit: 4,
            callback: (v) => Number(v).toLocaleString()
          }
        }
      },
      onClick: (_evt, els) => {
        if (els.length) {
          const idx = els[0].index;
          const clickedSub = flatSubs[idx]?.sub;
          if (clickedSub) {
            serviceSelectedSub = (serviceSelectedSub === clickedSub) ? null : clickedSub;
            renderService();
          }
        }
      },
      responsive: true,
      maintainAspectRatio: false
    },
    plugins: [serviceTypeTrendLabelsPlugin]
  });

  // 하단 안내 레이블 바 렌더링
  const groupBar = document.getElementById("serviceCategoryGroupBar");
  if (groupBar) {
    groupBar.innerHTML = `<div class="w-full text-center text-xs text-zinc-500 py-0.5 font-medium">
      금주(선택 기간) 발생건수 상위 ${flatSubs.length}개 소분류 내림차순 정렬 중 · 막대 클릭 시 해당 소분류 상세 필터
    </div>`;
  }
}

function renderService() {
  const period = E.getPeriod();
  const prevP = E.prevPeriod();

  const curAllChats = E.rawChats(period).filter((c) => c.valid);
  const prevAllChats = prevP ? E.rawChats(prevP).filter((c) => c.valid) : [];

  const curBuckets = E.claimBuckets(curAllChats);
  const prevBuckets = prevP ? E.claimBuckets(prevAllChats) : { service: [] };

  const sChats = curBuckets.service;
  const prevSChats = prevBuckets.service;

  const curTotal = sChats.length;
  const prevTotal = prevSChats.length;

  const curHuman = sChats.filter((c) => E.getServiceCategory(c) === "휴먼에러").length;
  const prevHuman = prevSChats.filter((c) => E.getServiceCategory(c) === "휴먼에러").length;

  const curProdClaim = sChats.filter((c) => E.getServiceCategory(c) === "제품불만").length;
  const prevProdClaim = prevSChats.filter((c) => E.getServiceCategory(c) === "제품불만").length;

  const curEscalation = sChats.filter((c) => {
    const cat = E.getServiceCategory(c);
    return cat === "상급자통화" || cat === "시스템" || c.risk === "HIGH";
  }).length;
  const prevEscalation = prevSChats.filter((c) => {
    const cat = E.getServiceCategory(c);
    return cat === "상급자통화" || cat === "시스템" || c.risk === "HIGH";
  }).length;

  const curSupervisor = sChats.filter((c) => E.getServiceCategory(c) === "상급자통화").length;
  const curSystem = sChats.filter((c) => E.getServiceCategory(c) === "시스템").length;
  const curHighRisk = sChats.filter((c) => c.risk === "HIGH" && E.getServiceCategory(c) !== "상급자통화" && E.getServiceCategory(c) !== "시스템").length;

  const subCounts = {};
  sChats.forEach((c) => {
    const sub = E.getServiceSub(c);
    subCounts[sub] = (subCounts[sub] || 0) + 1;
  });
  const subEntries = Object.entries(subCounts).sort((a, b) => b[1] - a[1]);
  const top1Sub = subEntries[0] ? `${subEntries[0][0]} (${Number(subEntries[0][1] || 0).toLocaleString()}건)` : "–";

  // 1. KPI Cards
  const kpiEl = document.getElementById("serviceKpiRow");
  if (kpiEl) {
    const subParts = [];
    subParts.push(`상급자통화 ${curSupervisor.toLocaleString()}건`);
    subParts.push(`시스템 ${curSystem.toLocaleString()}건`);
    if (curHighRisk > 0) subParts.push(`고위험 ${curHighRisk.toLocaleString()}건`);
    const escSubText = subParts.join(" · ");

    const escTooltip = `[에스컬레이션 / 시스템 처리 기준]
• 상급자 통화/강성: 상담사 1차 응대 불가로 관리자/팀장 통화로 이관되거나 대외기관 고발 언급 등 강성 건 (태그: 상급자통화/강성)
• 시스템 장애: 자사몰/플랫폼 오류, 쿠폰/결제 오류, 연동 오류 등 전산 시스템 결함 건 (태그/중분류: 시스템)
• 고위험(HIGH): 신속한 조치 및 부서 간 개입이 필요한 위험도 HIGH 건`;

    kpiEl.innerHTML =
      kpiCard("서비스 클레임 총 접수", `${curTotal.toLocaleString()}건`, E.delta(curTotal, prevTotal), { inverse: true }) +
      kpiCard("운영 / 휴먼에러", `${curHuman.toLocaleString()}건`, E.delta(curHuman, prevHuman), { inverse: true }) +
      kpiCard("품절 / 공급 / 정책불만", `${curProdClaim.toLocaleString()}건`, E.delta(curProdClaim, prevProdClaim), { inverse: true }) +
      `<div id="serviceKpiEscCard" class="cursor-pointer transition hover:opacity-90" title="클릭 시 하단 상세 내역에서 에스컬레이션/고위험 건만 즉시 필터링">` +
      kpiCard("에스컬레이션 / 시스템⚠", `${curEscalation.toLocaleString()}건`, E.delta(curEscalation, prevEscalation), {
        alert: curEscalation > 0,
        inverse: true,
        subText: escSubText + ` <span class="text-rose-600 font-bold underline ml-1">[상세보기]</span>`,
        tooltip: escTooltip + "\n• 클릭 시 하단 드릴다운 테이블에서 에스컬레이션/고위험 건만 즉시 필터링됩니다."
      }) + `</div>`;

    const escCard = document.getElementById("serviceKpiEscCard");
    if (escCard) {
      escCard.addEventListener("click", () => {
        serviceCategoryFilterVal = "escalation_all";
        const sel = document.getElementById("serviceCategoryFilter");
        if (sel) sel.value = "escalation_all";
        serviceSelectedSub = null;
        renderServiceDetailTable(sChats);
        const tblSec = document.getElementById("serviceDetailTableBody");
        if (tblSec) tblSec.scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
    }
  }

  // 1.5 [신규] 서비스 클레임 유형별 다주차 인입 추이 막대 그래프 렌더링
  renderServiceTypeTrendChart();

  // Update serviceFilterBadgeContainer
  const badgeContainer = document.getElementById("serviceFilterBadgeContainer");
  if (badgeContainer) {
    if (serviceSelectedSub) {
      badgeContainer.innerHTML = `
        <span class="inline-flex items-center gap-1.5 rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-semibold text-purple-800 shadow-sm">
          <span>불만유형: <strong>${serviceSelectedSub}</strong></span>
          <button id="clearServiceSubFilter" type="button" class="ml-1 rounded-full p-0.5 text-purple-700 hover:bg-purple-200 hover:text-purple-950 transition" title="필터 해제">✕</button>
        </span>
      `;
      const clearBtn = document.getElementById("clearServiceSubFilter");
      if (clearBtn) {
        clearBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          serviceSelectedSub = null;
          renderService();
        });
      }
    } else {
      badgeContainer.innerHTML = "";
    }
  }

  // 2. 서비스 클레임 유형별 접수 순위 (Bar Chart)
  const topSubs = subEntries.slice(0, 8);
  barChart("serviceTypeChart", topSubs.map((x) => x[0]), topSubs.map((x) => x[1]), {
    horizontal: true,
    colors: "#7c3aed"
  });

  // 3. 서비스 클레임 인입 채널 분포 (Doughnut Chart)
  const chCounts = E.groupCount(sChats, "channel");
  const chTotalEl = document.getElementById("serviceChannelTotal");
  if (chTotalEl) {
    chTotalEl.textContent = `총 ${curTotal.toLocaleString()}건`;
  }
  doughnutChart("serviceChannelChart", chCounts.map((x) => x[0]), chCounts.map((x) => x[1]));

  // 4. 최근 기간 서비스 클레임 발생 추이 (Multi-line Chart) + 전체 건수 데이터레이블 상시 노출
  const list = E.getPeriodList();
  const lookback = E.state.mode === "weekly" ? 7 : (E.state.mode === "monthly" ? 5 : (E.state.mode === "quarterly" ? 3 : 1));
  const recentWeeks = list.slice(Math.max(0, E.state.periodIndex - lookback), E.state.periodIndex + 1);
  const trendLabels = recentWeeks.map((w) => (w.label || "").replace(/202[56]년\s*/, ""));
  const trendTotal = [];
  const trendHuman = [];
  const trendProd = [];
  const trendEsc = [];

  recentWeeks.forEach((w) => {
    const wChats = E.rawChats(w).filter((c) => c.valid);
    const wBuckets = E.claimBuckets(wChats);
    const ws = wBuckets.service;
    trendTotal.push(ws.length);
    trendHuman.push(ws.filter((c) => E.getServiceCategory(c) === "휴먼에러").length);
    trendProd.push(ws.filter((c) => E.getServiceCategory(c) === "제품불만").length);
    trendEsc.push(ws.filter((c) => {
      const cat = E.getServiceCategory(c);
      return cat === "상급자통화" || cat === "시스템" || c.risk === "HIGH";
    }).length);
  });

  destroyChart("serviceTrendChart");
  const sTrendEl = document.getElementById("serviceTrendChart");
  if (sTrendEl) {
    const serviceTrendDataLabelsPlugin = {
      id: "serviceTrendLabels",
      afterDatasetsDraw(chart) {
        const ctx = chart.ctx;
        // dataset 0: 전체 서비스 데이터레이블 상시 노출
        const meta = chart.getDatasetMeta(0);
        if (!meta || !meta.visible) return;
        meta.data.forEach((element, index) => {
          const val = chart.data.datasets[0].data[index];
          if (val === null || val === undefined) return;
          const str = Number(val).toLocaleString();
          const isCur = (index === chart.data.labels.length - 1);

          ctx.save();
          ctx.font = isCur
            ? "bold 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
            : "bold 10px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          const textWidth = ctx.measureText(str).width;
          const x = element.x;
          const y = element.y - 13;

          ctx.fillStyle = isCur ? "#7c3aed" : "rgba(24, 24, 27, 0.90)";
          const padX = isCur ? 6 : 5, padY = 2;
          const rx = x - textWidth / 2 - padX;
          const ry = y - 7 - padY;
          const rw = textWidth + padX * 2;
          const rh = 14 + padY * 2;
          if (ctx.roundRect) {
            ctx.beginPath();
            ctx.roundRect(rx, ry, rw, rh, 3.5);
            ctx.fill();
          } else {
            ctx.fillRect(rx, ry, rw, rh);
          }
          ctx.fillStyle = "#ffffff";
          ctx.fillText(str, x, y);
          ctx.restore();
        });
      }
    };

    charts["serviceTrendChart"] = new Chart(sTrendEl, {
      type: "line",
      data: {
        labels: trendLabels,
        datasets: [
          { label: "전체 서비스", data: trendTotal, borderColor: "#7c3aed", backgroundColor: "#7c3aed", tension: 0.3, borderWidth: 2.5, pointRadius: 4, pointHoverRadius: 6 },
          { label: "휴먼에러", data: trendHuman, borderColor: "#ea580c", backgroundColor: "#ea580c", tension: 0.3, borderWidth: 1.5, pointRadius: 3 },
          { label: "품절/정책", data: trendProd, borderColor: "#0d9488", backgroundColor: "#0d9488", tension: 0.3, borderWidth: 1.5, pointRadius: 3 },
          { label: "상급자통화/시스템", data: trendEsc, borderColor: "#dc2626", backgroundColor: "#dc2626", tension: 0.3, borderWidth: 1.5, pointRadius: 3 }
        ]
      },
      options: {
        plugins: {
          datalabels: { display: false },
          legend: { position: "top", labels: { font: { size: 11 }, boxWidth: 10 } },
          tooltip: {
            callbacks: {
              label: (item) => `${item.dataset.label}: ${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`
            }
          }
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 10 } } },
          y: {
            grid: { color: "rgba(0,0,0,.05)" },
            beginAtZero: true,
            ticks: {
              font: { size: 10 },
              precision: 0,
              maxTicksLimit: 4,
              callback: (v) => Number(v).toLocaleString()
            }
          }
        },
        responsive: true,
        maintainAspectRatio: false
      },
      plugins: [serviceTrendDataLabelsPlugin]
    });
  }

  // 5. 서비스 클레임 유형별 증감 현황 (피벗 테이블)
  const prevSubCounts = {};
  prevSChats.forEach((c) => {
    const sub = E.getServiceSub(c);
    prevSubCounts[sub] = (prevSubCounts[sub] || 0) + 1;
  });

  const allSubs = Array.from(new Set([...Object.keys(subCounts), ...Object.keys(prevSubCounts)]))
    .filter((s) => s && s !== "(미지정)")
    .sort((a, b) => (subCounts[b] || 0) - (subCounts[a] || 0));

  const tableBody = document.getElementById("serviceTagTableBody");
  if (tableBody) {
    tableBody.innerHTML = allSubs.map((sub) => {
      const cCnt = subCounts[sub] || 0;
      const pCnt = prevSubCounts[sub] || 0;
      const diff = cCnt - pCnt;
      const share = curTotal > 0 ? ((cCnt / curTotal) * 100).toFixed(1) : "0.0";
      let diffBadge = "–";
      if (diff > 0) diffBadge = `<span class="tnum text-red-600 font-semibold">▲ ${diff.toLocaleString()}</span>`;
      else if (diff < 0) diffBadge = `<span class="tnum text-teal-700 font-semibold">▼ ${Math.abs(diff).toLocaleString()}</span>`;

      const sample = sChats.find((c) => E.getServiceSub(c) === sub) || prevSChats.find((c) => E.getServiceSub(c) === sub);
      const cat = sample ? E.getServiceCategory(sample) : "제품불만";

      const isSelected = serviceSelectedSub === sub;
      const rowClass = isSelected
        ? "bg-purple-50 ring-2 ring-inset ring-purple-600 font-semibold cursor-pointer transition shadow-sm"
        : "hover:bg-zinc-100/80 cursor-pointer transition";

      return `<tr class="${rowClass}" data-sub="${sub}">
        <td class="py-2 px-3 font-medium text-zinc-900 flex items-center justify-between">
          <span class="truncate">${sub}</span>
          ${isSelected ? '<span class="ml-1.5 shrink-0 rounded bg-purple-600 px-1.5 py-0.5 text-[10px] font-semibold text-white">필터 중 ✓</span>' : '<span class="ml-1.5 shrink-0 text-[10px] text-zinc-400">클릭 상세</span>'}
        </td>
        <td class="py-2 px-2 text-zinc-500 font-normal">${cat}</td>
        <td class="py-2 px-2 text-right tnum text-zinc-500">${pCnt.toLocaleString()}</td>
        <td class="py-2 px-2 text-right tnum font-semibold text-zinc-900">${cCnt.toLocaleString()}</td>
        <td class="py-2 px-2 text-right">${diffBadge}</td>
        <td class="py-2 px-2 text-right tnum text-zinc-500">${share}%</td>
      </tr>`;
    }).join("") || `<tr><td colspan="6" class="py-4 text-center text-zinc-400">서비스 클레임 접수 내역이 없습니다.</td></tr>`;

    tableBody.querySelectorAll("tr[data-sub]").forEach((row) => {
      row.addEventListener("click", () => {
        const sub = row.getAttribute("data-sub");
        serviceSelectedSub = (serviceSelectedSub === sub) ? null : sub;
        renderService();
      });
    });
  }

  // 6. 서비스 클레임 접수 상세 테이블
  renderServiceDetailTable(sChats);

  // 7. 서비스 이슈 & 인사이트 메모 및 데이터 스냅샷 렌더링
  renderCategoryInsights("service");
  initCategoryInsightHandlers("service");
}

function renderServiceDetailTable(sChats) {
  const tbody = document.getElementById("serviceDetailTableBody");
  if (!tbody) return;
  const term = (serviceSearchTerm || "").trim().toLowerCase();
  const catFilter = serviceCategoryFilterVal || "all";

  const filtered = sChats.filter((c) => {
    const cat = E.getServiceCategory(c);
    if (catFilter === "escalation_all") {
      if (cat !== "상급자통화" && cat !== "시스템" && c.risk !== "HIGH") return false;
    } else if (catFilter === "high_risk") {
      if (c.risk !== "HIGH") return false;
    } else if (catFilter !== "all" && cat !== catFilter) {
      return false;
    }
    if (serviceSelectedSub && E.getServiceSub(c) !== serviceSelectedSub) return false;
    if (!term) return true;
    const custName = getChatCustomerName(c);
    return (
      (custName || "").toLowerCase().includes(term) ||
      (cat || "").toLowerCase().includes(term) ||
      (E.getServiceSub(c) || "").toLowerCase().includes(term) ||
      (c.prod || "").toLowerCase().includes(term) ||
      (c.mall || "").toLowerCase().includes(term) ||
      (c.issue || "").toLowerCase().includes(term) ||
      (c.act || "").toLowerCase().includes(term) ||
      (c.tag || "").toLowerCase().includes(term)
    );
  });

  if (!filtered.length) {
    let emptyMsg = "검색 조건에 맞는 서비스 클레임 건이 없습니다.";
    if (catFilter === "escalation_all") emptyMsg = "선택 기간 접수된 에스컬레이션/시스템/고위험 클레임이 없습니다.";
    else if (catFilter === "high_risk") emptyMsg = "선택 기간 접수된 고위험(HIGH) 클레임이 없습니다.";
    else if (serviceSelectedSub) emptyMsg = `선택된 서비스 불만 유형 [${serviceSelectedSub}]에 해당하는 접수 내역이 없습니다.`;
    tbody.innerHTML = `<tr><td colspan="9" class="py-6 text-center text-zinc-400">${emptyMsg}</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.slice(0, 80).map((c) => {
    const cat = E.getServiceCategory(c);
    const sub = E.getServiceSub(c);

    let catBadge = '<span class="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] font-semibold text-zinc-800">일반</span>';
    if (cat === "휴먼에러") catBadge = '<span class="rounded bg-orange-100 px-1.5 py-0.5 text-[10px] font-semibold text-orange-800">휴먼에러</span>';
    else if (cat === "제품불만") catBadge = '<span class="rounded bg-teal-100 px-1.5 py-0.5 text-[10px] font-semibold text-teal-800">제품/정책</span>';
    else if (cat === "시스템") catBadge = '<span class="rounded bg-indigo-100 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-800">시스템</span>';
    else if (cat === "상급자통화") catBadge = '<span class="rounded bg-red-100 px-1.5 py-0.5 text-[10px] font-semibold text-red-800">상급자/강성</span>';
    else if (cat === "계절성") catBadge = '<span class="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-semibold text-blue-800">계절성</span>';
    else if (cat === "단순인입") catBadge = '<span class="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] font-semibold text-zinc-600">단순인입</span>';

    const riskBadge = c.risk === "HIGH"
      ? '<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-600 text-white shadow-2xs mr-1 animate-pulse" title="고위험 클레임">HIGH</span>'
      : '';

    const custName = getChatCustomerName(c);
    const issueText = c.issue
      ? c.issue.replace(/</g, "&lt;")
      : (c.tag
          ? `<span class="text-zinc-500 font-medium">[태그: ${c.tag}]</span> <span class="text-zinc-400 text-[11px]">(고객 문의원문 미기재 건)</span>`
          : `<span class="text-zinc-400 text-[11px]">상담원문 미작성 (단순 인입 후 즉시 종료)</span>`);
    const actText = c.act
      ? c.act.replace(/</g, "&lt;")
      : `<span class="text-zinc-400 text-[11px]">조치내역 미기재 (상담 미작성 종결)</span>`;

    const rowBg = c.risk === "HIGH" ? "bg-rose-50/50 hover:bg-rose-100/60" : "hover:bg-zinc-50";

    const dateStr = c.date || (c.time ? c.time.slice(0, 10) : "–");

    return `<tr class="${rowBg} transition">
      <td class="py-2.5 px-2"><div class="flex items-center gap-1">${catBadge}${riskBadge}</div></td>
      <td class="py-2.5 px-2 tnum text-zinc-600 whitespace-nowrap">${dateStr}</td>
      <td class="py-2.5 px-2 font-medium text-zinc-800">${sub}</td>
      <td class="py-2.5 px-2 font-medium text-zinc-900 whitespace-nowrap">${custName}</td>
      <td class="py-2.5 px-2 text-zinc-600">${c.channel || "채널톡"}</td>
      <td class="py-2.5 px-2 text-zinc-600">${c.mall || "자사몰/기타"}</td>
      <td class="py-2.5 px-3 font-medium text-zinc-900">${c.prod || "–"}</td>
      <td class="py-2.5 px-4 text-zinc-800 break-words max-w-xs">${issueText}</td>
      <td class="py-2.5 px-4 text-zinc-600 break-words max-w-xs">${actText}</td>
    </tr>`;
  }).join("");
}

let channelSearchTerm = "";
let channelFilterVal = "all";
let channelDirVal = "all";

const DOW_NAMES = ["목요일", "금요일", "토요일", "일요일", "월요일", "화요일", "수요일"];

window.renderChannel = renderChannel;
function renderChannel() {
  const period = E.getPeriod();
  const prevP = E.prevPeriod();

  const curChats = E.rawChats(period).filter((c) => c.valid);
  const prevChats = prevP ? E.rawChats(prevP).filter((c) => c.valid) : [];

  const curBoard = E.boardCount(period);
  const prevBoard = prevP ? E.boardCount(prevP) : 0;

  // 전체 고객 접점 채널 (배송접수 수기 건 제외)
  const curVisibleChats = curChats.filter((c) => c.channel !== "배송접수");
  const prevVisibleChats = prevChats.filter((c) => c.channel !== "배송접수");

  // CTI 전화 실적은 실제 CTI 통화 원장(E.aggregateCti)과 100% 동기화!
  const curCti = E.aggregateCti ? E.aggregateCti(period) : null;
  const prevCti = prevP && E.aggregateCti ? E.aggregateCti(prevP) : null;

  const curPhone = curVisibleChats.filter((c) => c.channel === "전화");
  const curPhoneIn = curCti ? curCti.inTotal : curPhone.filter((c) => c.direction === "INBOUND").length;
  const curPhoneOut = curCti ? curCti.outTotal : curPhone.filter((c) => c.direction === "OUTBOUND").length;
  const curPhoneTotal = curCti ? curCti.totalCalls : curPhone.length;
  const prevPhoneTotal = prevCti ? prevCti.totalCalls : prevVisibleChats.filter((c) => c.channel === "전화").length;

  const curOnlineChats = curVisibleChats.filter((c) => c.channel !== "전화");
  const prevOnlineChats = prevVisibleChats.filter((c) => c.channel !== "전화");
  const curTotalAll = curOnlineChats.length + curPhoneTotal + curBoard;
  const prevTotalAll = prevOnlineChats.length + prevPhoneTotal + prevBoard;

  const curAlfInflow = curVisibleChats.filter((c) => c.alfInflow);
  const curAlfTotal = curAlfInflow.length;
  const curAlfResolved = curAlfInflow.filter((c) => c.alfResolved).length;
  const alfRate = curAlfTotal > 0 ? ((curAlfResolved / curAlfTotal) * 100).toFixed(1) : "0.0";
  const prevAlfInflow = prevVisibleChats.filter((c) => c.alfInflow);
  const prevAlfTotal = prevAlfInflow.length;
  const prevAlfResolved = prevAlfInflow.filter((c) => c.alfResolved).length;
  const prevAlfRate = prevAlfTotal > 0 ? ((prevAlfResolved / prevAlfTotal) * 100).toFixed(1) : null;

  const curAgentChat = curVisibleChats.filter((c) => (c.channel === "채팅" || c.channel === "상담사챗") && c.agent && c.agent !== "ALF (AI 상담)" && c.agent !== "미배정");
  const curAgentChatIn = curAgentChat.filter((c) => c.direction !== "OUTBOUND").length;
  const curAgentChatOut = curAgentChat.filter((c) => c.direction === "OUTBOUND").length;
  const prevAgentChat = prevVisibleChats.filter((c) => (c.channel === "채팅" || c.channel === "상담사챗") && c.agent && c.agent !== "ALF (AI 상담)" && c.agent !== "미배정");
  const prevAgentChatTotal = prevAgentChat.length;

  // 1. KPI Cards (최상단 4대 핵심 지표: 총 건수 / 전화 / 채팅 / 게시판)
  const kpiEl = document.getElementById("channelKpiRow");
  if (kpiEl) {
    kpiEl.innerHTML =
      kpiCard("총 상담 인입량", `${curTotalAll.toLocaleString()}건`, E.delta(curTotalAll, prevTotalAll), {
        subText: `전화 ${curPhoneTotal.toLocaleString()} · 채팅 ${curOnlineChats.length.toLocaleString()} · 게시판 ${curBoard.toLocaleString()}`
      }) +
      kpiCard("전화 (콜 / CTI)", `${curPhoneTotal.toLocaleString()}건`, E.delta(curPhoneTotal, prevPhoneTotal), {
        alert: curPhoneTotal > 500,
        subText: `인바운드(수신) ${curPhoneIn.toLocaleString()}건 / 아웃바운드(발신) ${curPhoneOut.toLocaleString()}건`
      }) +
      kpiCard("채팅 (상담사 & 챗봇)", `${curOnlineChats.length.toLocaleString()}건`, E.delta(curOnlineChats.length, prevOnlineChats.length), {
        subText: `상담사챗 ${curAgentChat.length.toLocaleString()}건 · ALF 챗봇 ${curAlfTotal.toLocaleString()}건 (완결율 ${alfRate}%)`
      }) +
      kpiCard("게시판(스마트스토어/몰)", `${curBoard.toLocaleString()}건`, E.delta(curBoard, prevBoard), {
        subText: "자사몰 및 스마트스토어 Q&A 접수"
      });
  }

  // 2. 인/아웃바운드 믹스 차트 (Grouped Bar Chart - 배송접수 제외)
  destroyChart("channelMixChart");
  const mixEl = document.getElementById("channelMixChart");
  if (mixEl) {
    charts["channelMixChart"] = new Chart(mixEl, {
      type: "bar",
      data: {
        labels: ["전화 (콜)", "상담사챗", "챗봇(ALF)"],
        datasets: [
          {
            label: "인바운드 (수신)",
            data: [curPhoneIn, curAgentChatIn, curAlfTotal],
            backgroundColor: "#0f766e",
            borderRadius: 4
          },
          {
            label: "아웃바운드 (발신)",
            data: [curPhoneOut, curAgentChatOut, 0],
            backgroundColor: "#ea580c",
            borderRadius: 4
          }
        ]
      },
      options: {
        layout: { padding: { top: 22 } },
        plugins: {
          datalabels: { display: false },
          legend: { position: "top", labels: { font: { size: 11 }, boxWidth: 10 } },
          tooltip: {
            callbacks: {
              label: (item) => `${item.dataset.label}: ${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`
            }
          },
          datalabels: {
            display: (ctx) => {
              const v = ctx.dataset.data[ctx.dataIndex];
              return v != null && v > 0;
            },
            color: (ctx) => ctx.datasetIndex === 0 ? "#0f766e" : "#ea580c",
            anchor: "end",
            align: "top",
            offset: 2,
            font: { weight: "600", size: 10 },
            formatter: (v) => `${Number(v).toLocaleString()}건`
          }
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 11 } } },
          y: {
            grace: "15%",
            grid: { color: "rgba(0,0,0,.05)" },
            beginAtZero: true,
            ticks: {
              font: { size: 11 },
              precision: 0,
              maxTicksLimit: 4,
              callback: (v) => Number(v).toLocaleString()
            }
          }
        },
        responsive: true,
        maintainAspectRatio: false
      }
    });
  }

  // 3. 채널별 인입 점유율 (Doughnut Chart - 배송접수 제외)
  const shareTotalEl = document.getElementById("channelShareTotal");
  if (shareTotalEl) {
    shareTotalEl.textContent = `총 ${curTotalAll.toLocaleString()}건`;
  }
  doughnutChart("channelShareChart",
    ["전화 (CTI)", "상담사챗", "챗봇(ALF)", "게시판(스마트스토어/몰)"],
    [curPhoneTotal, curAgentChat.length, curAlfTotal, curBoard]
  );

  // 4. 요일별 인입 집중도 (운영주차 목~수 기준 Bar Chart - 순수 상담 기준)
  const dowCounts = [0, 1, 2, 3, 4, 5, 6].map((d) => curVisibleChats.filter((c) => c.dow === d).length);
  const dowColors = [0, 1, 2, 3, 4, 5, 6].map((d) => (d === 4 ? "#0f766e" : "#5eead4")); // Highlight Monday (dow=4)
  barChart("channelDowChart", DOW_NAMES, dowCounts, {
    colors: dowColors,
    horizontal: false
  });

  // 5. 시간대별 상담 인입 흐름 (08시 ~ 19시 Area / Line Chart - 순수 상담 기준)
  const hours = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19];
  const hourLabels = hours.map((h) => `${h}시`);
  const hourCounts = hours.map((h) => curVisibleChats.filter((c) => c.hour === h).length);

  destroyChart("channelHourChart");
  const hourEl = document.getElementById("channelHourChart");
  if (hourEl) {
    charts["channelHourChart"] = new Chart(hourEl, {
      type: "line",
      data: {
        labels: hourLabels,
        datasets: [{
          label: "시간별 인입 건수",
          data: hourCounts,
          borderColor: "#0f766e",
          backgroundColor: "rgba(15, 118, 110, 0.15)",
          fill: true,
          tension: 0.35,
          borderWidth: 2,
          pointRadius: 3
        }]
      },
      options: {
        layout: { padding: { top: 22 } },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (item) => `${item.dataset.label || '인입'}: ${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`
            }
          },
          datalabels: {
            display: (ctx) => {
              const v = ctx.dataset.data[ctx.dataIndex];
              return v != null && v > 0;
            },
            align: "top",
            anchor: "end",
            offset: 2,
            font: { size: 9.5, weight: "600" },
            color: "#0f766e",
            formatter: (v) => `${Number(v).toLocaleString()}건`
          }
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 10 } } },
          y: {
            grid: { color: "rgba(0,0,0,.05)" },
            beginAtZero: true,
            ticks: {
              font: { size: 10 },
              precision: 0,
              maxTicksLimit: 4,
              callback: (v) => Number(v).toLocaleString()
            }
          }
        },
        responsive: true,
        maintainAspectRatio: false
      }
    });
  }

  // 6. 채널별 운영 지표 매트릭스 피벗 테이블 (순수 4대 채널)
  const tableBody = document.getElementById("channelMetricTableBody");
  if (tableBody) {
    const channelRows = [
      {
        name: "전화 (Call / CTI)",
        prev: prevPhoneTotal,
        cur: curPhoneTotal,
        inCnt: curPhoneIn,
        outCnt: curPhoneOut,
        rate: curPhoneTotal > 0 ? (curPhoneOut > 0 ? `IN ${((curPhoneIn / curPhoneTotal) * 100).toFixed(0)}% / OUT ${((curPhoneOut / curPhoneTotal) * 100).toFixed(0)}%` : "100% 인바운드") : "–"
      },
      {
        name: "상담사챗 (Agent Chat)",
        prev: prevAgentChatTotal,
        cur: curAgentChat.length,
        inCnt: curAgentChatIn,
        outCnt: curAgentChatOut,
        rate: curAgentChat.length > 0 ? (curAgentChatOut > 0 ? `IN ${((curAgentChatIn / curAgentChat.length) * 100).toFixed(0)}% / OUT ${((curAgentChatOut / curAgentChat.length) * 100).toFixed(0)}%` : "100% 인바운드") : "–"
      },
      {
        name: "챗봇 (ALF)",
        prev: prevAlfTotal,
        cur: curAlfTotal,
        inCnt: curAlfTotal,
        outCnt: 0,
        rate: `${alfRate}% 자체완결`
      },
      {
        name: "게시판 (스마트스토어/몰)",
        prev: prevBoard,
        cur: curBoard,
        inCnt: curBoard,
        outCnt: 0,
        rate: "100% 답변완료"
      }
    ];

    tableBody.innerHTML = channelRows.map((r) => {
      const diff = r.cur - r.prev;
      const share = curTotalAll > 0 ? ((r.cur / curTotalAll) * 100).toFixed(1) : "0.0";
      let diffBadge = "–";
      if (diff > 0) diffBadge = `<span class="tnum text-teal-700 font-semibold">▲ ${diff.toLocaleString()}</span>`;
      else if (diff < 0) diffBadge = `<span class="tnum text-zinc-500 font-semibold">▼ ${Math.abs(diff).toLocaleString()}</span>`;

      return `<tr class="hover:bg-zinc-50/50">
        <td class="py-2.5 px-3 font-medium text-zinc-800">${r.name}</td>
        <td class="py-2.5 px-2 text-right tnum text-zinc-500">${r.prev.toLocaleString()}</td>
        <td class="py-2.5 px-2 text-right tnum font-semibold text-zinc-900">${r.cur.toLocaleString()}</td>
        <td class="py-2.5 px-2 text-right">${diffBadge}</td>
        <td class="py-2.5 px-2 text-right tnum text-zinc-600 font-medium">${share}%</td>
        <td class="py-2.5 px-2 text-right tnum text-teal-700">${r.inCnt.toLocaleString()}</td>
        <td class="py-2.5 px-2 text-right tnum text-orange-600">${r.outCnt.toLocaleString()}</td>
        <td class="py-2.5 px-2 text-right font-medium text-zinc-700">${r.rate}</td>
      </tr>`;
    }).join("");
  }

  // 7. 상담사별 종합 실적 매트릭스 (전화 vs 채팅 구분)
  renderAgentPerformanceMatrix(period, curCti, curAgentChat);

  // 8. 실시간 상담 인입 내역 상세 테이블
  renderChannelDetailTable(curChats);

  // 9. 서브 탭 렌더링
  if (channelSubTab === "cti") renderCti();
  else if (channelSubTab === "alf") renderAlf();
  else if (channelSubTab === "claim") renderClaimLeadtimeDetail();
}
window.switchChannelSubTab = switchChannelSubTab;

function renderAgentPerformanceMatrix(period, curCti, curAgentChat) {
  const tbody = document.getElementById("agentPerformanceTableBody");
  if (!tbody) return;

  const agentMap = {};

  // 1. 전화 (CTI) 실적 반영
  if (curCti && curCti.agentStats) {
    curCti.agentStats.forEach((st) => {
      const name = st.agent || "미배정";
      if (!agentMap[name]) {
        agentMap[name] = {
          name,
          callIn: 0,
          callOut: 0,
          callTotal: 0,
          callTalkSec: 0,
          callAvgSec: 0,
          chatIn: 0,
          chatOut: 0,
          chatTotal: 0
        };
      }
      agentMap[name].callIn += st.inAns || 0;
      agentMap[name].callOut += st.outAns || 0;
      agentMap[name].callTotal += st.totalAns || 0;
      agentMap[name].callTalkSec += st.totalTalkSec || 0;
      if (agentMap[name].callTotal > 0) {
        agentMap[name].callAvgSec = Math.round(agentMap[name].callTalkSec / agentMap[name].callTotal);
      }
    });
  }

  // 2. 채팅 (상담사챗) 실적 반영
  if (curAgentChat && curAgentChat.length) {
    curAgentChat.forEach((c) => {
      const name = c.agent || "미배정";
      if (!agentMap[name]) {
        agentMap[name] = {
          name,
          callIn: 0,
          callOut: 0,
          callTotal: 0,
          callTalkSec: 0,
          callAvgSec: 0,
          chatIn: 0,
          chatOut: 0,
          chatTotal: 0
        };
      }
      if (c.direction === "OUTBOUND") {
        agentMap[name].chatOut += 1;
      } else {
        agentMap[name].chatIn += 1;
      }
      agentMap[name].chatTotal += 1;
    });
  }

  const agents = Object.values(agentMap);
  const grandSum = agents.reduce((sum, a) => sum + (a.callTotal + a.chatTotal), 0);

  agents.sort((a, b) => {
    if (a.name === "미배정") return 1;
    if (b.name === "미배정") return -1;
    return (b.callTotal + b.chatTotal) - (a.callTotal + a.chatTotal);
  });

  if (!agents.length) {
    tbody.innerHTML = `<tr><td colspan="11" class="py-6 text-center text-zinc-400">선택 기간에 배정된 상담사 실적이 없습니다.</td></tr>`;
    return;
  }

  let totCallIn = 0, totCallOut = 0, totCallTot = 0, totCallTalk = 0;
  let totChatIn = 0, totChatOut = 0, totChatTot = 0;

  const rowsHtml = agents.map((a) => {
    const tot = a.callTotal + a.chatTotal;
    totCallIn += a.callIn; totCallOut += a.callOut; totCallTot += a.callTotal; totCallTalk += a.callTalkSec;
    totChatIn += a.chatIn; totChatOut += a.chatOut; totChatTot += a.chatTotal;

    const share = grandSum > 0 ? ((tot / grandSum) * 100).toFixed(1) : "0.0";
    let channelBadge = '<span class="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] text-zinc-600 font-medium">균형</span>';
    if (a.callTotal > a.chatTotal * 1.5) {
      channelBadge = '<span class="rounded bg-teal-100 px-1.5 py-0.5 text-[10px] text-teal-800 font-bold">전화 중심</span>';
    } else if (a.chatTotal > a.callTotal * 1.5) {
      channelBadge = '<span class="rounded bg-indigo-100 px-1.5 py-0.5 text-[10px] text-indigo-800 font-bold">채팅 중심</span>';
    }

    const talkM = Math.floor(a.callAvgSec / 60);
    const talkS = a.callAvgSec % 60;
    const talkStr = a.callTotal > 0 ? (talkM > 0 ? `${talkM}분 ${talkS}초` : `${talkS}초`) : "-";

    return `<tr class="hover:bg-zinc-50/70 transition">
      <td class="py-2.5 px-3 font-semibold text-zinc-900 border-r border-black/5 bg-zinc-50/30">${a.name}</td>
      <td class="py-2.5 px-2 text-right tnum text-teal-700">${a.callIn.toLocaleString()}건</td>
      <td class="py-2.5 px-2 text-right tnum text-orange-600">${a.callOut.toLocaleString()}건</td>
      <td class="py-2.5 px-2 text-right tnum font-semibold text-teal-900 bg-teal-50/20">${a.callTotal.toLocaleString()}건</td>
      <td class="py-2.5 px-2 text-right tnum text-zinc-500 border-r border-black/5 text-[11px]">${talkStr}</td>
      <td class="py-2.5 px-2 text-right tnum text-indigo-700">${a.chatIn.toLocaleString()}건</td>
      <td class="py-2.5 px-2 text-right tnum text-orange-600">${a.chatOut.toLocaleString()}건</td>
      <td class="py-2.5 px-2 text-right tnum font-semibold text-indigo-900 bg-indigo-50/20 border-r border-black/5">${a.chatTotal.toLocaleString()}건</td>
      <td class="py-2.5 px-2 text-right tnum font-extrabold text-zinc-900 bg-zinc-100/50">${tot.toLocaleString()}건</td>
      <td class="py-2.5 px-2 text-right tnum font-semibold text-zinc-700">${share}%</td>
      <td class="py-2.5 px-2 text-center">${channelBadge}</td>
    </tr>`;
  }).join("");

  const totAvgSec = totCallTot > 0 ? Math.round(totCallTalk / totCallTot) : 0;
  const totM = Math.floor(totAvgSec / 60);
  const totS = totAvgSec % 60;
  const totTalkStr = totCallTot > 0 ? (totM > 0 ? `${totM}분 ${totS}초` : `${totS}초`) : "-";

  const totalRowHtml = `
    <tr class="bg-zinc-100/90 font-bold border-t-2 border-zinc-300">
      <td class="py-2.5 px-3 text-center border-r border-black/5 text-zinc-800">상담사 실적 합계</td>
      <td class="py-2.5 px-2 text-right tnum text-teal-800">${totCallIn.toLocaleString()}건</td>
      <td class="py-2.5 px-2 text-right tnum text-orange-700">${totCallOut.toLocaleString()}건</td>
      <td class="py-2.5 px-2 text-right tnum text-teal-950 bg-teal-100/30">${totCallTot.toLocaleString()}건</td>
      <td class="py-2.5 px-2 text-right tnum text-zinc-600 border-r border-black/5 text-[11px]">${totTalkStr}</td>
      <td class="py-2.5 px-2 text-right tnum text-indigo-800">${totChatIn.toLocaleString()}건</td>
      <td class="py-2.5 px-2 text-right tnum text-orange-700">${totChatOut.toLocaleString()}건</td>
      <td class="py-2.5 px-2 text-right tnum text-indigo-950 bg-indigo-100/30 border-r border-black/5">${totChatTot.toLocaleString()}건</td>
      <td class="py-2.5 px-2 text-right tnum font-extrabold text-zinc-950 bg-zinc-200/50">${grandSum.toLocaleString()}건</td>
      <td class="py-2.5 px-2 text-right tnum text-zinc-900">100.0%</td>
      <td class="py-2.5 px-2 text-center text-zinc-500 font-normal text-[10px]">전체 상담원 합산</td>
    </tr>
  `;

  tbody.innerHTML = rowsHtml + totalRowHtml;
}

function renderChannelDetailTable(chats) {
  const tbody = document.getElementById("channelDetailTableBody");
  if (!tbody) return;
  const term = (channelSearchTerm || "").trim().toLowerCase();
  const chFilter = channelFilterVal || "all";
  const dirFilter = channelDirVal || "all";

  const filtered = chats.filter((c) => {
    if (chFilter !== "all" && c.channel !== chFilter) return false;
    if (dirFilter !== "all" && (c.direction || "INBOUND") !== dirFilter) return false;
    if (!term) return true;
    return (
      (c.channel || "").toLowerCase().includes(term) ||
      (c.journey || "").toLowerCase().includes(term) ||
      (c.tag || "").toLowerCase().includes(term) ||
      (c.issue || "").toLowerCase().includes(term) ||
      (c.act || "").toLowerCase().includes(term) ||
      (c.prod || "").toLowerCase().includes(term)
    );
  });

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="9" class="py-6 text-center text-zinc-400">검색 조건에 맞는 상담 인입 내역이 없습니다.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.slice(0, 80).map((c) => {
    let chBadge = '<span class="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] font-semibold text-zinc-800">기타</span>';
    if (c.channel === "전화") chBadge = '<span class="rounded bg-sky-100 px-1.5 py-0.5 text-[10px] font-semibold text-sky-800">전화</span>';
    else if (c.channel === "상담사챗") chBadge = '<span class="rounded bg-teal-100 px-1.5 py-0.5 text-[10px] font-semibold text-teal-800">상담사챗</span>';
    else if (c.channel === "챗봇(ALF)") chBadge = '<span class="rounded bg-purple-100 px-1.5 py-0.5 text-[10px] font-semibold text-purple-800">챗봇(ALF)</span>';
    else if (c.channel === "배송접수") chBadge = '<span class="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800">배송접수</span>';

    const dirBadge =
      c.direction === "OUTBOUND"
        ? '<span class="rounded bg-orange-100 px-1.5 py-0.5 text-[10px] font-semibold text-orange-800">OUT</span>'
        : '<span class="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-blue-700">IN</span>';

    const custName = getChatCustomerName(c);
    const dateStr = c.date || (c.time ? c.time.slice(0, 10) : "–");
    const dowName = (typeof DOW_NAMES !== "undefined" && DOW_NAMES[c.dow]) ? DOW_NAMES[c.dow] : "";
    const timeText = `${dowName.slice(0, 1)} ${c.hour || 14}시`;

    return `<tr class="hover:bg-zinc-50">
      <td class="py-2.5 px-2">${chBadge}</td>
      <td class="py-2.5 px-2">${dirBadge}</td>
      <td class="py-2.5 px-2 tnum text-zinc-600 whitespace-nowrap">${dateStr}</td>
      <td class="py-2.5 px-2 tnum text-zinc-500 whitespace-nowrap">${timeText}</td>
      <td class="py-2.5 px-2 font-medium text-zinc-900 whitespace-nowrap">${custName}</td>
      <td class="py-2.5 px-2 font-medium text-zinc-700">${c.journey || "–"}</td>
      <td class="py-2.5 px-3 text-zinc-600 font-medium truncate max-w-xs" title="${(c.tag || '–').replace(/"/g, '&quot;')}">${c.tag || "–"}</td>
      <td class="py-2.5 px-4 text-zinc-800 break-words max-w-xs">${(c.issue || "–").replace(/</g, "&lt;")}</td>
      <td class="py-2.5 px-4 text-zinc-600 break-words max-w-xs">${(c.act || "–").replace(/</g, "&lt;")}</td>
    </tr>`;
  }).join("");

  // 기간 변경 시 현재 활성화된 서브탭 즉시 재동기화 (채팅 상세, 게시판 상세, 클레임 분석 등)
  if (channelSubTab === "cti") {
    renderCti();
  } else if (channelSubTab === "chat") {
    renderChatDetail();
  } else if (channelSubTab === "board") {
    renderBoardDetail();
  } else if (channelSubTab === "alf") {
    renderAlf();
  } else if (channelSubTab === "claim") {
    renderClaimLeadtimeDetail();
  }
}

let channelSubTab = "overview";
let claimLeadtimeScope = "period";
let claimWindowDays = 30;
let claimPage = 1;
const CLAIM_PAGE_SIZE = 15;
let claimPageSize = 15;
let claimCategoryFilterVal = "all";
let claimCallFilterVal = "all";
let claimLeadtimeFilterVal = "all";
let claimQuadrantFilterVal = "all";
let claimSearchTerm = "";
let claimYScaleMode = "focus"; // "focus" (72h) or "full"
let ctiDirFilterVal = "all";
let ctiAgentFilterVal = "all";
let ctiSearchTerm = "";
let alfStatusFilterVal = "all";
let alfSearchTerm = "";

function switchChannelSubTab(tab) {
  channelSubTab = tab;
  const overviewSec = document.getElementById("channelOverviewSection");
  const ctiSec = document.getElementById("ctiDetailSection");
  const chatSec = document.getElementById("chatDetailSection");
  const boardSec = document.getElementById("boardDetailSection");
  const alfSec = document.getElementById("alfDetailSection");
  const claimSec = document.getElementById("claimLeadtimeSection");

  const btnOverview = document.getElementById("btnSubChannelOverview");
  const btnCti = document.getElementById("btnSubCtiDetail");
  const btnChat = document.getElementById("btnSubChatDetail");
  const btnBoard = document.getElementById("btnSubBoardDetail");
  const btnAlf = document.getElementById("btnSubAlfDetail");
  const btnClaim = document.getElementById("btnSubClaimLeadtimeDetail");

  const activeBtnClass = "inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-teal-700";
  const inactiveBtnClass = "inline-flex items-center gap-1.5 rounded-lg bg-zinc-100 px-3.5 py-1.5 text-xs font-medium text-zinc-600 transition hover:bg-zinc-200 hover:text-zinc-900";

  if (overviewSec) overviewSec.hidden = (tab !== "overview");
  if (ctiSec) ctiSec.hidden = (tab !== "cti");
  if (chatSec) chatSec.hidden = (tab !== "chat");
  if (boardSec) boardSec.hidden = (tab !== "board");
  if (alfSec) alfSec.hidden = (tab !== "alf");
  if (claimSec) claimSec.hidden = (tab !== "claim");

  if (btnOverview) btnOverview.className = (tab === "overview" ? activeBtnClass : inactiveBtnClass);
  if (btnCti) btnCti.className = (tab === "cti" ? activeBtnClass : inactiveBtnClass);
  if (btnChat) btnChat.className = (tab === "chat" ? activeBtnClass : inactiveBtnClass);
  if (btnBoard) btnBoard.className = (tab === "board" ? activeBtnClass : inactiveBtnClass);
  if (btnAlf) btnAlf.className = (tab === "alf" ? activeBtnClass : inactiveBtnClass);
  if (btnClaim) btnClaim.className = (tab === "claim" ? activeBtnClass : inactiveBtnClass);

  if (tab === "cti") {
    renderCti();
  } else if (tab === "chat") {
    renderChatDetail();
  } else if (tab === "board") {
    renderBoardDetail();
  } else if (tab === "alf") {
    renderAlf();
  } else if (tab === "claim") {
    renderClaimLeadtimeDetail();
  }
window.switchChannelSubTab = switchChannelSubTab;
}

function renderCtiAnswerRateTrendChart() {
  destroyChart("ctiAnswerRateTrendChart");
  const el = document.getElementById("ctiAnswerRateTrendChart");
  if (!el) return;

  const list = E.getPeriodList();
  const lookback = E.state.mode === "weekly" ? 6 : (E.state.mode === "monthly" ? 6 : 4);
  const recent = list.slice(Math.max(0, E.state.periodIndex - lookback + 1), E.state.periodIndex + 1);
  const curPeriod = E.getPeriod();

  const labels = recent.map((p) => {
    const disp = formatPeriodDisplayLabel(p, E.state.mode);
    return p.key === curPeriod.key ? `${disp} (현재)` : disp;
  });

  const ansSeries = [];
  const targetMissedSeries = [];
  const nonTargetMissedSeries = [];
  const rateSeries = [];

  recent.forEach((p) => {
    const cti = E.aggregateCti(p);
    ansSeries.push(cti.inAns);
    targetMissedSeries.push(cti.inTargetMissed);
    nonTargetMissedSeries.push(cti.inNonTargetMissed);
    rateSeries.push(Number(cti.answerRate.toFixed(1)));
  });

  charts["ctiAnswerRateTrendChart"] = new Chart(el, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          type: "line",
          label: "실질 응대율 (%)",
          data: rateSeries,
          borderColor: "#4f46e5",
          backgroundColor: "#4f46e5",
          borderWidth: 2.5,
          pointRadius: 5,
          pointHoverRadius: 7,
          pointBackgroundColor: "#ffffff",
          pointBorderColor: "#4f46e5",
          pointBorderWidth: 2,
          yAxisID: "y1",
          order: 0,
          datalabels: {
            align: "top",
            anchor: "end",
            offset: 4,
            color: "#4f46e5",
            font: { weight: "bold", size: 11 },
            formatter: (v) => `${v}%`
          }
        },
        {
          type: "bar",
          label: "응답 성공",
          data: ansSeries,
          backgroundColor: recent.map((w) => (w.key === curPeriod.key ? "#0f766e" : "#14b8a6")),
          borderRadius: 4,
          yAxisID: "y",
          order: 1,
          datalabels: {
            display: (ctx) => ctx.dataset.data[ctx.dataIndex] > 0,
            color: "#ffffff",
            anchor: "center",
            align: "center",
            font: { weight: "600", size: 10 },
            formatter: (v) => `${Number(v).toLocaleString()}건`
          }
        },
        {
          type: "bar",
          label: "실질 포기호 (대기 포기)",
          data: targetMissedSeries,
          backgroundColor: "#ef4444",
          borderRadius: 4,
          yAxisID: "y",
          order: 2,
          datalabels: {
            display: (ctx) => ctx.dataset.data[ctx.dataIndex] > 0,
            color: "#ffffff",
            anchor: "center",
            align: "center",
            font: { weight: "bold", size: 10 },
            formatter: (v) => `${v}건`
          }
        },
        {
          type: "bar",
          label: "운영시간 외 자동안내",
          data: nonTargetMissedSeries,
          backgroundColor: "rgba(241, 245, 249, 0.65)",
          borderColor: "#e2e8f0",
          borderWidth: 1,
          borderRadius: 4,
          yAxisID: "y",
          order: 3,
          datalabels: {
            display: (ctx) => ctx.dataset.data[ctx.dataIndex] > 0,
            color: "#94a3b8",
            anchor: "end",
            align: "top",
            offset: -2,
            font: { weight: "500", size: 9 },
            formatter: (v) => `${v}건`
          }
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: {
        padding: { top: 22 }
      },
      scales: {
        x: {
          stacked: true,
          grid: { display: false },
          ticks: { font: { size: 10 } }
        },
        y: {
          stacked: true,
          grid: { color: "rgba(0,0,0,.05)" },
          title: { display: true, text: "인바운드 콜 수 (건)", font: { size: 10 } },
          ticks: { font: { size: 10 }, precision: 0 },
          beginAtZero: true,
          grace: "10%"
        },
        y1: {
          position: "right",
          grid: { display: false },
          title: { display: true, text: "응대율 (%)", font: { size: 10 } },
          min: 0,
          max: 105,
          ticks: {
            font: { size: 10 },
            callback: (v) => `${v}%`
          }
        }
      },
      plugins: {
        legend: {
          position: "top",
          labels: { font: { size: 11 }, boxWidth: 10 }
        },
        tooltip: {
          callbacks: {
            label: (item) => {
              if (item.dataset.type === "line") {
                return `실질 응대율: ${item.raw}% (응답 / 실질응대대상)`;
              }
              if (item.dataset.label.includes("운영시간 외")) {
                return `${item.dataset.label}: ${item.raw}건 (영업시간 외 ARS 안내, 실질 응대율 산정 제외)`;
              }
              return `${item.dataset.label}: ${item.raw}건`;
            },
            footer: (items) => {
              const bars = items.filter((it) => it.dataset.type === "bar");
              const total = bars.reduce((s, it) => s + (it.raw || 0), 0);
              return total > 0 ? `총 인바운드 인입: ${total}건` : "";
            }
          }
        }
      }
    }
  });
}

function renderCti() {
  const period = E.getPeriod();
  const prevP = E.prevPeriod();

  const cur = E.aggregateCti(period);
  const prev = prevP ? E.aggregateCti(prevP) : null;

  // 1. KPI Cards
  const kpiEl = document.getElementById("ctiKpiRow");
  if (kpiEl) {
    const talkMin = Math.floor(cur.avgTalkSec / 60);
    const talkSec = cur.avgTalkSec % 60;
    const talkTimeStr = cur.avgTalkSec > 0 ? (talkMin > 0 ? `${talkMin}분 ${talkSec}초` : `${talkSec}초`) : "0초";
    const totalTalkHours = (cur.agentStats.reduce((s, a) => s + a.totalTalkSec, 0) / 3600).toFixed(1);

    const longCallSubHtml = cur.longCalls > 0
      ? `총 ${totalTalkHours}시간 · <button id="btnFilterLongCalls" type="button" class="inline-flex items-center gap-0.5 rounded bg-amber-100 hover:bg-amber-200 text-amber-900 px-1.5 py-0.5 text-[10px] font-bold cursor-pointer transition underline" title="클릭 시 10분 이상 통화 목록으로 즉시 드릴다운">10분 이상 통화: ${cur.longCalls.toLocaleString()}건 ⏱️ (상세보기 →)</button>`
      : `총 ${totalTalkHours}시간 누적`;

    kpiEl.innerHTML =
      kpiCard("총 CTI 통화 처리량", `${cur.totalCalls.toLocaleString()}건`, prev ? E.delta(cur.totalCalls, prev.totalCalls) : null, {
        subText: `인바운드 ${cur.inTotal.toLocaleString()}건 / 아웃바운드 ${cur.outTotal.toLocaleString()}건`
      }) +
      kpiCard("인바운드 실질 응답률", `${cur.answerRate.toFixed(1)}%`, prev ? (cur.answerRate - prev.answerRate) : null, {
        alert: cur.answerRate < 90,
        subText: `응대대상 ${cur.targetCalls.toLocaleString()}건 중 ${cur.inAns.toLocaleString()}건 응답 (전체 연결률 ${cur.connectRate.toFixed(1)}%)`,
        tooltip: `[채널톡 공식 응답률 산출 기준]\n• 산식: 상담사 연결 성공 건수 ÷ 실질 응대 대상 콜 수(성공 + 실질 부재호) × 100\n• 응대 대상(Y): 상담원 대기열(운영시간 내), 링 울림 초과/종료, 부재 등 실질 인입 건\n• 비대상(N): 운영시간 아님, IVR 진입 전 종료, 워크플로우 자동 안내 종료\n• 인바운드 전체 인입 대비 연결률: ${cur.connectRate.toFixed(1)}%`
      }) +
      kpiCard("평균 통화시간 (Talk)", talkTimeStr, null, {
        subText: longCallSubHtml,
        tooltip: `• 평균 통화 시간: 상담원과 고객 간 실제 통화 시간 평균\n• 10분(600초) 이상 통화: ${cur.longCalls.toLocaleString()}건 (클릭 시 하단 상세 내역 즉시 필터링)`
      }) +
      kpiCard("평균 대기시간 (Queue)", `${Number(cur.avgWaitSec || 0).toLocaleString()}초`, prev ? E.delta(cur.avgWaitSec, prev.avgWaitSec) : null, {
        subText: `인입 후 응답/포기까지 평균 대기`,
        tooltip: "고객이 IVR 이후 상담원 연결을 기다린 평균 대기시간"
      });

    // 10분 이상 통화 원클릭 필터링 버튼 이벤트 등록
    const btnLong = document.getElementById("btnFilterLongCalls");
    if (btnLong) {
      btnLong.addEventListener("click", (e) => {
        e.preventDefault();
        const dirSelect = document.getElementById("ctiDirFilter");
        if (dirSelect) dirSelect.value = "long-call";
        ctiDirFilterVal = "long-call";
        renderCtiDetailTable(cur.calls);
        const targetEl = document.getElementById("ctiDetailTableBody");
        if (targetEl) {
          targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      });
    }
  }

  // 1.5 전화상담 응대율 및 인입 추이 차트 렌더링
  renderCtiAnswerRateTrendChart();

  // 1.8 전화 상담 고객 여정(Journey) 분포 도넛 차트
  const ctiJourneyBadge = document.getElementById("ctiJourneyTotalBadge");
  if (ctiJourneyBadge) {
    ctiJourneyBadge.textContent = `${cur.calls.length.toLocaleString()}건 전수 분석`;
  }
  const ctiJourneyEl = document.getElementById("ctiJourneyChart");
  if (ctiJourneyEl) {
    destroyChart("ctiJourneyChart");
    const journeyCounts = {};
    cur.calls.forEach(c => {
      const j = c.journey || "기타";
      journeyCounts[j] = (journeyCounts[j] || 0) + 1;
    });
    const jEntries = Object.entries(journeyCounts).sort((a, b) => b[1] - a[1]);
    const jLabels = jEntries.map(e => e[0]);
    const jData = jEntries.map(e => e[1]);
    const jColors = ["#0f766e", "#0284c7", "#f59e0b", "#6366f1", "#8b5cf6", "#ec4899", "#64748b", "#14b8a6"];

    charts["ctiJourneyChart"] = new Chart(ctiJourneyEl, {
      type: "doughnut",
      data: {
        labels: jLabels,
        datasets: [{
          data: jData,
          backgroundColor: jColors.slice(0, jLabels.length),
          borderWidth: 2,
          borderColor: "#ffffff"
        }]
      },
      options: {
        cutout: "60%",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "right", labels: { font: { size: 11 }, boxWidth: 10 } },
          datalabels: {
            display: (ctx) => {
              const val = ctx.dataset.data[ctx.dataIndex];
              const sum = jData.reduce((a, b) => a + b, 0);
              return sum > 0 && (val / sum >= 0.05);
            },
            color: "#ffffff",
            font: { weight: "bold", size: 10 },
            formatter: (v) => {
              const sum = jData.reduce((a, b) => a + b, 0);
              return `${((v / sum) * 100).toFixed(0)}%`;
            }
          }
        }
      }
    });
  }

  // 2. 포기호 사유 도넛 차트
  const badgeEl = document.getElementById("ctiMissedTotalBadge");
  if (badgeEl) {
    badgeEl.textContent = `실질 관리대상 부재호 ${cur.inTargetMissed.toLocaleString()}건 / 운영시간 외 안내 ${cur.inNonTargetMissed.toLocaleString()}건 (총 ${cur.inMissed.toLocaleString()}건)`;
  }

  destroyChart("ctiMissedChart");
  const missedEl = document.getElementById("ctiMissedChart");
  if (missedEl) {
    const reasons = cur.missedReasons.slice(0, 5);
    const labels = reasons.length ? reasons.map((r) => r.reason) : ["포기호 없음"];
    const data = reasons.length ? reasons.map((r) => r.count) : [0];
    const colors = ["#f43f5e", "#ea580c", "#f59e0b", "#6366f1", "#8b5cf6", "#64748b"];

    charts["ctiMissedChart"] = new Chart(missedEl, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: colors.slice(0, labels.length),
          borderWidth: 2,
          borderColor: "#ffffff"
        }]
      },
      options: {
        plugins: {
          legend: { position: "bottom", labels: { font: { size: 10 }, boxWidth: 8, padding: 8 } },
          tooltip: {
            callbacks: {
              label: (item) => `${item.label}: ${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`
            }
          },
          datalabels: {
            display: (ctx) => {
              const v = ctx.dataset.data[ctx.dataIndex];
              const sum = data.reduce((a, b) => a + (Number(b) || 0), 0);
              return v > 0 && sum > 0 && (v / sum >= 0.05);
            },
            color: "#ffffff",
            font: { weight: "bold", size: 10 },
            formatter: (value, ctx) => {
              const sum = data.reduce((a, b) => a + (Number(b) || 0), 0);
              const pct = sum > 0 ? ((value / sum) * 100).toFixed(1) : "0.0";
              return `${Number(value).toLocaleString()}건\n(${pct}%)`;
            },
            textAlign: "center"
          }
        },
        cutout: "60%",
        responsive: true,
        maintainAspectRatio: false
      }
    });
  }

  // 2-2. 포기호 사유 테이블 (관리대상 부재호 vs 자연이탈 뱃지 표기)
  const reasonTbody = document.getElementById("ctiMissedReasonTableBody");
  if (reasonTbody) {
    if (!cur.missedReasons.length) {
      reasonTbody.innerHTML = `<tr><td colspan="3" class="py-4 text-center text-zinc-400">선택 기간에 발생한 포기호가 없습니다.</td></tr>`;
    } else {
      reasonTbody.innerHTML = cur.missedReasons.map((r) => {
        const isTarget = r.reason.includes("운영시간 내") || [
          "응대 가능 상담원 없음",
          "상담원 수신 거절",
          "대기열 최대 대기시간 초과",
          "링 울리는 시간 초과",
          "최대 대기열 수 초과",
          "링 울리는 중 고객 종료",
          "음성 사서함",
          "고객이 먼저 끊었을 때"
        ].includes(r.reason);

        const tagBadge = isTarget
          ? '<span class="rounded bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold text-rose-800">관리대상 (부재)</span>'
          : '<span class="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] text-zinc-500 font-medium">운영시간 외 안내</span>';

        return `
          <tr class="hover:bg-zinc-50">
            <td class="py-1.5 px-2 font-medium text-zinc-700 flex items-center justify-between">
              <span>${r.reason}</span>
              ${tagBadge}
            </td>
            <td class="py-1.5 px-2 text-right tnum font-semibold text-rose-600">${r.count.toLocaleString()}건</td>
            <td class="py-1.5 px-2 text-right tnum text-zinc-500">${r.pct}%</td>
          </tr>
        `;
      }).join("");
    }
  }

  // 2-3. 상담원별 통화 실적 바 차트
  destroyChart("ctiAgentChart");
  const agentChartEl = document.getElementById("ctiAgentChart");
  if (agentChartEl) {
    const agents = cur.agentStats;
    charts["ctiAgentChart"] = new Chart(agentChartEl, {
      type: "bar",
      data: {
        labels: agents.map((a) => a.agent.replace("CX_", "")),
        datasets: [
          {
            label: "인바운드 응대",
            data: agents.map((a) => a.inAns),
            backgroundColor: "#0f766e",
            borderRadius: 4
          },
          {
            label: "아웃바운드 발신",
            data: agents.map((a) => a.outAns),
            backgroundColor: "#ea580c",
            borderRadius: 4
          }
        ]
      },
      options: {
        layout: { padding: { top: 22 } },
        plugins: {
          datalabels: { display: false },
          legend: { position: "top", labels: { font: { size: 11 }, boxWidth: 10 } },
          tooltip: {
            callbacks: {
              label: (item) => `${item.dataset.label}: ${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`
            }
          },
          datalabels: {
            display: (ctx) => {
              const v = ctx.dataset.data[ctx.dataIndex];
              return v != null && v > 0;
            },
            color: (ctx) => ctx.datasetIndex === 0 ? "#0f766e" : "#ea580c",
            anchor: "end",
            align: "top",
            offset: 2,
            font: { weight: "600", size: 10 },
            formatter: (v) => `${Number(v).toLocaleString()}건`
          }
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 11 } } },
          y: {
            grace: "15%",
            grid: { color: "rgba(0,0,0,.05)" },
            beginAtZero: true,
            ticks: {
              font: { size: 11 },
              precision: 0,
              maxTicksLimit: 4,
              callback: (v) => Number(v).toLocaleString()
            }
          }
        },
        responsive: true,
        maintainAspectRatio: false
      }
    });
  }

  // 3. 상담원 CTI 성과 매트릭스 표
  const agentTbody = document.getElementById("ctiAgentTableBody");
  if (agentTbody) {
    const totalAnsAll = cur.agentStats.reduce((s, a) => s + a.totalAns, 0);
    if (!cur.agentStats.length) {
      agentTbody.innerHTML = `<tr><td colspan="8" class="py-6 text-center text-zinc-400">상담원 실적 데이터가 없습니다.</td></tr>`;
    } else {
      agentTbody.innerHTML = cur.agentStats.map((a) => {
        const share = totalAnsAll > 0 ? ((a.totalAns / totalAnsAll) * 100).toFixed(1) : "0";
        const avgMin = Math.floor(a.avgTalkSec / 60);
        const avgSec = a.avgTalkSec % 60;
        const avgStr = a.avgTalkSec > 0 ? `${avgMin}분 ${avgSec}초` : "–";

        const maxMin = Math.floor(a.maxTalkSec / 60);
        const maxSec = a.maxTalkSec % 60;
        const maxStr = a.maxTalkSec > 0 ? `${maxMin}분 ${maxSec}초` : "–";

        const totalTalkMin = Math.round(a.totalTalkSec / 60);

        return `<tr class="hover:bg-zinc-50">
          <td class="py-2.5 px-3 font-semibold text-zinc-800">${a.agent}</td>
          <td class="py-2.5 px-2 text-right tnum font-medium text-teal-700">${a.inAns.toLocaleString()}건</td>
          <td class="py-2.5 px-2 text-right tnum font-medium text-orange-700">${a.outAns.toLocaleString()}건</td>
          <td class="py-2.5 px-2 text-right tnum font-bold text-zinc-900">${a.totalAns.toLocaleString()}건</td>
          <td class="py-2.5 px-2 text-right tnum text-zinc-600">${share}%</td>
          <td class="py-2.5 px-2 text-right tnum text-zinc-600">${totalTalkMin.toLocaleString()}분</td>
          <td class="py-2.5 px-2 text-right tnum font-medium text-zinc-700">${avgStr}</td>
          <td class="py-2.5 px-2 text-right tnum text-zinc-500">${maxStr}</td>
        </tr>`;
      }).join("");
    }
  }

  // 4. 상담원 필터 셀렉트 박스 동적 갱신
  const agentSelect = document.getElementById("ctiAgentFilter");
  if (agentSelect) {
    const currentVal = agentSelect.value;
    const agentList = cur.agentStats.map((a) => a.agent);
    let optionsHtml = '<option value="all">전체 상담원</option>';
    agentList.forEach((ag) => {
      optionsHtml += `<option value="${ag}">${ag}</option>`;
    });
    agentSelect.innerHTML = optionsHtml;
    if (agentList.includes(currentVal)) {
      agentSelect.value = currentVal;
    }
  }

  // 5. 전화 인입/발신 문의 유형(태그)별 증감 분석 차트 및 피벗 테이블
  renderCtiTagAnalysis(cur.calls, prev ? prev.calls : []);

  // 6. CDR 상세 드릴다운 테이블 렌더링
  renderCtiDetailTable(cur.calls);
}


function renderCtiDetailTable(calls) {
  const tbody = document.getElementById("ctiDetailTableBody");
  if (!tbody) return;

  const term = (ctiSearchTerm || "").toLowerCase().trim();

  const filtered = calls.filter((c) => {
    // Direction / Status filter
    if (ctiDirFilterVal === "inbound-ans") {
      if (c.dir !== "inbound" || c.ans !== 1) return false;
    } else if (ctiDirFilterVal === "inbound-missed") {
      if ((c.dir !== "inbound" && c.dir !== "missed") || c.ans === 1) return false;
    } else if (ctiDirFilterVal === "outbound") {
      if (c.dir !== "outbound") return false;
    } else if (ctiDirFilterVal === "long-call") {
      if (c.ans !== 1 || (c.talk || 0) < 600) return false;
    }

    // Agent filter
    if (ctiAgentFilterVal !== "all" && c.agent !== ctiAgentFilterVal) {
      return false;
    }

    // Keyword search (고객명, 전화번호, 상담원, 문의내용, 조치결과, 태그, 포기사유)
    if (term) {
      const custName = getCtiCustomerName(c);
      const match =
        (custName || "").toLowerCase().includes(term) ||
        (c.phone || "").toLowerCase().includes(term) ||
        (c.agent || "").toLowerCase().includes(term) ||
        (c.issue || "").toLowerCase().includes(term) ||
        (c.act || "").toLowerCase().includes(term) ||
        (c.tag || "").toLowerCase().includes(term) ||
        (c.reason || "").toLowerCase().includes(term);
      if (!match) return false;
    }

    return true;
  });

  // Update active filter notice banner
  const noticeEl = document.getElementById("ctiActiveFilterNotice");
  if (noticeEl) {
    if (ctiDirFilterVal === "long-call") {
      noticeEl.innerHTML = `
        <span class="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-900 shadow-sm ring-1 ring-amber-500/30">
          <span>필터 적용: <strong>10분 이상 장시간 통화 (${filtered.length.toLocaleString()}건)</strong></span>
          <button id="clearCtiLongFilter" type="button" class="ml-1 rounded-full p-0.5 text-amber-800 hover:bg-amber-200 hover:text-amber-950 transition font-bold" title="필터 해제">✕ 전체보기</button>
        </span>
      `;
      const clearBtn = document.getElementById("clearCtiLongFilter");
      if (clearBtn) {
        clearBtn.addEventListener("click", () => {
          const dirSelect = document.getElementById("ctiDirFilter");
          if (dirSelect) dirSelect.value = "all";
          ctiDirFilterVal = "all";
          renderCtiDetailTable(calls);
        });
      }
    } else {
      noticeEl.innerHTML = "";
    }
  }

  if (!filtered.length) {
    const emptyMsg = ctiDirFilterVal === "long-call"
      ? "선택된 기간에 10분 이상 통화한 건이 없습니다."
      : "검색 조건에 일치하는 전화상담 통화 내역이 없습니다.";
    tbody.innerHTML = `<tr><td colspan="11" class="py-8 text-center text-zinc-400">${emptyMsg}</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.slice(0, 100).map((c) => {
    let dirBadge = '<span class="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-blue-700">IN</span>';
    if (c.dir === "outbound") {
      dirBadge = '<span class="rounded bg-orange-100 px-1.5 py-0.5 text-[10px] font-semibold text-orange-800">OUT</span>';
    } else if (c.dir === "missed") {
      dirBadge = '<span class="rounded bg-rose-50 px-1.5 py-0.5 text-[10px] font-semibold text-rose-700">MISSED</span>';
    }

    let statusBadge = '<span class="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700">응대완료</span>';
    if (c.ans === 0) {
      if (c.dir === "outbound") {
        statusBadge = '<span class="rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">부재/실패</span>';
      } else {
        statusBadge = '<span class="rounded bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold text-rose-800">포기호</span>';
      }
    }

    const custName = getCtiCustomerName(c);
    const waitStr = c.wait > 0 ? `${c.wait}초` : "–";
    const talkMin = Math.floor(c.talk / 60);
    const talkSec = c.talk % 60;
    const talkStr = c.talk > 0 ? (talkMin > 0 ? `${talkMin}분 ${talkSec}초` : `${talkSec}초`) : "–";

    const isLongCall = c.ans === 1 && c.talk >= 600;
    const talkCell = isLongCall
      ? `<span class="inline-flex items-center gap-1 rounded bg-amber-100 text-amber-900 px-1.5 py-0.5 font-bold shadow-xs ring-1 ring-amber-500/30" title="10분 이상 장시간 통화">${talkStr} ⏱️</span>`
      : `<span class="font-semibold ${c.talk >= 300 ? 'text-amber-700' : 'text-zinc-800'}">${talkStr}</span>`;

    const timeStr = c.time ? c.time.slice(5, 16) : "–";
    const tagDisplay = c.tag || c.journey || "–";
    const issueText = c.issue ? c.issue.replace(/</g, "&lt;") : (c.reason ? `<span class="text-rose-600 font-medium">[포기사유] ${c.reason}</span>` : "–");
    const actText = c.act ? c.act.replace(/</g, "&lt;") : "–";

    return `<tr class="hover:bg-zinc-50 ${isLongCall ? 'bg-amber-50/30' : ''}">
      <td class="py-2.5 px-2.5 tnum text-zinc-600 whitespace-nowrap">${timeStr}</td>
      <td class="py-2.5 px-2">${dirBadge}</td>
      <td class="py-2.5 px-2">${statusBadge}</td>
      <td class="py-2.5 px-2 font-medium text-zinc-800 whitespace-nowrap">${c.agent || "미배정"}</td>
      <td class="py-2.5 px-2 font-medium text-zinc-900 whitespace-nowrap">${custName}</td>
      <td class="py-2.5 px-2.5 tnum text-zinc-600 whitespace-nowrap">${c.phone || "–"}</td>
      <td class="py-2.5 px-2 text-right tnum text-zinc-600">${waitStr}</td>
      <td class="py-2.5 px-2 text-right tnum">${talkCell}</td>
      <td class="py-2.5 px-3 text-zinc-600 text-xs truncate max-w-[140px]" title="${tagDisplay}">${tagDisplay}</td>
      <td class="py-2.5 px-4 text-zinc-800 break-words max-w-xs">${issueText}</td>
      <td class="py-2.5 px-4 text-zinc-600 break-words max-w-xs">${actText}</td>
    </tr>`;
  }).join("");
}

function renderAlf() {
  const period = E.getPeriod();
  const prevP = E.prevPeriod();

  const cur = E.aggregateAlf(period);
  const prev = prevP ? E.aggregateAlf(prevP) : null;

  // 1. KPI Cards
  const kpiEl = document.getElementById("alfKpiRow");
  if (kpiEl) {
    const compRateNum = parseFloat(cur.compRate);
    const prevRateNum = prev ? parseFloat(prev.compRate) : null;
    const rateDiff = prevRateNum != null ? compRateNum - prevRateNum : null;

    kpiEl.innerHTML =
      kpiCard("ALF 챗봇 총 인입", `${cur.totalInflow.toLocaleString()}건`, prev ? E.delta(cur.totalInflow, prev.totalInflow) : null, {
        subText: `선택 기간 전체 챗봇 시작 건수`
      }) +
      kpiCard("챗봇 자체 완결율", `${cur.compRate}%`, rateDiff, {
        alert: compRateNum < 30,
        subText: `상담사 연결 없이 ${cur.compCount.toLocaleString()}건 완결`
      }) +
      kpiCard("상담사 전환율", `${cur.transRate}%`, prev ? (parseFloat(cur.transRate) - parseFloat(prev.transRate)) : null, {
        inverse: true,
        subText: `심층 상담 위해 ${cur.transCount.toLocaleString()}건 이관`
      }) +
      kpiCard("ALF 고객 만족도 (CSAT)", `${cur.avgCsat}점`, null, {
        subText: `5점 만점 기준 평가`
      });
  }

  // 2. 챗봇 인입 문의 유형 Top 10 차트 (Bar Chart)
  const top10 = cur.topTags.slice(0, 10);
  const tagBadgeEl = document.getElementById("alfTagTotalBadge");
  if (tagBadgeEl) {
    tagBadgeEl.textContent = `총 ${cur.totalInflow.toLocaleString()}건 (완결율 ${cur.compRate}%)`;
  }

  destroyChart("alfTagChart");
  const tagChartEl = document.getElementById("alfTagChart");
  if (tagChartEl) {
    charts["alfTagChart"] = new Chart(tagChartEl, {
      type: "bar",
      data: {
        labels: top10.map((t) => t.tag),
        datasets: [
          {
            label: "자체 완결",
            data: top10.map((t) => t.completed),
            backgroundColor: "#0d9488",
            borderRadius: 4,
            stack: "alf"
          },
          {
            label: "상담사 이관",
            data: top10.map((t) => t.transferred),
            backgroundColor: "#f97316",
            borderRadius: 4,
            stack: "alf"
          }
        ]
      },
      options: {
        indexAxis: "y",
        layout: { padding: { right: 50 } },
        plugins: {
          datalabels: { display: false },
          legend: { position: "top", labels: { font: { size: 11 }, boxWidth: 10 } },
          tooltip: {
            callbacks: {
              label: (item) => `${item.dataset.label}: ${Number(item.raw != null ? item.raw : 0).toLocaleString()}건`,
              footer: (items) => {
                const comp = items.find(it => it.datasetIndex === 0)?.raw || 0;
                const trans = items.find(it => it.datasetIndex === 1)?.raw || 0;
                const tot = comp + trans;
                const r = tot > 0 ? ((comp / tot) * 100).toFixed(1) : "0.0";
                return `합계: ${tot}건 (자체완결율: ${r}%)`;
              }
            }
          },
          datalabels: {
            display: (ctx) => {
              const v = ctx.dataset.data[ctx.dataIndex];
              return v != null && v > 0;
            },
            color: "#ffffff",
            anchor: "center",
            align: "center",
            font: { weight: "bold", size: 10 },
            formatter: (v) => `${Number(v).toLocaleString()}건`
          }
        },
        scales: {
          x: {
            grace: "15%",
            grid: { color: "rgba(0,0,0,.05)" },
            beginAtZero: true,
            ticks: {
              font: { size: 10 },
              precision: 0,
              maxTicksLimit: 4,
              callback: (v) => Number(v).toLocaleString()
            }
          },
          y: { grid: { display: false }, ticks: { font: { size: 11 } } }
        },
        responsive: true,
        maintainAspectRatio: false
      }
    });
  }

  // 3. 문의 유형별 완결 vs 상담사이관 분석표
  const tagTableBody = document.getElementById("alfTagTableBody");
  if (tagTableBody) {
    tagTableBody.innerHTML = cur.topTags.map((t) => {
      const compRate = parseFloat(t.compRate);
      let rateBadge = `<span class="tnum text-zinc-500 font-medium">${t.compRate}%</span>`;
      if (compRate >= 50) {
        rateBadge = `<span class="rounded bg-teal-50 px-1.5 py-0.5 text-xs font-semibold text-teal-700 ring-1 ring-teal-600/20">${t.compRate}%</span>`;
      } else if (compRate <= 25) {
        rateBadge = `<span class="rounded bg-rose-50 px-1.5 py-0.5 text-xs font-semibold text-rose-700 ring-1 ring-rose-600/20">${t.compRate}%</span>`;
      }

      return `<tr class="hover:bg-zinc-50/50">
        <td class="py-2 px-2.5 font-medium text-zinc-800">${t.tag}</td>
        <td class="py-2 px-1.5 text-zinc-500">${t.journey}</td>
        <td class="py-2 px-1.5 text-right tnum font-semibold text-zinc-900">${Number(t.total || 0).toLocaleString()}</td>
        <td class="py-2 px-1.5 text-right tnum text-teal-700 font-medium">${Number(t.completed || 0).toLocaleString()}</td>
        <td class="py-2 px-1.5 text-right tnum text-orange-600 font-medium">${Number(t.transferred || 0).toLocaleString()}</td>
        <td class="py-2 px-2 text-right">${rateBadge}</td>
      </tr>`;
    }).join("") || `<tr><td colspan="6" class="py-6 text-center text-zinc-400">챗봇 인입 데이터가 없습니다.</td></tr>`;
  }

  // 4. ALF 대화 원장 드릴다운
  renderAlfDetailTable(cur.chats);
}

function renderAlfDetailTable(chats) {
  const tbody = document.getElementById("alfDetailTableBody");
  if (!tbody) return;

  const term = (alfSearchTerm || "").toLowerCase().trim();
  const statusFilter = alfStatusFilterVal || "all";

  const filtered = chats.filter((c) => {
    if (statusFilter === "completed" && !c.alfResolved) return false;
    if (statusFilter === "transferred" && c.alfResolved) return false;

    if (term) {
      const match =
        (c.tag || "").toLowerCase().includes(term) ||
        (c.journey || "").toLowerCase().includes(term) ||
        (c.issue || "").toLowerCase().includes(term) ||
        (c.act || "").toLowerCase().includes(term) ||
        (c.prod || "").toLowerCase().includes(term);
      if (!match) return false;
    }
    return true;
  });

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="py-8 text-center text-zinc-400">검색 조건에 일치하는 챗봇 대화 건이 없습니다.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.slice(0, 100).map((c) => {
    const isComp = Boolean(c.alfResolved);
    const statusBadge = isComp
      ? '<span class="rounded bg-teal-50 px-2 py-0.5 text-[11px] font-semibold text-teal-700 ring-1 ring-teal-600/20">자체완결</span>'
      : '<span class="rounded bg-orange-50 px-2 py-0.5 text-[11px] font-semibold text-orange-700 ring-1 ring-orange-600/20">상담사이관</span>';

    const timeStr = c.time ? c.time.slice(5, 16) : "–";
    const csatStr = c.csat ? `${c.csat}★` : "–";
    const issueText = (c.issue || "–").replace(/</g, "&lt;");
    const actText = (c.act || "–").replace(/</g, "&lt;");

    return `<tr class="hover:bg-zinc-50">
      <td class="py-2.5 px-2.5 tnum text-zinc-600 whitespace-nowrap">${timeStr}</td>
      <td class="py-2.5 px-2">${statusBadge}</td>
      <td class="py-2.5 px-2 text-zinc-600">${c.journey || "–"}</td>
      <td class="py-2.5 px-3 font-medium text-zinc-900 truncate max-w-[150px]" title="${c.tag || "–"}">${c.tag || "–"}</td>
      <td class="py-2.5 px-2 text-center tnum font-semibold text-amber-600">${csatStr}</td>
      <td class="py-2.5 px-4 text-zinc-800 break-words max-w-xs">${issueText}</td>
      <td class="py-2.5 px-4 text-zinc-600 break-words max-w-xs">${actText}</td>
    </tr>`;
  }).join("");
}

let compSearchTerm = "";
let compActionFilterVal = "all";
let compMonthFilterVal = "all";
let compSelectedBucketKey = null; // null (기본 선택주차) | "all" (전체합계) | 특정 버킷 key
let compMatrixSortKey = "total"; // "total" (건수) | "name" (제품명)
let compMatrixSortOrder = "desc"; // "desc" (내림차순) | "asc" (오름차순)
let compDetailSortKey = "time"; // "time" (접수순) | "prod" (제품명)
let compDetailSortOrder = "desc"; // "desc" (내림차순) | "asc" (오름차순)

function getActualProductName(raw) {
  if (!raw || typeof raw !== "string") return "미지정 / 기타";
  let p = raw.replace(/[\r\n\t]+/g, " ").replace(/\s+/g, " ").trim();
  p = p.replace(/[♬♪]+$/g, "").trim();
  return p || "미지정 / 기타";
}

function getProductFamily(raw) {
  // 실제품명(10팩/20팩 등 규격 보존) 기준 반환
  return getActualProductName(raw);
}

function isQualityClaimRaw(c) {
  if (!c) return false;
  // 고객 여정(journey)이 '제품사용'인 건만 추출 (재통화 태그 제외 - 사용자 절대 기준)
  if (c.journey !== "제품사용") return false;
  if (c.sub === "재통화") return false;
  return true;
}

function isCompChat(c) {
  if (!isQualityClaimRaw(c)) return false;
  const cidStr = String(c.id);
  if (window.COMP_OVERRIDES && Array.isArray(window.COMP_OVERRIDES.excluded_ids)) {
    if (window.COMP_OVERRIDES.excluded_ids.includes(cidStr)) return false;
  }
  return true;
}

function getCompActionType(act) {
  const a = act || "";
  if (a.includes("교환") || a.includes("재출고") || a.includes("선교환") || a.includes("대체")) return "교환";
  if (a.includes("환불") || a.includes("반품") || a.includes("취소")) return "환불";
  if (a.includes("회수") || a.includes("수거") || a.includes("품질")) return "회수";
  if (a.includes("보상")) return "보상";
  return "교환";
}

function getCompBucketList(period, year) {
  if (E.state.mode === "weekly") {
    const recentWeeks = E.WEEKS.slice(Math.max(0, E.state.periodIndex - 7), E.state.periodIndex + 1);
    return recentWeeks.map((w) => ({
      key: w.key,
      label: formatPeriodDisplayLabel(w, "weekly"),
      rawChats: E.chatsForWeekKey(w.key).filter(isQualityClaimRaw),
      chats: E.chatsForWeekKey(w.key).filter(isCompChat)
    }));
  } else if (E.state.mode === "monthly") {
    const yearMonths = E.MONTHS.filter((m) => m.key.startsWith(year));
    return yearMonths.map((m) => ({
      key: m.key,
      label: m.label.replace(`${year}년 `, ""),
      rawChats: E.rawChats(m).filter(isQualityClaimRaw),
      chats: E.rawChats(m).filter(isCompChat)
    }));
  } else if (E.state.mode === "quarterly") {
    const yearQuarters = E.QUARTERS.filter((q) => q.key.startsWith(year));
    return yearQuarters.map((q) => ({
      key: q.key,
      label: q.label.replace(`${year}년 `, ""),
      rawChats: E.rawChats(q).filter(isQualityClaimRaw),
      chats: E.rawChats(q).filter(isCompChat)
    }));
  } else {
    // yearly
    const yearMonths = E.MONTHS.filter((m) => m.key.startsWith(year));
    return yearMonths.map((m) => ({
      key: m.key,
      label: m.label.replace(`${year}년 `, ""),
      rawChats: E.rawChats(m).filter(isQualityClaimRaw),
      chats: E.rawChats(m).filter(isCompChat)
    }));
  }
}

function getCompTargetChats(bucketList) {
  const period = E.getPeriod();
  if (!period) return [];
  const year = period.key.slice(0, 4);
  const buckets = bucketList || getCompBucketList(period, year);

  // If compMonthFilterVal is set and not 'all'
  if (compMonthFilterVal && compMonthFilterVal !== "all") {
    const b = buckets.find((x) => x.key === compMonthFilterVal);
    if (b) return b.rawChats || b.chats;
    const mPeriod = E.MONTHS.find((m) => m.key === compMonthFilterVal);
    if (mPeriod) return E.rawChats(mPeriod).filter(isQualityClaimRaw);
    const wPeriod = E.WEEKS.find((w) => w.key === compMonthFilterVal);
    if (wPeriod) return E.chatsForWeekKey(wPeriod.key).filter(isQualityClaimRaw);
    const qPeriod = E.QUARTERS.find((q) => q.key === compMonthFilterVal);
    if (qPeriod) return E.rawChats(qPeriod).filter(isQualityClaimRaw);
  }

  // If entire matrix (all) is selected
  if (compSelectedBucketKey === "all") {
    return buckets.flatMap((b) => b.rawChats || b.chats);
  }

  // If a specific bucket is selected via matrix click
  if (compSelectedBucketKey) {
    const b = buckets.find((x) => x.key === compSelectedBucketKey);
    if (b) return b.rawChats || b.chats;
  }

  const curPeriodChats = E.rawChats(period).filter(isQualityClaimRaw);
  if (curPeriodChats.length > 0) return curPeriodChats;
  if (buckets.length) return buckets.flatMap((b) => b.rawChats || b.chats);
  return E.WEEKS.flatMap((w) => E.chatsForWeekKey(w.key)).filter(isQualityClaimRaw);
}

function escapeHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ==========================================
// Crosshair & Quadrant Watermark Plugin for Chart.js
// ==========================================
const quadrantCrosshairPlugin = {
  id: "quadrantCrosshair",
  beforeDraw: (chart) => {
    const { ctx, chartArea, scales } = chart;
    if (!chartArea || !scales.x || !scales.y) return;
    const { left, right, top, bottom } = chartArea;
    const x20 = scales.x.getPixelForValue(20);
    const y24 = scales.y.getPixelForValue(24);

    ctx.save();

    // 1. Faint quadrant background tints
    if (x20 >= left && x20 <= right && y24 >= top && y24 <= bottom) {
      // 1사분면 (우측 상단: 재통화↑ 시간↑)
      ctx.fillStyle = "rgba(244, 63, 94, 0.05)";
      ctx.fillRect(x20, top, right - x20, y24 - top);

      // 2사분면 (좌측 상단: 재통화↓ 시간↑)
      ctx.fillStyle = "rgba(245, 158, 11, 0.04)";
      ctx.fillRect(left, top, x20 - left, y24 - top);

      // 4사분면 (우측 하단: 재통화↑ 시간↓)
      ctx.fillStyle = "rgba(2, 132, 199, 0.04)";
      ctx.fillRect(x20, y24, right - x20, bottom - y24);

      // 3사분면 (좌측 하단: 재통화↓ 시간↓)
      ctx.fillStyle = "rgba(16, 185, 129, 0.04)";
      ctx.fillRect(left, y24, x20 - left, bottom - y24);
    }

    // 2. Dashed Crosshair Lines
    ctx.setLineDash([5, 4]);
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = "rgba(100, 116, 139, 0.35)";

    // Vertical line at X = 20% (재통화 기준선)
    if (x20 >= left && x20 <= right) {
      ctx.beginPath();
      ctx.moveTo(x20, top);
      ctx.lineTo(x20, bottom);
      ctx.stroke();

      ctx.fillStyle = "#64748b";
      ctx.font = "bold 9px sans-serif";
      ctx.fillText("기준: 재통화율 20%", Math.min(x20 + 4, right - 85), bottom - 6);
    }

    // Horizontal line at Y = 24h (당일해결 기준선)
    if (y24 >= top && y24 <= bottom) {
      ctx.beginPath();
      ctx.moveTo(left, y24);
      ctx.lineTo(right, y24);
      ctx.stroke();

      ctx.fillStyle = "#64748b";
      ctx.font = "bold 9px sans-serif";
      ctx.fillText("기준: 당일 해결 (24h)", left + 6, Math.max(y24 - 4, top + 10));
    }

    // 3. Corner Quadrant Watermark Badges
    ctx.setLineDash([]);
    ctx.font = "bold 10px sans-serif";

    // 1사분면 (우측 상단)
    ctx.fillStyle = "rgba(190, 18, 60, 0.7)";
    ctx.fillText("🚨 1사분면: 최우선 개선", right - 130, top + 16);

    // 2사분면 (좌측 상단)
    ctx.fillStyle = "rgba(180, 83, 9, 0.7)";
    ctx.fillText("⏱️ 2사분면: 장기 검수형", left + 8, top + 16);

    // 4사분면 (우측 하단)
    ctx.fillStyle = "rgba(3, 105, 161, 0.7)";
    ctx.fillText("🔁 4사분면: 단기 핑퐁", right - 120, y24 + 16);

    // 3사분면 (좌측 하단)
    ctx.fillStyle = "rgba(4, 120, 87, 0.7)";
    ctx.fillText("✅ 3사분면: 빠른 종결", left + 8, y24 + 16);

    ctx.restore();
  }
};

function updateQuadrantPillsUI() {
  const container = document.getElementById("claimQuadrantPills");
  if (!container) return;
  const buttons = container.querySelectorAll(".btn-quadrant-filter");
  const activeStyles = {
    all: "bg-zinc-800 text-white shadow-2xs font-bold",
    "1": "bg-rose-600 text-white shadow-2xs font-bold ring-1 ring-rose-700",
    "2": "bg-amber-600 text-white shadow-2xs font-bold ring-1 ring-amber-700",
    "3": "bg-emerald-600 text-white shadow-2xs font-bold ring-1 ring-emerald-700",
    "4": "bg-sky-600 text-white shadow-2xs font-bold ring-1 ring-sky-700"
  };
  const inactiveStyles = {
    all: "bg-zinc-100 text-zinc-600 hover:bg-zinc-200 font-medium",
    "1": "bg-rose-50 text-rose-700 ring-1 ring-rose-600/20 hover:bg-rose-100 font-medium",
    "2": "bg-amber-50 text-amber-700 ring-1 ring-amber-600/20 hover:bg-amber-100 font-medium",
    "3": "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20 hover:bg-emerald-100 font-medium",
    "4": "bg-sky-50 text-sky-700 ring-1 ring-sky-600/20 hover:bg-sky-100 font-medium"
  };

  buttons.forEach(btn => {
    const q = btn.dataset.quadrant;
    const base = "btn-quadrant-filter rounded px-2.5 py-1 transition cursor-pointer ";
    btn.className = base + (q === claimQuadrantFilterVal ? activeStyles[q] : inactiveStyles[q]);
  });
}

window.renderClaimLeadtimeDetail = renderClaimLeadtimeDetail;
function renderClaimLeadtimeDetail() {
  const period = E.getPeriod();
  const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope, claimWindowDays);
  const s = res.summary;

  // 1. 상단 4대 메트릭 카드
  const kpiEl = document.getElementById("claimAnalysisKpiRow");
  if (kpiEl) {
    const durMinInt = Math.floor(s.avgDurationMin);
    const durSecInt = Math.round((s.avgDurationMin - durMinInt) * 60);
    const durDisplay = durMinInt > 0 ? `${durMinInt}분 ${durSecInt}초` : `${durSecInt}초`;
    const multiCalls = s.callDist.count2_3 + s.callDist.count4_plus;

    kpiEl.innerHTML =
      kpiCard("평균 통화 횟수", `건당 ${s.avgCalls}회`, null, {
        subText: `총 ${s.totalClaims.toLocaleString()}건 중 재통화 ${multiCalls.toLocaleString()}건 (${s.repeatRate}%)`,
        alert: Number(s.avgCalls) >= 1.5
      }) +
      kpiCard("평균 총 통화 시간", `건당 ${s.avgDurationMin}분`, null, {
        subText: `실제 평균 통화: ${durDisplay} (원장 합산)`
      }) +
      kpiCard("평균 해결 리드타임", `${s.avgLeadTimeHours}시간 (${s.avgLeadTimeDays}일)`, null, {
        subText: `최초 접수부터 최종 통화 완료까지 소요`
      }) +
      kpiCard("FCR (1회 종결율)", `${s.fcrRate}%`, null, {
        subText: `재통화율 ${s.repeatRate}% (글로벌 표준 품질 지표)`,
        alert: Number(s.fcrRate) < 80
      });
  }

  // 2. 도식화 다이어그램 1: 프로세스 플로우 파이프라인
  renderClaimProcessFlow(res.summary);

  // 3. 고도화 분석: 클레임 유형별 리드타임 & 재통화율 병목 매트릭스
  renderClaimCategoryBreakdown(res.summary.categoryBreakdown);

  // 4. 도식화 다이어그램 2: 세부 태그별 4사분면 리스크 버블 차트 & 랭킹
  updateQuadrantPillsUI();
  renderClaimTagMatrix(res.summary.tagBreakdown, res.claims);

  // 5. 통화 횟수별 분포 막대차트
  destroyChart("claimCallCountChart");
  const callChartEl = document.getElementById("claimCallCountChart");
  if (callChartEl) {
    const tot = s.totalClaims || 1;
    const countData = [s.callDist.count1, s.callDist.count2_3, s.callDist.count4_plus];
    const pctData = countData.map(v => ((v / tot) * 100).toFixed(1));

    const badgeEl = document.getElementById("claimCallCountBadge");
    if (badgeEl) badgeEl.textContent = `1회 종결율: ${s.fcrRate}%`;

    charts["claimCallCountChart"] = new Chart(callChartEl, {
      type: "bar",
      data: {
        labels: ["1회 해결 (단일 통화)", "2~3회 재통화", "4회 이상 다회 통화"],
        datasets: [{
          label: "클레임 건수",
          data: countData,
          backgroundColor: ["#0f766e", "#f59e0b", "#e11d48"],
          borderRadius: 6,
          maxBarThickness: 52
        }]
      },
      options: {
        layout: { padding: { top: 24 } },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: (ctx) => `${ctx.raw.toLocaleString()}건 (${pctData[ctx.dataIndex]}%)` }
          },
          datalabels: {
            display: true,
            anchor: "end",
            align: "top",
            offset: 2,
            font: { weight: "600", size: 11 },
            color: (ctx) => ["#0f766e", "#d97706", "#e11d48"][ctx.dataIndex],
            formatter: (v, ctx) => `${Number(v).toLocaleString()}건 (${pctData[ctx.dataIndex]}%)`
          }
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 11 } } },
          y: {
            grace: "20%",
            grid: { color: "rgba(0,0,0,.05)" },
            beginAtZero: true,
            ticks: { font: { size: 11 }, precision: 0, callback: (v) => Number(v).toLocaleString() }
          }
        },
        responsive: true,
        maintainAspectRatio: false
      }
    });
  }

  // 6. 해결 기간(리드타임) 구간별 건수 히스토그램
  destroyChart("claimLeadtimeChart");
  const ltChartEl = document.getElementById("claimLeadtimeChart");
  if (ltChartEl) {
    const tot = s.totalClaims || 1;
    const ltData = [s.leadDist.sameDay, s.leadDist.days1_3, s.leadDist.days4_7, s.leadDist.gt7Days];
    const ltPct = ltData.map(v => ((v / tot) * 100).toFixed(1));

    const badgeEl = document.getElementById("claimLeadtimeBadge");
    if (badgeEl) badgeEl.textContent = `당일 해결율: ${((s.leadDist.sameDay / tot) * 100).toFixed(1)}%`;

    charts["claimLeadtimeChart"] = new Chart(ltChartEl, {
      type: "bar",
      data: {
        labels: ["당일 해결 (24시간 이내)", "1~3일 (24~72시간)", "4~7일 (72~168시간)", "7일 초과 (최대 30일)"],
        datasets: [{
          label: "클레임 건수",
          data: ltData,
          backgroundColor: ["#10b981", "#0284c7", "#f59e0b", "#ef4444"],
          borderRadius: 6,
          maxBarThickness: 52
        }]
      },
      options: {
        layout: { padding: { top: 24 } },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: (ctx) => `${ctx.raw.toLocaleString()}건 (${ltPct[ctx.dataIndex]}%)` }
          },
          datalabels: {
            display: true,
            anchor: "end",
            align: "top",
            offset: 2,
            font: { weight: "600", size: 11 },
            color: (ctx) => ["#10b981", "#0284c7", "#d97706", "#ef4444"][ctx.dataIndex],
            formatter: (v, ctx) => `${Number(v).toLocaleString()}건 (${ltPct[ctx.dataIndex]}%)`
          }
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 11 } } },
          y: {
            grace: "20%",
            grid: { color: "rgba(0,0,0,.05)" },
            beginAtZero: true,
            ticks: { font: { size: 11 }, precision: 0, callback: (v) => Number(v).toLocaleString() }
          }
        },
        responsive: true,
        maintainAspectRatio: false
      }
    });
  }

    // 6.5. 클레임 대분류별 통화 및 리드타임 비교 매트릭스 표 & 가로 막대 차트 렌더링
  const cats = res.summary.categoryBreakdown || [];
  const catChartEl = document.getElementById("claimCategoryBarChart");
  if (catChartEl && cats.length > 0) {
    destroyChart("claimCategoryBarChart");
    const labels = cats.map(c => c.category);
    const repeatData = cats.map(c => c.repeatRate);
    const leadData = cats.map(c => c.avgLeadHours);

    charts["claimCategoryBarChart"] = new Chart(catChartEl, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "재통화율 (%)",
            data: repeatData,
            backgroundColor: "#e11d48",
            borderRadius: 4
          },
          {
            label: "평균 리드타임 (h)",
            data: leadData,
            backgroundColor: "#0f766e",
            borderRadius: 4
          }
        ]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "top", labels: { font: { size: 10 }, boxWidth: 8 } },
          datalabels: {
            display: true,
            anchor: "end",
            align: "right",
            font: { size: 9, weight: "bold" },
            formatter: (v, ctx) => ctx.datasetIndex === 0 ? `${v}%` : `${v}h`
          }
        },
        scales: {
          x: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.05)" } },
          y: { ticks: { font: { size: 10, weight: "600" } } }
        },
        onClick: (_evt, els) => {
          if (els.length) {
            const idx = els[0].index;
            const cat = cats[idx]?.category;
            if (cat && typeof window.setClaimCategoryFilter === "function") {
              window.setClaimCategoryFilter(cat);
            }
          }
        }
      }
    });
  }

  const catTbody = document.getElementById("claimCategoryTableBody");
  if (catTbody) {
    if (!cats.length) {
      catTbody.innerHTML = `<tr><td colspan="7" class="py-6 text-center text-zinc-400 font-medium">분석된 클레임 유형 내역이 없습니다.</td></tr>`;
    } else {
      catTbody.innerHTML = cats.map((c) => {
        const leadDaysStr = (c.avgLeadHours / 24).toFixed(1);
        return `<tr class="hover:bg-zinc-50 transition cursor-pointer" onclick="setClaimCategoryFilter('${escapeHtml(c.category)}')">
          <td class="py-2.5 px-3 font-semibold text-zinc-900 flex items-center justify-between">
            <span>${escapeHtml(c.category)}</span>
            <span class="text-[10px] font-normal text-teal-700 bg-teal-50 px-1.5 py-0.5 rounded ring-1 ring-teal-600/20">원장 필터 ➔</span>
          </td>
          <td class="py-2.5 px-2 text-right tnum font-semibold text-zinc-900">${c.total.toLocaleString()}건</td>
          <td class="py-2.5 px-2 text-right tnum text-rose-700 font-medium">${c.repeats.toLocaleString()}건</td>
          <td class="py-2.5 px-2 text-right tnum font-bold ${c.repeatRate >= 20 ? 'text-rose-600' : 'text-zinc-700'}">${c.repeatRate}%</td>
          <td class="py-2.5 px-2 text-right tnum text-zinc-800 font-medium">${c.avgCalls}회</td>
          <td class="py-2.5 px-2 text-right tnum font-semibold ${c.avgLeadHours >= 24 ? 'text-amber-700' : 'text-teal-800'}">
            ${c.avgLeadHours}h <span class="text-[10px] text-zinc-500 font-normal">(${leadDaysStr}일)</span>
          </td>
          <td class="py-2.5 px-2 text-right tnum text-zinc-700 font-medium">${c.avgDurationMin}분</td>
        </tr>`;
      }).join("");
    }
  }

  // 7. 하단 클레임 상세 원장 테이블
  renderClaimTable(res.claims);
}

function renderClaimProcessFlow(s) {
  if (!s) return;

  const elTot = document.getElementById("flowTotalClaims");
  const elFcr = document.getElementById("flowFcrRate");
  const elC1 = document.getElementById("flowCount1");
  const elRep = document.getElementById("flowRepeatRate");
  const elC23 = document.getElementById("flowCount23");
  const elRisk = document.getElementById("flowRiskRate");
  const elC4 = document.getElementById("flowCount4Plus");

  if (elTot) elTot.textContent = `${(s.totalClaims || 0).toLocaleString()}건`;
  if (elFcr) elFcr.textContent = `FCR ${s.fcrRate}%`;
  if (elC1) elC1.textContent = `${(s.callDist?.count1 || 0).toLocaleString()}건 (${s.fcrRate}%)`;
  if (elRep) elRep.textContent = `재통화 ${s.repeatRate}%`;
  if (elC23) elC23.textContent = `${(s.callDist?.count2_3 || 0).toLocaleString()}건`;
  const riskRate = s.totalClaims > 0 ? (((s.callDist?.count4_plus || 0) / s.totalClaims) * 100).toFixed(1) : "0.0";
  if (elRisk) elRisk.textContent = `위험 ${riskRate}%`;
  if (elC4) elC4.textContent = `${(s.callDist?.count4_plus || 0).toLocaleString()}건 (${riskRate}%)`;
}

function renderClaimTagMatrix(tagBreakdown, claims) {
  // 1. 활성 필터 / 검색 배지 동기화
  const quadrantPills = document.querySelectorAll("#claimQuadrantPills .btn-quadrant-filter");
  quadrantPills.forEach((pill) => {
    const q = pill.dataset.quadrant;
    if (q === claimQuadrantFilterVal) {
      pill.className = "btn-quadrant-filter rounded px-2 py-1 font-bold bg-zinc-800 text-white shadow-2xs transition cursor-pointer";
    } else {
      const qColors = {
        "1": "bg-rose-50 text-rose-700 ring-1 ring-rose-600/20 hover:bg-rose-100",
        "2": "bg-amber-50 text-amber-700 ring-1 ring-amber-600/20 hover:bg-amber-100",
        "4": "bg-sky-50 text-sky-700 ring-1 ring-sky-600/20 hover:bg-sky-100",
        "3": "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20 hover:bg-emerald-100",
        "all": "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
      };
      pill.className = `btn-quadrant-filter rounded px-2 py-1 font-semibold ${qColors[q] || "bg-zinc-100 text-zinc-600"} transition cursor-pointer`;
    }
  });

  // 우측 세부 태그 상세 실적 테이블 렌더링
  const tagTbody = document.getElementById("claimTagTableBody");
  if (tagTbody) {
    if (tagBreakdown.length === 0) {
      tagTbody.innerHTML = `<tr><td colspan="6" class="py-6 text-center text-zinc-400">분석 대상 클레임 태그가 없습니다.</td></tr>`;
    } else {
      tagTbody.innerHTML = tagBreakdown.map((t) => {
        const isSelected = claimSearchTerm && claimSearchTerm === t.tag;
        const qBadges = {
          "1": '<span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold bg-rose-100 text-rose-800 ring-1 ring-rose-600/20">🚨 1사분면</span>',
          "2": '<span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold bg-amber-100 text-amber-800 ring-1 ring-amber-600/20">⏱️ 2사분면</span>',
          "4": '<span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold bg-sky-100 text-sky-800 ring-1 ring-sky-600/20">🔁 4사분면</span>',
          "3": '<span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-emerald-100 text-emerald-800 ring-1 ring-emerald-600/20">✅ 3사분면</span>'
        };

        const rowBg = isSelected ? "bg-amber-50/80 font-semibold" : "hover:bg-zinc-50";
        return `
          <tr class="${rowBg} transition cursor-pointer" data-tag="${escapeHtml(t.tag)}">
            <td class="py-2 px-2.5 font-medium text-zinc-900 truncate max-w-[130px]" title="${escapeHtml(t.tag)}">
              ${escapeHtml(t.tag)}
            </td>
            <td class="py-2 px-2 text-right tnum font-bold text-zinc-900">${t.total.toLocaleString()}건</td>
            <td class="py-2 px-2 text-right tnum font-semibold text-rose-700">${t.repeatRate}%</td>
            <td class="py-2 px-2 text-right tnum font-semibold text-teal-800">${t.avgLeadHours}h (${(t.avgLeadHours/24).toFixed(1)}일)</td>
            <td class="py-2 px-2 text-center">${qBadges[t.quadrant] || "–"}</td>
            <td class="py-2 px-2 text-center">
              <button type="button" class="btn-tag-filter rounded px-1.5 py-0.5 text-[10px] font-medium bg-zinc-100 text-zinc-700 hover:bg-teal-600 hover:text-white transition">
                ${isSelected ? "해제" : "원장보기"}
              </button>
            </td>
          </tr>
        `;
      }).join("");

      // 테이블 행 클릭 시 해당 태그로 원장 즉시 필터링
      tagTbody.querySelectorAll("tr[data-tag]").forEach((tr) => {
        tr.addEventListener("click", () => {
          const clickedTag = tr.getAttribute("data-tag");
          if (claimSearchTerm === clickedTag) {
            claimSearchTerm = "";
          } else {
            claimSearchTerm = clickedTag;
          }
          const searchInput = document.getElementById("claimSearchInput");
          if (searchInput) searchInput.value = claimSearchTerm;
          claimPage = 1;
          renderClaimTagMatrix(tagBreakdown, claims);
          renderClaimTable(claims);

          const tblSection = document.getElementById("claimDetailTableBody");
          if (tblSection) tblSection.scrollIntoView({ behavior: "smooth", block: "center" });
        });
      });
    }
  }

  // 2. 4사분면 버블 차트 렌더링
  destroyChart("claimTagMatrixChart");
  const chartEl = document.getElementById("claimTagMatrixChart");
  if (!chartEl || tagBreakdown.length === 0) return;

  const maxY = Math.max(...tagBreakdown.map(t => t.avgLeadHours), 0);
  const isFocusScale = claimYScaleMode === "focus" && maxY > 72;
  // 72시간 집중뷰일 때 상단 캡 포인트가 차트 상단 경계선에 딱 붙어 잘리지 않도록 82h까지 여유 헤드룸(Headroom) 부여
  const effectiveYMax = isFocusScale ? 82 : Math.max(maxY * 1.15, 48);

  // 상단 캡 포인트 분산 배치 계산
  const cappedList = tagBreakdown.filter(t => isFocusScale && t.avgLeadHours > 72).sort((a, b) => a.repeatRate - b.repeatRate);
  const cappedYMap = new Map();
  cappedList.forEach((t, idx) => {
    // 인접한 X 좌표를 가진 캡 포인트들의 Y축을 71h~74h로 미세 분산하여 글자 겹침 완화
    const staggerY = 71 + (idx % 2) * 2.5;
    cappedYMap.set(t.tag, staggerY);
  });

  const bubbleData = tagBreakdown.map(t => {
    let plotY = t.avgLeadHours;
    let isCapped = false;
    if (isFocusScale && t.avgLeadHours > 72) {
      plotY = cappedYMap.get(t.tag) || 72;
      isCapped = true;
    }
    return {
      x: t.repeatRate,
      y: plotY,
      realY: t.avgLeadHours,
      isCapped,
      r: t.r,
      tag: t.tag,
      total: t.total,
      quadrant: t.quadrant,
      avgCalls: t.avgCalls
    };
  });

  // 스마트 라벨 배치 (Collision avoidance): 상단 캡 포인트와 0점 클러스터 겹침 방지
  bubbleData.forEach((d) => {
    d.showLabel = (claimQuadrantFilterVal !== "all" && d.quadrant !== claimQuadrantFilterVal)
      ? false
      : (d.total >= 3 || d.quadrant === "1" || (claimSearchTerm && claimSearchTerm === d.tag));
    d.labelAlign = "top";
    d.labelOffset = 4;
  });

  // 1) 상단 영역(y >= 68h) 포인트는 상단 경계선 잘림 방지를 위해 align을 'bottom'으로 설정
  const topCapped = bubbleData.filter(d => d.showLabel && d.y >= 68).sort((a, b) => a.x - b.x);
  topCapped.forEach((p, idx) => {
    p.labelAlign = (idx % 2 === 0) ? "bottom" : "top";
    p.labelOffset = 5;
  });

  // 2) 3사분면 원점 클러스터 (x <= 8% && y <= 2h) 겹침 방지: 최대 상위 3개만 분산 표기
  const zeroCluster = bubbleData.filter(d => d.showLabel && d.x <= 8 && d.y <= 2).sort((a, b) => b.total - a.total);
  const zeroAligns = ["top", "right", "bottom"];
  zeroCluster.forEach((p, idx) => {
    if (idx < zeroAligns.length) {
      p.labelAlign = zeroAligns[idx];
      p.labelOffset = 5;
    } else {
      // 4위 이하는 차트 복잡도 방지를 위해 숨김 (호버 툴팁 및 우측 테이블에서 전체 확인 가능)
      p.showLabel = false;
    }
  });

  const bgColors = bubbleData.map(d => {
    const isDimmed = claimQuadrantFilterVal !== "all" && d.quadrant !== claimQuadrantFilterVal;
    const alpha = isDimmed ? 0.12 : 0.8;
    if (d.quadrant === "1") return `rgba(225, 29, 72, ${alpha})`;
    if (d.quadrant === "2") return `rgba(245, 158, 11, ${alpha})`;
    if (d.quadrant === "4") return `rgba(2, 132, 199, ${alpha})`;
    return `rgba(16, 185, 129, ${alpha})`;
  });

  const borderColors = bubbleData.map(d => {
    const isDimmed = claimQuadrantFilterVal !== "all" && d.quadrant !== claimQuadrantFilterVal;
    if (isDimmed) return "rgba(148, 163, 184, 0.25)";
    if (d.quadrant === "1") return "#be123c";
    if (d.quadrant === "2") return "#d97706";
    if (d.quadrant === "4") return "#0369a1";
    return "#059669";
  });

  charts["claimTagMatrixChart"] = new Chart(chartEl, {
    type: "bubble",
    data: {
      datasets: [{
        label: "태그별 리스크 & 병목",
        data: bubbleData,
        backgroundColor: bgColors,
        borderColor: borderColors,
        borderWidth: (ctx) => {
          const d = ctx.dataset.data[ctx.dataIndex];
          return (claimSearchTerm && claimSearchTerm === d?.tag) ? 3 : 1.5;
        }
      }]
    },
    plugins: [quadrantCrosshairPlugin],
    options: {
      layout: { padding: { top: 22, right: 28, bottom: 10, left: 10 } },
      onClick: (evt, elements) => {
        if (!elements.length) return;
        const idx = elements[0].index;
        const clickedData = bubbleData[idx];
        if (clickedData && clickedData.tag) {
          if (claimSearchTerm === clickedData.tag) {
            claimSearchTerm = "";
          } else {
            claimSearchTerm = clickedData.tag;
          }
          const searchInput = document.getElementById("claimSearchInput");
          if (searchInput) searchInput.value = claimSearchTerm;
          claimPage = 1;
          renderClaimTagMatrix(tagBreakdown, claims);
          renderClaimTable(claims);

          const tblSection = document.getElementById("claimDetailTableBody");
          if (tblSection) tblSection.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (items) => items.length ? items[0].raw.tag : "",
            label: (ctx) => {
              const d = ctx.raw;
              const h = Number(d.realY || d.y) || 0;
              const days = (h / 24).toFixed(1);
              const durDisplay = `${h}시간 (${days}일)${d.isCapped ? ' [상단 72h 초과 집중표시]' : ''}`;
              const qNames = { "1": "🚨 1사분면 (최우선 개선)", "2": "⏱️ 2사분면 (장기 검수형)", "3": "✅ 3사분면 (빠른 종결)", "4": "🔁 4사분면 (단기 핑퐁)" };
              return [
                `총 건수: ${d.total.toLocaleString()}건 (평균 ${d.avgCalls}회 통화)`,
                `재통화율: ${d.x}% (재통화 기준선: 20%)`,
                `평균 해결시간: ${durDisplay}`,
                `사분면: ${qNames[d.quadrant] || ""}`,
                `💡 클릭 시 하단 원장 자동 필터링`
              ];
            }
          }
        },
        datalabels: {
          display: (ctx) => {
            const d = ctx.dataset.data[ctx.dataIndex];
            return d.showLabel;
          },
          align: (ctx) => {
            const d = ctx.dataset.data[ctx.dataIndex];
            return d.labelAlign || "top";
          },
          offset: (ctx) => {
            const d = ctx.dataset.data[ctx.dataIndex];
            return d.labelOffset || 4;
          },
          clamp: true, // 캔버스 영역 밖 잘림(clipping) 방지
          clip: false,
          font: { weight: "600", size: 10 },
          color: (ctx) => borderColors[ctx.dataIndex],
          formatter: (v) => {
            const parts = v.tag.split("/");
            const shortName = parts[parts.length - 1];
            if (v.isCapped) return `▲${shortName} (${v.realY}h)`;
            return shortName;
          }
        }
      },
      scales: {
        x: {
          min: 0,
          max: Math.max(...bubbleData.map(d => d.x), 75) + 6,
          title: { display: true, text: "재통화율 (%) ➔", font: { size: 11, weight: "bold" }, color: "#64748b" },
          grid: { color: "rgba(0,0,0,.06)" },
          ticks: { font: { size: 10 }, callback: (v) => `${v}%` }
        },
        y: {
          beginAtZero: true,
          max: effectiveYMax,
          title: {
            display: true,
            text: isFocusScale ? "평균 해결 리드타임 (h, 72시간 집중뷰) ➔" : "평균 해결 리드타임 (시간) ➔",
            font: { size: 11, weight: "bold" },
            color: "#64748b"
          },
          grid: { color: "rgba(0,0,0,.06)" },
          ticks: {
            font: { size: 10 },
            callback: (v) => {
              const days = (v / 24).toFixed(1);
              return `${v}h (${days}일)`;
            }
          }
        }
      },
      responsive: true,
      maintainAspectRatio: false
    }
  });
}

function renderClaimCategoryBreakdown(categories) {
  const tbody = document.getElementById("claimCategoryBreakdownTable");
  if (!tbody || !categories) return;

  tbody.innerHTML = categories.map((c) => {
    let riskBadge = "";
    if (c.repeatRate >= 25 || c.avgLeadHours >= 24) {
      riskBadge = '<span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold bg-rose-100 text-rose-800 ring-1 ring-rose-600/20">🚨 고위험 병목</span>';
    } else if (c.repeatRate >= 15 || c.avgLeadHours >= 12) {
      riskBadge = '<span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold bg-amber-100 text-amber-800 ring-1 ring-amber-600/20">⚠️ 주의 관찰</span>';
    } else {
      riskBadge = '<span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-emerald-100 text-emerald-800 ring-1 ring-emerald-600/20">✅ 양호 (신속)</span>';
    }

    return `
      <tr class="hover:bg-zinc-50 transition">
        <td class="py-2.5 px-3 font-semibold text-zinc-900">${escapeHtml(c.category)}</td>
        <td class="py-2.5 px-3 text-right tnum font-bold text-zinc-900">${c.total.toLocaleString()}건</td>
        <td class="py-2.5 px-3 text-right tnum font-semibold text-rose-700">${c.repeatRate}%</td>
        <td class="py-2.5 px-3 text-right tnum font-semibold text-teal-800">${c.avgLeadHours}시간 (${c.avgLeadDays}일)</td>
        <td class="py-2.5 px-3 text-right tnum text-zinc-700">${c.avgCalls}회</td>
        <td class="py-2.5 px-3 text-right tnum text-zinc-600">${c.avgDurationMin}분</td>
        <td class="py-2.5 px-3 text-center">${riskBadge}</td>
      </tr>
    `;
  }).join("");
}

function renderClaimTable(claims) {
  const tbody = document.getElementById("claimDetailTableBody");
  const countBadge = document.getElementById("claimTableCountBadge");
  const paginationEl = document.getElementById("claimPagination");
  const activeBadge = document.getElementById("claimTableActiveFilterBadge");
  const resetBtn = document.getElementById("btnResetClaimTableFilters");
  if (!tbody) return;

  // Active filter badge text
  let activeFilters = [];
  if (claimQuadrantFilterVal !== "all") {
    const qNames = { "1": "🚨 1사분면(최우선)", "2": "⏱️ 2사분면(장기)", "3": "✅ 3사분면(신속)", "4": "🔁 4사분면(핑퐁)" };
    activeFilters.push(qNames[claimQuadrantFilterVal] || claimQuadrantFilterVal);
  }
  if (claimCategoryFilterVal !== "all") activeFilters.push(`분류: ${claimCategoryFilterVal}`);
  if (claimCallFilterVal !== "all") activeFilters.push(`통화: ${claimCallFilterVal}`);
  if (claimSearchTerm) activeFilters.push(`검색: "${claimSearchTerm}"`);

  if (activeBadge) {
    activeBadge.textContent = activeFilters.length ? activeFilters.join(" · ") : "전체 건";
    activeBadge.className = activeFilters.length
      ? "rounded bg-amber-50 px-2 py-0.5 text-[11px] font-bold text-amber-800 ring-1 ring-amber-600/30"
      : "rounded bg-zinc-100 px-2 py-0.5 text-[11px] font-semibold text-zinc-700 ring-1 ring-black/5";
  }
  if (resetBtn) {
    resetBtn.classList.toggle("hidden", activeFilters.length === 0);
  }

  // 필터링 적용
  let filtered = claims.filter(c => {
    // 1. 사분면 필터
    if (claimQuadrantFilterVal !== "all" && c.quadrant !== claimQuadrantFilterVal) return false;

    // 2. 통화 횟수 필터
    if (claimCallFilterVal === "1" && c.call_count !== 1) return false;
    if (claimCallFilterVal === "2-3" && (c.call_count < 2 || c.call_count > 3)) return false;
    if (claimCallFilterVal === "4+" && c.call_count < 4) return false;

    // 3. 카테고리 필터
    if (claimCategoryFilterVal !== "all") {
      if (claimCategoryFilterVal === "품질" && !c.category.includes("품질")) return false;
      if (claimCategoryFilterVal === "배송" && !c.category.includes("배송")) return false;
      if (claimCategoryFilterVal === "휴먼에러" && !c.category.includes("휴먼에러")) return false;
      if (claimCategoryFilterVal === "시스템" && !c.category.includes("시스템")) return false;
    }

    // 4. 검색어 필터
    if (claimSearchTerm) {
      const q = claimSearchTerm.toLowerCase();
      const match = (c.cust && c.cust.toLowerCase().includes(q)) ||
                    (c.phone && c.phone.includes(q)) ||
                    (c.first_tag && c.first_tag.toLowerCase().includes(q)) ||
                    (c.agent && c.agent.toLowerCase().includes(q)) ||
                    (c.issue && c.issue.toLowerCase().includes(q)) ||
                    (c.act && c.act.toLowerCase().includes(q)) ||
                    (c.claim_id && c.claim_id.toLowerCase().includes(q));
      if (!match) return false;
    }
    return true;
  });

  if (countBadge) {
    countBadge.textContent = `${filtered.length.toLocaleString()}건`;
  }

  // 페이지네이션
  const totalPages = Math.max(1, Math.ceil(filtered.length / CLAIM_PAGE_SIZE));
  if (claimPage > totalPages) claimPage = 1;
  const startIdx = (claimPage - 1) * CLAIM_PAGE_SIZE;
  const pageItems = filtered.slice(startIdx, startIdx + CLAIM_PAGE_SIZE);

  if (pageItems.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" class="py-12 text-center text-zinc-400 font-medium">선택하신 조건에 해당하는 클레임 내역이 없습니다. (상단의 '필터 초기화 ↺' 버튼을 누르시면 전체 건을 보실 수 있습니다)</td></tr>`;
    if (paginationEl) paginationEl.innerHTML = "";
    return;
  }

  tbody.innerHTML = pageItems.map((c, idx) => {
    let callBadgeClass = "bg-teal-50 text-teal-700 ring-teal-600/20";
    if (c.call_count >= 4) callBadgeClass = "bg-rose-50 text-rose-700 ring-rose-600/20 font-bold";
    else if (c.call_count >= 2) callBadgeClass = "bg-amber-50 text-amber-700 ring-amber-600/20 font-semibold";

    let leadBadge = "";
    if (c.lead_time_hours <= 24.0) {
      leadBadge = `<span class="inline-flex items-center rounded bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-800 ring-1 ring-inset ring-emerald-600/20" title="${c.lead_time_hours}시간 (${c.lead_time_days}일)">${c.lead_time_hours}h <span class="text-[10px] text-zinc-500 font-normal ml-0.5">(${c.lead_time_days}일)</span></span>`;
    } else {
      leadBadge = `<span class="inline-flex items-center rounded bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-800 ring-1 ring-inset ring-amber-600/20" title="${c.lead_time_hours}시간 (${c.lead_time_days}일)">${c.lead_time_hours}h <span class="text-[10px] text-zinc-500 font-normal ml-0.5">(${c.lead_time_days}일)</span></span>`;
    }

    const issueSnippet = (c.issue || "-").replace(/\n/g, " ");
    const actSnippet = (c.act || "-").replace(/\n/g, " ");

    const timelineHtml = c.calls.map((call, cIdx) => {
      const durSec = call.talk || 0;
      const durStr = `${Math.floor(durSec / 60)}분 ${durSec % 60}초`;
      const isOut = call.dir === "outbound";
      return `
        <div class="flex items-start gap-2.5 text-xs py-1.5 border-l-2 ${cIdx === 0 ? 'border-teal-600' : 'border-amber-500'} pl-3 ml-2">
          <div class="font-bold min-w-[55px] ${cIdx === 0 ? 'text-teal-700' : 'text-amber-700'}">${cIdx + 1}차 ${isOut ? '발신(OUT)' : '수신(IN)'}</div>
          <div class="text-zinc-500 font-mono min-w-[130px]">${call.time || "-"}</div>
          <div class="font-medium text-zinc-700 min-w-[70px]">${escapeHtml(call.agent || "-")}</div>
          <div class="text-zinc-600 min-w-[65px]">${durStr}</div>
          <div class="text-zinc-600 flex-1">
            <span class="text-zinc-400 font-medium">문의:</span> ${escapeHtml((call.issue || "-").replace(/\n/g, " "))}
            <span class="text-teal-600 font-medium ml-2">조치:</span> ${escapeHtml((call.act || "-").replace(/\n/g, " "))}
          </div>
        </div>
      `;
    }).join("");

    return `
      <tr class="hover:bg-zinc-50/80 transition cursor-pointer" onclick="toggleClaimRow('${c.claim_id}')">
        <td class="py-2.5 px-3 font-mono text-[11px] text-zinc-500">
          <div class="flex items-center gap-1">
            <span id="chevron-${c.claim_id}" class="text-[10px] text-zinc-400 transition-transform">▶</span>
            <span>${c.claim_id}</span>
          </div>
        </td>
        <td class="py-2.5 px-3 font-medium text-zinc-900">
          <div>${escapeHtml(c.cust)}</div>
          <div class="text-[10px] text-zinc-400 font-mono">${escapeHtml(c.phone)}</div>
        </td>
        <td class="py-2.5 px-3 text-[11px] text-zinc-600 whitespace-nowrap">${c.first_time || "-"}</td>
        <td class="py-2.5 px-3 text-[11px] text-zinc-600 whitespace-nowrap">${c.last_time || "-"}</td>
        <td class="py-2.5 px-3 whitespace-nowrap">${leadBadge}</td>
        <td class="py-2.5 px-3 text-center">
          <span class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] ring-1 ring-inset ${callBadgeClass}">
            ${c.call_count}회
          </span>
        </td>
        <td class="py-2.5 px-3 text-right font-medium text-zinc-800 tnum whitespace-nowrap">
          ${c.total_call_duration_str}
        </td>
        <td class="py-2.5 px-3 text-[11px] text-zinc-700 max-w-[150px] truncate" title="${escapeHtml(c.first_tag)}">
          ${escapeHtml(c.first_tag || "-")}
        </td>
        <td class="py-2.5 px-3 text-[11px] text-zinc-600 whitespace-nowrap">${escapeHtml(c.agent || "-")}</td>
        <td class="py-2.5 px-3 text-[11px] text-zinc-500 max-w-[260px]">
          <div class="truncate text-zinc-800" title="${escapeHtml(issueSnippet)}"><span class="font-medium text-zinc-400">Q:</span> ${escapeHtml(issueSnippet)}</div>
          <div class="truncate text-zinc-500 text-[10px]" title="${escapeHtml(actSnippet)}"><span class="font-medium text-teal-600">A:</span> ${escapeHtml(actSnippet)}</div>
        </td>
      </tr>
      <tr id="timeline-${c.claim_id}" class="hidden bg-zinc-50/70">
        <td colspan="10" class="p-3 border-y border-teal-200/50">
          <div class="rounded-lg bg-white p-3 ring-1 ring-black/5">
            <div class="text-xs font-bold text-zinc-800 mb-2 flex items-center justify-between">
              <span>📞 통화 여정 타임라인 (총 ${c.call_count}회 통화 · 소요시간 ${c.lead_time_hours}시간)</span>
              <span class="text-[11px] text-zinc-400 font-normal">고객: ${escapeHtml(c.cust)} (${escapeHtml(c.phone)})</span>
            </div>
            <div class="space-y-1">
              ${timelineHtml}
            </div>
          </div>
        </td>
      </tr>
    `;
  }).join("");

  // Pagination buttons
  if (paginationEl) {
    paginationEl.innerHTML = `
      <div>
        전체 <span class="font-semibold text-zinc-800">${filtered.length.toLocaleString()}</span>건 중 
        <span class="font-semibold text-zinc-800">${startIdx + 1}</span>~<span class="font-semibold text-zinc-800">${Math.min(filtered.length, startIdx + CLAIM_PAGE_SIZE)}</span>건 표시 (페이지 ${claimPage}/${totalPages})
      </div>
      <div class="flex items-center gap-1.5">
        <button id="btnClaimPrevPage" type="button" class="rounded border border-black/10 bg-white px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50 disabled:opacity-40 cursor-pointer" ${claimPage <= 1 ? "disabled" : ""}>이전</button>
        <button id="btnClaimNextPage" type="button" class="rounded border border-black/10 bg-white px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50 disabled:opacity-40 cursor-pointer" ${claimPage >= totalPages ? "disabled" : ""}>다음</button>
      </div>
    `;

    const btnPrev = document.getElementById("btnClaimPrevPage");
    if (btnPrev) {
      btnPrev.addEventListener("click", () => {
        if (claimPage > 1) {
          claimPage--;
          renderClaimTable(claims);
        }
      });
    }

    const btnNext = document.getElementById("btnClaimNextPage");
    if (btnNext) {
      btnNext.addEventListener("click", () => {
        if (claimPage < totalPages) {
          claimPage++;
          renderClaimTable(claims);
        }
      });
    }
  }
}

function toggleClaimRow(claimId) {
  const row = document.getElementById(`timeline-${claimId}`);
  const chevron = document.getElementById(`chevron-${claimId}`);
  if (!row) return;

  if (row.classList.contains("hidden")) {
    row.classList.remove("hidden");
    if (chevron) chevron.style.transform = "rotate(90deg)";
  } else {
    row.classList.add("hidden");
    if (chevron) chevron.style.transform = "rotate(0deg)";
  }
}

async function exportClaimAnalysisToExcel() {
  const period = E.getPeriod();
  const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope, claimWindowDays);
  const claims = res.claims;

  if (!claims || claims.length === 0) {
    alert("다운로드할 클레임 데이터가 없습니다.");
    return;
  }

  if (typeof ExcelJS === "undefined") {
    alert("ExcelJS 라이브러리를 불러오는 중입니다. 잠시 후 다시 시도해 주세요.");
    return;
  }

  const wb = new ExcelJS.Workbook();
  wb.creator = "CX Dashboard";
  wb.created = new Date();

  // Sheet 1: 클레임 리드타임 상세 원장
  const ws = wb.addWorksheet("클레임_리드타임_원장");
  ws.columns = [
    { header: "Claim ID", key: "claim_id", width: 22 },
    { header: "사분면", key: "quadrant_name", width: 18 },
    { header: "클레임 유형", key: "category", width: 26 },
    { header: "고객명", key: "cust", width: 14 },
    { header: "연락처", key: "phone", width: 16 },
    { header: "최초 클레임 일시", key: "first_time", width: 20 },
    { header: "최종 통화 일시", key: "last_time", width: 20 },
    { header: "소요 리드타임(시간)", key: "lead_time_hours", width: 18 },
    { header: "소요 리드타임(일)", key: "lead_time_days", width: 16 },
    { header: "총 통화횟수(회)", key: "call_count", width: 14 },
    { header: "총 통화시간(분)", key: "total_call_duration", width: 16 },
    { header: "세부 태그", key: "first_tag", width: 28 },
    { header: "담당 상담사", key: "agent", width: 14 },
    { header: "고객 문의내용", key: "issue", width: 36 },
    { header: "상담원 조치내용", key: "act", width: 36 }
  ];

  // Header style
  ws.getRow(1).font = { bold: true, color: { argb: "FFFFFFFF" } };
  ws.getRow(1).fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF0F766E" } };
  ws.getRow(1).alignment = { vertical: "middle", horizontal: "center" };

  const qNames = { "1": "1사분면(최우선개선)", "2": "2사분면(장기검수)", "3": "3사분면(빠른해결)", "4": "4사분면(단기핑퐁)" };

  claims.forEach((c) => {
    ws.addRow({
      claim_id: c.claim_id,
      quadrant_name: qNames[c.quadrant] || "3사분면(빠른해결)",
      category: c.category,
      cust: c.cust,
      phone: c.phone,
      first_time: c.first_time,
      last_time: c.last_time,
      lead_time_hours: c.lead_time_hours,
      lead_time_days: c.lead_time_days,
      call_count: c.call_count,
      total_call_duration: c.total_call_duration,
      first_tag: c.first_tag,
      agent: c.agent,
      issue: c.issue,
      act: c.act
    });
  });

  const pLabel = period && period.key ? period.key : "ALL";
  const fileName = `클레임_처리_리드타임_통화분석_${pLabel}.xlsx`;

  const buf = await wb.xlsx.writeBuffer();
  const blob = new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
function renderCompensation() {
  const period = E.getPeriod();
  if (!period) return;
  const prevP = E.prevPeriod();
  const year = period.key.slice(0, 4);

  // Determine buckets based on E.state.mode
  const bucketList = getCompBucketList(period, year);

  let matrixTitle = "";
  let matrixSubtitle = "";
  let totalColLabel = "합계";
  let chartTitle = "";
  let chartSubtitle = "";
  let chartBadge = "";

  if (E.state.mode === "weekly") {
    matrixTitle = "최근 8주간 · 제품별 품질보상/교환 추이 매트릭스";
    matrixSubtitle = `주차별 교환·보상 발생 현황 (실제품 규격별, 선택: ${formatPeriodDisplayLabel(period, "weekly")})`;
    totalColLabel = "최근 8주 합계";
    chartTitle = "최근 8주간 품질보상/교환 발생 추이";
    chartSubtitle = "주차별 품질보상 건수";
    chartBadge = "주간 추이";
  } else if (E.state.mode === "monthly") {
    matrixTitle = `${year}년 월별 · 제품별 보상/교환 피벗 매트릭스`;
    matrixSubtitle = `${year}년 월간 품질 교환·보상 건수 히트맵 (실제품 규격별, 선택: ${period.label})`;
    totalColLabel = `${year}년 누적 합계`;
    chartTitle = `${year}년 월별 품질보상/교환 처리 추이`;
    chartSubtitle = `${year}년 월간 발생량`;
    chartBadge = "월간 추이";
  } else if (E.state.mode === "quarterly") {
    matrixTitle = `${year}년 분기별 · 제품별 보상/교환 피벗 매트릭스`;
    matrixSubtitle = `${year}년 분기별 교환·보상 발생 현황 (실제품 규격별, 선택: ${period.label})`;
    totalColLabel = `${year}년 누적 합계`;
    chartTitle = `${year}년 분기별 품질보상/교환 처리 추이`;
    chartSubtitle = `${year}년 분기별 발생량`;
    chartBadge = "분기 추이";
  } else {
    matrixTitle = `${period.label} 연간 · 제품별 보상/교환 피벗 매트릭스`;
    matrixSubtitle = `${period.label} 월별 품질 교환·보상 누적 히트맵 (실제품 규격별)`;
    totalColLabel = `${year}년 연간 합계`;
    chartTitle = `${period.label} 월별 품질보상 발생 추이`;
    chartSubtitle = `${period.label} 월간 발생량`;
    chartBadge = "연간 추이";
  }

  // 1. Determine KPI Target Chats dynamically based on user's selected area!
  // If compSelectedBucketKey === "all" -> entire bucketList sum!
  // If compSelectedBucketKey matches a bucket -> that bucket's chats!
  // Otherwise default to current period.key!
  let activeBucketKey = compSelectedBucketKey;
  if (!activeBucketKey || (activeBucketKey !== "all" && !bucketList.some((b) => b.key === activeBucketKey))) {
    activeBucketKey = period.key;
  }

  let kpiChats = [];
  let kpiLabel = "";
  let kpiPrevChats = null;

  if (activeBucketKey === "all") {
    kpiChats = bucketList.flatMap((b) => b.chats);
    kpiLabel = `${totalColLabel} 누적`;
    kpiPrevChats = null;
  } else {
    const selBucket = bucketList.find((b) => b.key === activeBucketKey);
    if (selBucket) {
      kpiChats = selBucket.chats;
      kpiLabel = selBucket.label;
      const bIdx = bucketList.findIndex((b) => b.key === activeBucketKey);
      if (bIdx > 0) {
        kpiPrevChats = bucketList[bIdx - 1].chats;
      } else if (prevP) {
        kpiPrevChats = E.rawChats(prevP).filter(isCompChat);
      }
    } else {
      kpiChats = E.rawChats(period).filter(isCompChat);
      kpiLabel = formatPeriodDisplayLabel(period, E.state.mode);
      kpiPrevChats = prevP ? E.rawChats(prevP).filter(isCompChat) : null;
    }
  }

  const curTotal = kpiChats.length;
  const prevTotal = kpiPrevChats ? kpiPrevChats.length : null;

  const byAction = { "교환": 0, "환불": 0, "회수": 0, "보상": 0 };
  kpiChats.forEach((c) => {
    const actType = getCompActionType(c.act);
    byAction[actType] = (byAction[actType] || 0) + 1;
  });

  const exchShare = curTotal > 0 ? ((byAction["교환"] / curTotal) * 100).toFixed(1) : "0.0";
  const recallShare = curTotal > 0 ? ((byAction["회수"] / curTotal) * 100).toFixed(1) : "0.0";

  // Top actual product for current selected target chats
  const famCounts = {};
  kpiChats.forEach((c) => {
    const fam = getActualProductName(c.prod);
    famCounts[fam] = (famCounts[fam] || 0) + 1;
  });
  const topFam = Object.entries(famCounts).sort((a, b) => b[1] - a[1])[0] || ["–", 0];

  // Render KPI cards
  const kpiEl = document.getElementById("compKpiRow");
  if (kpiEl) {
    const topProdDisplay = topFam[0] !== "–"
      ? `<span class="text-base font-semibold truncate max-w-full inline-block" title="${topFam[0]} (${Number(topFam[1] || 0).toLocaleString()}건)">${topFam[0]}</span> <span class="text-xs font-normal text-zinc-500 whitespace-nowrap">(${Number(topFam[1] || 0).toLocaleString()}건)</span>`
      : "–";

    kpiEl.innerHTML =
      kpiCard("품질보상 총 접수", `${curTotal.toLocaleString()}건`, prevTotal != null ? E.delta(curTotal, prevTotal) : null, {
        inverse: true,
        subText: `${kpiLabel} 기준`
      }) +
      kpiCard("최다 보상 제품", topProdDisplay, null, {
        subText: `${kpiLabel} 접수 1위 (실제품/규격)`
      }) +
      kpiCard("맞교환 / 재출고 비중", `${exchShare}%`, null, {
        subText: `총 ${byAction["교환"].toLocaleString()}건 교환 처리`
      }) +
      kpiCard("회수 / 품질검수", `${byAction["회수"].toLocaleString()}건`, null, {
        subText: `전체 대비 ${recallShare}% 비중`
      });
  }

  // Populate #compMonthFilter dropdown with months of current year
  const mSelect = document.getElementById("compMonthFilter");
  if (mSelect) {
    const yearMonths = E.MONTHS.filter((m) => m.key.startsWith(year));
    let optHtml = `<option value="all">전체 기간 (${year}년)</option>`;
    yearMonths.forEach((m) => {
      const mLabel = m.label.replace(`${year}년 `, "");
      optHtml += `<option value="${m.key}">${year}년 ${mLabel}</option>`;
    });
    mSelect.innerHTML = optHtml;
    if (compMonthFilterVal && (compMonthFilterVal === "all" || yearMonths.some((m) => m.key === compMonthFilterVal))) {
      mSelect.value = compMonthFilterVal;
    } else {
      compMonthFilterVal = "all";
      mSelect.value = "all";
    }
  }

  // Update export button text
  const exportPeriodBtnText = document.getElementById("compExportPeriodBtnText");
  if (exportPeriodBtnText) {
    exportPeriodBtnText.textContent = `${kpiLabel} 보상내역서 (Excel)`;
  }

  // Update matrix container header texts
  const mTitleEl = document.getElementById("compMatrixTitle");
  if (mTitleEl) mTitleEl.textContent = matrixTitle;
  const mSubEl = document.getElementById("compMatrixSubtitle");
  if (mSubEl) {
    // 조잡한 한글 설명 제거하여 깔끔하게 노출
    mSubEl.textContent = matrixSubtitle;
  }
  const pBadgeEl = document.getElementById("compPeriodBadge");
  if (pBadgeEl) pBadgeEl.textContent = `${kpiLabel} 선택됨`;

  const tTitleEl = document.getElementById("compTrendTitle");
  if (tTitleEl) tTitleEl.textContent = chartTitle;
  const tSubEl = document.getElementById("compTrendSubtitle");
  if (tSubEl) tSubEl.textContent = chartSubtitle;
  const tBadgeEl = document.getElementById("compTrendBadge");
  if (tBadgeEl) tBadgeEl.textContent = chartBadge;

  // 2. Render Matrix
  renderCompMatrix(bucketList, totalColLabel, activeBucketKey);

  // 3. Render Trend Chart
  barChart("compMonthlyChart", bucketList.map((b) => b.label), bucketList.map((b) => b.chats.length), {
    colors: "#0f766e",
    horizontal: false
  });

  // 4. Detail target chats
  const targetDetailChats = getCompTargetChats(bucketList);

  // 5. 보상 사유별 분포
  const reasonCounts = E.groupCount(targetDetailChats, "sub").slice(0, 6);
  const reasonTotalEl = document.getElementById("compReasonTotal");
  if (reasonTotalEl) {
    reasonTotalEl.textContent = `총 ${targetDetailChats.length.toLocaleString()}건`;
  }
  doughnutChart("compReasonChart", reasonCounts.map((x) => x[0]), reasonCounts.map((x) => x[1]));

  // 6. 실시간 보상 접수 상세 테이블
  renderCompDetailTable(targetDetailChats);
}

function renderCompMatrix(bucketList, totalColLabel, activeKey) {
  const thead = document.getElementById("compMatrixThead");
  const tbody = document.getElementById("compMatrixTableBody");
  if (!tbody || !bucketList || !bucketList.length) return;

  // 1. Sync & populate sort select dropdown dynamically
  const sortSelect = document.getElementById("compMatrixSortSelect");
  if (sortSelect) {
    const curVal = `${compMatrixSortKey}_${compMatrixSortOrder}`;
    let optHtml = `
      <option value="total_desc">전체 합계 많은순 (▼)</option>
      <option value="total_asc">전체 합계 적은순 (▲)</option>
      <option value="name_asc">제품명 가나다순 (ㄱ→ㅎ ▲)</option>
      <option value="name_desc">제품명 역순 (ㅎ→ㄱ ▼)</option>
    `;
    if (bucketList && bucketList.length) {
      optHtml += `<optgroup label="월별 / 주차별 건수 정렬">`;
      bucketList.forEach((b) => {
        optHtml += `<option value="${b.key}_desc">${b.label} 건수 많은순 (▼)</option>`;
        optHtml += `<option value="${b.key}_asc">${b.label} 건수 적은순 (▲)</option>`;
      });
      optHtml += `</optgroup>`;
    }
    sortSelect.innerHTML = optHtml;

    const validVals = Array.from(sortSelect.options).map((o) => o.value);
    if (validVals.includes(curVal)) {
      sortSelect.value = curVal;
    } else {
      compMatrixSortKey = "total";
      compMatrixSortOrder = "desc";
      sortSelect.value = "total_desc";
    }
  }

  // 2. Render <thead> dynamically with simplified ▼▲ sort indicators and compact padding
  if (thead) {
    const isSortName = compMatrixSortKey === "name";
    const isSortTotal = compMatrixSortKey === "total";

    const nameSortIndicator = isSortName
      ? `<span class="inline-block text-teal-700 font-bold ml-1 text-xs">${compMatrixSortOrder === "asc" ? "▲" : "▼"}</span>`
      : `<span class="inline-block text-zinc-300 ml-1 text-[11px]">⇅</span>`;

    const totalSortIndicator = isSortTotal
      ? `<span class="inline-block text-teal-700 font-bold ml-1 text-xs">${compMatrixSortOrder === "desc" ? "▼" : "▲"}</span>`
      : `<span class="inline-block text-zinc-300 ml-1 text-[11px]">⇅</span>`;

    thead.innerHTML = `<tr>
      <th id="compSortThName" class="py-2 px-2.5 font-semibold min-w-[175px] max-w-[205px] bg-zinc-50 sticky left-0 z-10 shadow-[1px_0_0_0_rgba(0,0,0,0.05)] text-zinc-800 cursor-pointer select-none hover:bg-zinc-100 transition" title="클릭 시 제품명 정렬 (▲ 오름차순 / ▼ 내림차순)">
        <div class="flex items-center justify-between gap-1">
          <span class="truncate">실제품명 (규격)</span>
          ${nameSortIndicator}
        </div>
      </th>
      ${bucketList.map((b) => {
        const isSortThisBucket = compMatrixSortKey === b.key;
        const isSelected = b.key === activeKey || b.key === compMonthFilterVal;

        let sortArrow = "";
        if (isSortThisBucket) {
          sortArrow = `<span class="inline-block text-[11px] ml-0.5 font-bold text-amber-300">${compMatrixSortOrder === 'desc' ? '▼' : '▲'}</span>`;
        }

        let thClass = "py-2 px-2 font-medium text-right min-w-[55px] text-zinc-600 hover:bg-teal-100/70 cursor-pointer select-none transition";
        if (isSortThisBucket) {
          thClass = "py-2 px-2 font-bold text-right min-w-[58px] bg-teal-800 text-white shadow-md ring-2 ring-inset ring-amber-400 cursor-pointer select-none";
        } else if (isSelected) {
          thClass = "py-2 px-2 font-bold text-right min-w-[55px] bg-teal-600 text-white shadow-sm ring-1 ring-inset ring-teal-700 cursor-pointer select-none";
        }

        const tooltip = `클릭 시 '${b.label}' 기준 KPI 갱신 및 건수 ${compMatrixSortOrder === 'desc' ? '많은순' : '적은순'} 정렬`;

        return `<th class="${thClass}" data-bucket="${b.key}" title="${tooltip}">
          <div class="flex items-center justify-end gap-0.5">
            <span class="truncate">${b.label}</span>
            ${sortArrow}
          </div>
        </th>`;
      }).join("")}
      <th id="compSortThTotal" class="py-2 px-2.5 font-bold text-right min-w-[100px] ${activeKey === 'all' ? 'bg-teal-700 text-white' : 'bg-zinc-100 text-teal-950'} shadow-[inset_1px_0_0_rgba(0,0,0,0.05)] cursor-pointer select-none hover:bg-zinc-200 transition" title="클릭 시 전체 누적 KPI 갱신 및 총 건수 정렬 (▼ 많은순 / ▲ 적은순)">
        <div class="flex items-center justify-end gap-1">
          <span class="truncate">${totalColLabel}</span>
          ${totalSortIndicator}
        </div>
      </th>
    </tr>`;

    // 제품명 정렬 헤더 클릭
    const thName = document.getElementById("compSortThName");
    if (thName) {
      thName.addEventListener("click", () => {
        if (compMatrixSortKey === "name") {
          compMatrixSortOrder = (compMatrixSortOrder === "asc" ? "desc" : "asc");
        } else {
          compMatrixSortKey = "name";
          compMatrixSortOrder = "asc";
        }
        renderCompensation();
      });
    }

    // 전체 합계 건수 정렬 및 전체 누적 KPI 연동 클릭
    const thTotal = document.getElementById("compSortThTotal");
    if (thTotal) {
      thTotal.addEventListener("click", () => {
        compSelectedBucketKey = "all";
        compMonthFilterVal = "all";
        if (compMatrixSortKey === "total") {
          compMatrixSortOrder = (compMatrixSortOrder === "desc" ? "asc" : "desc");
        } else {
          compMatrixSortKey = "total";
          compMatrixSortOrder = "desc";
        }
        renderCompensation();
      });
    }

    // 각 월/주차 헤더 클릭: 해당 기간 기준 KPI 갱신 & 건수 정렬 & 상세 필터 동시 적용!
    thead.querySelectorAll("th[data-bucket]").forEach((th) => {
      th.addEventListener("click", () => {
        const bKey = th.getAttribute("data-bucket");
        compSelectedBucketKey = bKey;
        compMonthFilterVal = bKey;
        if (compMatrixSortKey === bKey) {
          compMatrixSortOrder = (compMatrixSortOrder === "desc" ? "asc" : "desc");
        } else {
          compMatrixSortKey = bKey;
          compMatrixSortOrder = "desc";
        }
        renderCompensation();
      });
    });
  }

  // 3. Aggregate counts by family and bucket
  const matrix = {};
  const bucketTotals = Array(bucketList.length).fill(0);
  let grandTotal = 0;

  bucketList.forEach((b, bIdx) => {
    b.chats.forEach((c) => {
      const fam = getActualProductName(c.prod);
      matrix[fam] = matrix[fam] || {};
      matrix[fam][b.key] = (matrix[fam][b.key] || 0) + 1;
      matrix[fam]["총계"] = (matrix[fam]["총계"] || 0) + 1;
      bucketTotals[bIdx]++;
      grandTotal++;
    });
  });

  // 4. Sort families by compMatrixSortKey & compMatrixSortOrder
  const sortedFamilies = Object.entries(matrix).sort((a, b) => {
    if (compMatrixSortKey === "name") {
      const cmp = a[0].localeCompare(b[0], "ko");
      return compMatrixSortOrder === "asc" ? cmp : -cmp;
    } else if (compMatrixSortKey === "total") {
      const valA = a[1]["총계"] || 0;
      const valB = b[1]["총계"] || 0;
      if (valA !== valB) {
        return compMatrixSortOrder === "asc" ? valA - valB : valB - valA;
      }
      return a[0].localeCompare(b[0], "ko");
    } else {
      // 월단위 / 주차별 건수 정렬
      const valA = (a[1][compMatrixSortKey]) || 0;
      const valB = (b[1][compMatrixSortKey]) || 0;
      if (valA !== valB) {
        return compMatrixSortOrder === "asc" ? valA - valB : valB - valA;
      }
      const totA = a[1]["총계"] || 0;
      const totB = b[1]["총계"] || 0;
      if (totA !== totB) return totB - totA;
      return a[0].localeCompare(b[0], "ko");
    }
  });

  function cellStyle(val) {
    if (!val || val === 0) return "text-zinc-300 font-light";
    if (val < 10) return "text-zinc-700 bg-teal-50/40";
    if (val < 30) return "text-teal-900 bg-teal-100/70 font-medium";
    return "text-teal-950 bg-teal-200/90 font-bold";
  }

  // 5. Render rows with reduced padding on product name and compact cell sizing
  const rowsHtml = sortedFamilies.map(([fam, data]) => {
    const cells = bucketList.map((b) => {
      const v = data[b.key] || 0;
      const isSortThisBucket = compMatrixSortKey === b.key;
      const isSelected = b.key === activeKey || b.key === compMonthFilterVal;

      let highlight = "";
      if (isSortThisBucket) {
        highlight = "ring-2 ring-inset ring-amber-400 bg-amber-50/70 font-bold ";
      } else if (isSelected) {
        highlight = "ring-2 ring-inset ring-teal-600 bg-teal-50/90 font-bold ";
      }
      return `<td class="py-1.5 px-2 text-right tnum ${highlight}${cellStyle(v)}">${v > 0 ? v.toLocaleString() : "–"}</td>`;
    }).join("");

    const isTotalSorted = compMatrixSortKey === "total";
    const totalCellHighlight = isTotalSorted ? "ring-2 ring-inset ring-teal-600 font-extrabold " : "";

    return `<tr class="hover:bg-zinc-50/50">
      <td class="py-1.5 px-2.5 font-medium text-zinc-900 bg-white sticky left-0 z-10 shadow-[1px_0_0_0_rgba(0,0,0,0.05)] whitespace-nowrap max-w-[205px] truncate text-[11px]" title="${fam}">${fam}</td>
      ${cells}
      <td class="py-1.5 px-2.5 text-right tnum font-bold text-teal-950 bg-zinc-50 shadow-[inset_1px_0_0_rgba(0,0,0,0.05)] ${totalCellHighlight}">${(data["총계"] || 0).toLocaleString()}</td>
    </tr>`;
  }).join("");

  // 6. Footer row
  const footerHtml = `<tr class="bg-zinc-100 font-bold border-t-2 border-black/10">
    <td class="py-2 px-2.5 text-zinc-900 bg-zinc-100 sticky left-0 z-10 shadow-[1px_0_0_0_rgba(0,0,0,0.05)] font-bold text-xs">합계</td>
    ${bucketTotals.map((t, idx) => {
      const bKey = bucketList[idx].key;
      const isSortThisBucket = compMatrixSortKey === bKey;
      const isSelected = bKey === activeKey || bKey === compMonthFilterVal;

      let footerCellClass = "text-zinc-800 font-semibold";
      if (isSortThisBucket) {
        footerCellClass = "text-amber-950 bg-amber-200/90 font-bold ring-2 ring-inset ring-amber-400";
      } else if (isSelected) {
        footerCellClass = "text-teal-950 bg-teal-200/80 font-bold ring-2 ring-inset ring-teal-600";
      }
      return `<td class="py-2 px-2 text-right tnum ${footerCellClass}">${t.toLocaleString()}</td>`;
    }).join("")}
    <td class="py-2 px-2.5 text-right tnum font-extrabold text-teal-950 bg-zinc-200 shadow-[inset_1px_0_0_rgba(0,0,0,0.05)]">${grandTotal.toLocaleString()}</td>
  </tr>`;

  tbody.innerHTML = rowsHtml + footerHtml;
}

// =============================================================
// 보상 내역 수기 예외 관리 (제외 / 수기 추가) 오버라이드 시스템
// =============================================================
window.COMP_OVERRIDES = { excluded_ids: [], excluded_reasons: {}, manual_additions: [] };
let compOverridesLoaded = false;

async function ensureCompOverridesLoaded() {
  if (compOverridesLoaded) return;
  try {
    const res = await fetch("/api/compensation_overrides");
    if (res.ok) {
      window.COMP_OVERRIDES = await res.json();
      if (!Array.isArray(window.COMP_OVERRIDES.excluded_ids)) window.COMP_OVERRIDES.excluded_ids = [];
      if (!window.COMP_OVERRIDES.excluded_reasons || typeof window.COMP_OVERRIDES.excluded_reasons !== "object") {
        window.COMP_OVERRIDES.excluded_reasons = {};
      }
      if (!Array.isArray(window.COMP_OVERRIDES.manual_additions)) window.COMP_OVERRIDES.manual_additions = [];
      compOverridesLoaded = true;
    }
  } catch (e) {
    console.warn("Failed to fetch compensation overrides:", e);
  }
}

async function saveCompOverridesToServer() {
  try {
    await fetch("/api/compensation_overrides", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(window.COMP_OVERRIDES)
    });
  } catch (e) {
    console.error("Failed to save compensation overrides:", e);
  }
}

function refreshCompensationViews() {
  if (typeof renderCompensation === "function") {
    renderCompensation();
  } else if (typeof renderCompDetailTable === "function" && typeof getCompTargetChats === "function") {
    renderCompDetailTable(getCompTargetChats());
  }
}

window.toggleCompOverride = async function(chatId, isRestore) {
  if (typeof window.isUserAdmin === "function" && !window.isUserAdmin()) {
    alert("보상내역 제외 및 복원은 관리자(admin) 계정만 가능합니다.");
    return;
  }
  const idStr = String(chatId);
  if (isRestore) {
    // 다시 추가 (복원)
    window.COMP_OVERRIDES.excluded_ids = window.COMP_OVERRIDES.excluded_ids.filter((x) => x !== idStr);
    if (window.COMP_OVERRIDES.excluded_reasons) {
      delete window.COMP_OVERRIDES.excluded_reasons[idStr];
    }
    await saveCompOverridesToServer();
    refreshCompensationViews();
    alert("✓ 해당 건이 보상 신청 목록에 다시 추가(복원)되었습니다.");
  } else {
    // 제외 사유 입력 대화상자
    const reason = prompt(
      "보상 제외 사유를 입력해주세요:\n(예: 단순 변심 교환, 고객 귀책 파손, 중복 접수, 수기 확인 정상품 등)",
      "단순 변심 교환"
    );
    if (reason === null) return; // 취소 클릭
    const cleanReason = reason.trim() || "관리자 수기 제외";

    if (!window.COMP_OVERRIDES.excluded_ids.includes(idStr)) {
      window.COMP_OVERRIDES.excluded_ids.push(idStr);
    }
    if (!window.COMP_OVERRIDES.excluded_reasons) {
      window.COMP_OVERRIDES.excluded_reasons = {};
    }
    window.COMP_OVERRIDES.excluded_reasons[idStr] = {
      reason: cleanReason,
      date: new Date().toISOString().slice(0, 10)
    };

    await saveCompOverridesToServer();
    refreshCompensationViews();
    alert(`✓ 보상 제외 처리되었습니다.\n- 제외 사유: ${cleanReason}\n- 언제든 [보상 다시 추가] 버튼을 눌러 복원하실 수 있습니다.`);
  }
};

window.deleteManualComp = async function(manualId) {
  if (typeof window.isUserAdmin === "function" && !window.isUserAdmin()) {
    alert("수기 보상 건 삭제는 관리자(cx) 계정만 가능합니다.");
    return;
  }
  if (!confirm("해당 수기 등록 보상 건을 삭제하시겠습니까?")) return;
  window.COMP_OVERRIDES.manual_additions = window.COMP_OVERRIDES.manual_additions.filter((x) => x.id !== manualId);
  await saveCompOverridesToServer();
  refreshCompensationViews();
};

function renderCompDetailTable(chats) {
  const tbody = document.getElementById("compDetailTableBody");
  if (!tbody) return;

  // 비동기 오버라이드 데이터 보장
  if (!compOverridesLoaded) {
    ensureCompOverridesLoaded().then(() => renderCompDetailTable(chats));
  }

  // Sync compDetailSortSelect
  const sortSelect = document.getElementById("compDetailSortSelect");
  if (sortSelect) {
    sortSelect.value = `${compDetailSortKey}_${compDetailSortOrder}`;
  }

  // Update prod sort icon
  const prodIcon = document.getElementById("compDetailProdSortIcon");
  if (prodIcon) {
    if (compDetailSortKey === "prod") {
      prodIcon.className = "inline-flex items-center text-[10px] text-teal-700 bg-teal-50 px-1 py-0.5 rounded ring-1 ring-teal-600/30 font-bold ml-1";
      prodIcon.textContent = compDetailSortOrder === "asc" ? "▲ 가나다" : "▼ 역순";
    } else {
      prodIcon.className = "text-zinc-300 ml-1 text-xs";
      prodIcon.textContent = "⇅";
    }
  }

  const term = (compSearchTerm || "").trim().toLowerCase();
  const actFilter = compActionFilterVal || "all";

  // 수기 추가된 건들을 현재 뷰에 포함
  const period = typeof E !== "undefined" && E.getPeriod ? E.getPeriod() : null;
  const curWeekKey = period ? period.key : "";
  const manualList = (window.COMP_OVERRIDES.manual_additions || []).map((m) => ({
    id: m.id,
    is_manual: true,
    sub: m.issueType || "수기보상",
    prod: m.prod,
    cust: m.cust,
    mfg: m.mfg || "-",
    mall: m.mall || "수기등록",
    issue: m.issue || "수기 추가 보상 건",
    act: m.act || "보상 처리 완료",
    date: m.date || new Date().toISOString().slice(0, 10),
    time: m.date || ""
  }));

  const allList = [...manualList, ...chats];

  const excludedSet = new Set((window.COMP_OVERRIDES?.excluded_ids || []).map(String));

  let filtered = allList.filter((c) => {
    const cidStr = String(c.id);
    const isExcluded = excludedSet.has(cidStr);
    const actType = getCompActionType(c.act);

    if (actFilter === "comp_only") {
      if (isExcluded) return false;
    } else if (actFilter === "excluded_only") {
      if (!isExcluded) return false;
    } else if (actFilter !== "all" && actType !== actFilter) {
      return false;
    }

    if (!term) return true;
    return (
      (actType || "").toLowerCase().includes(term) ||
      (c.cust || "").toLowerCase().includes(term) ||
      (c.prod || "").toLowerCase().includes(term) ||
      (c.sub || "").toLowerCase().includes(term) ||
      (c.mfg || "").toLowerCase().includes(term) ||
      (c.mall || "").toLowerCase().includes(term) ||
      (c.issue || "").toLowerCase().includes(term) ||
      (c.act || "").toLowerCase().includes(term) ||
      (c.date || "").toLowerCase().includes(term)
    );
  });

  // Apply sorting
  filtered.sort((a, b) => {
    if (compDetailSortKey === "prod") {
      const nameA = getActualProductName(a.prod);
      const nameB = getActualProductName(b.prod);
      const cmp = nameA.localeCompare(nameB, "ko");
      return compDetailSortOrder === "asc" ? cmp : -cmp;
    } else {
      const timeA = a.date || a.time || "";
      const timeB = b.date || b.time || "";
      const cmp = timeA.localeCompare(timeB);
      return compDetailSortOrder === "asc" ? cmp : -cmp;
    }
  });

  if (!filtered.length) {
    const monthName = compMonthFilterVal !== "all" ? `선택 월 [${compMonthFilterVal}]` : "검색 조건";
    tbody.innerHTML = `<tr><td colspan="10" class="py-6 text-center text-zinc-400">${monthName}에 맞는 보상 처리 건이 없습니다.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.slice(0, 100).map((c) => {
    const cidStr = String(c.id);
    const isExcluded = excludedSet.has(cidStr);
    const isManual = Boolean(c.is_manual);
    const exInfo = window.COMP_OVERRIDES.excluded_reasons?.[cidStr];

    const actType = getCompActionType(c.act);
    let actBadge = '<span class="rounded bg-teal-100 px-1.5 py-0.5 text-[10px] font-semibold text-teal-800">교환</span>';
    if (isManual) {
      actBadge = '<span class="rounded bg-indigo-100 px-1.5 py-0.5 text-[10px] font-bold text-indigo-800">수기추가</span>';
    } else if (isExcluded) {
      actBadge = '<span class="rounded bg-zinc-200 px-1.5 py-0.5 text-[10px] font-semibold text-zinc-600 line-through">제외됨</span>';
    } else if (actType === "환불") {
      actBadge = '<span class="rounded bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold text-rose-800">환불</span>';
    } else if (actType === "회수") {
      actBadge = '<span class="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800">회수</span>';
    } else if (actType === "보상") {
      actBadge = '<span class="rounded bg-indigo-100 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-800">보상</span>';
    }

    let actionBtnHtml = "";
    if (isManual) {
      actionBtnHtml = `<button type="button" onclick="window.deleteManualComp('${c.id}')" class="rounded bg-zinc-100 px-2 py-1 text-[11px] font-semibold text-zinc-600 hover:bg-zinc-200 transition">삭제</button>`;
    } else if (isExcluded) {
      actionBtnHtml = `<button type="button" onclick="window.toggleCompOverride('${c.id}', true)" class="rounded bg-teal-50 px-2.5 py-1 text-[11px] font-bold text-teal-700 hover:bg-teal-100 ring-1 ring-teal-600/30 transition shadow-xs">+ 보상 다시 추가</button>`;
    } else {
      actionBtnHtml = `<button type="button" onclick="window.toggleCompOverride('${c.id}', false)" class="rounded bg-rose-50 px-2.5 py-1 text-[11px] font-semibold text-rose-700 hover:bg-rose-100 ring-1 ring-rose-200 transition">보상 제외</button>`;
    }

    const rowClass = isExcluded ? "bg-rose-50/25 opacity-60 text-zinc-400" : "hover:bg-zinc-50";
    const prodClass = isExcluded ? "line-through text-zinc-400 font-medium" : "font-medium text-zinc-900";
    const resolvedName = (c.cust && c.cust !== "고객" && c.cust !== "-" && c.cust !== "–")
      ? c.cust
      : (c.custName && c.custName !== "고객" && c.custName !== "-" && c.custName !== "–")
        ? c.custName
        : (c.name && c.name !== "고객" && c.name !== "-" && c.name !== "–")
          ? c.name
          : getChatCustomerName(c);
    const custName = (resolvedName || "고객").replace(/</g, "&lt;");
    const dateStr = c.date || (c.time ? c.time.slice(0, 10) : (c.managedAt ? c.managedAt.slice(0, 10) : "–"));

    const reasonTag = isExcluded && exInfo ? `<div class="mt-0.5 text-[10px] text-rose-600 font-medium bg-rose-50 px-1.5 py-0.5 rounded ring-1 ring-rose-200 inline-block" title="제외일자: ${exInfo.date}">제외사유: ${exInfo.reason}</div>` : "";

    return `<tr class="${rowClass}">
      <td class="py-2.5 px-2">${actBadge}</td>
      <td class="py-2.5 px-2 tnum font-medium text-zinc-600 whitespace-nowrap">${dateStr}</td>
      <td class="py-2.5 px-2 font-medium text-zinc-800">${c.sub || "–"}</td>
      <td class="py-2.5 px-3 ${prodClass}">
        <div>${getActualProductName(c.prod)}</div>
        ${reasonTag}
      </td>
      <td class="py-2.5 px-2 font-semibold text-zinc-800">${custName}</td>
      <td class="py-2.5 px-2 tnum text-zinc-500">${formatMfgDate(c.mfg)}</td>
      <td class="py-2.5 px-2 text-zinc-600">${c.mall || "–"}</td>
      <td class="py-2.5 px-4 text-zinc-800 break-words max-w-xs">${(c.issue || "–").replace(/</g, "&lt;")}</td>
      <td class="py-2.5 px-4 text-zinc-600 break-words max-w-xs">${(c.act || "–").replace(/</g, "&lt;")}</td>
      <td class="py-2.5 px-2 text-center whitespace-nowrap">${actionBtnHtml}</td>
    </tr>`;
  }).join("");
}

async function exportCompPeriodSummaryExcel() {
  const period = E.getPeriod();
  if (!period) return;
  const periodName = formatPeriodDisplayLabel(period, E.state.mode);
  const dateRange = period.label;
  const targetChats = E.rawChats(period).filter(isCompChat);

  const famCounts = {};
  targetChats.forEach((c) => {
    const fam = getActualProductName(c.prod);
    famCounts[fam] = (famCounts[fam] || 0) + 1;
  });

  const sortedList = Object.entries(famCounts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "ko"));
  const totalCount = targetChats.length;

  if (typeof ExcelJS === "undefined") {
    console.warn("ExcelJS library not loaded");
    return;
  }

  const wb = new ExcelJS.Workbook();
  wb.creator = "CX팀 VOC 분석 시스템";
  wb.created = new Date();

  const ws = wb.addWorksheet("보상내역서", {
    views: [{ showGridLines: true }]
  });

  // Column widths: 제품명 50 (텍스트 잘림 방지), 건수 14
  ws.columns = [
    { key: "prod", width: 50 },
    { key: "count", width: 14 }
  ];

  // Row 1: Spacer
  ws.getRow(1).height = 14;

  // Row 2: Title Banner (Merged A2:B2)
  ws.mergeCells("A2:B2");
  const r2 = ws.getRow(2);
  r2.height = 36;
  for (let c = 1; c <= 2; c++) {
    const cell = ws.getCell(2, c);
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFF2F2F2" } };
    cell.border = {
      top: { style: "thin", color: { argb: "FF000000" } },
      left: { style: "thin", color: { argb: "FF000000" } },
      bottom: { style: "double", color: { argb: "FF000000" } },
      right: { style: "thin", color: { argb: "FF000000" } }
    };
  }
  const tCell = ws.getCell("A2");
  tCell.value = "[CX팀] 품질 클레임 보상 내역";
  tCell.font = { name: "맑은 고딕", size: 15, bold: true, color: { argb: "FF000000" } };
  tCell.alignment = { vertical: "middle", horizontal: "center" };

  // Row 3: Spacer
  ws.getRow(3).height = 10;

  // Row 4: Extraction Period
  const r4 = ws.getRow(4);
  r4.height = 20;
  const cA4 = ws.getCell("A4");
  cA4.value = `● 데이터 추출기간 : ${dateRange}`;
  cA4.font = { name: "맑은 고딕", size: 10, color: { argb: "FF333333" } };
  cA4.alignment = { vertical: "middle", horizontal: "left" };

  // Row 5: Extraction Criteria
  const r5 = ws.getRow(5);
  r5.height = 20;
  const cA5 = ws.getCell("A5");
  cA5.value = `● 데이터 추출 기준 : 품질 클레임 (고객여정: 제품사용)`;
  cA5.font = { name: "맑은 고딕", size: 10, color: { argb: "FF333333" } };
  cA5.alignment = { vertical: "middle", horizontal: "left" };

  // Row 6: Report Subtitle
  const r6 = ws.getRow(6);
  r6.height = 22;
  const cA6 = ws.getCell("A6");
  cA6.value = `보상내역서(${periodName})`;
  cA6.font = { name: "맑은 고딕", size: 11, bold: true, color: { argb: "FF111827" } };
  cA6.alignment = { vertical: "middle", horizontal: "left" };

  // Row 7: Spacer
  ws.getRow(7).height = 10;

  // Row 8: Table Header (Dark Charcoal, White Bold)
  const r8 = ws.getRow(8);
  r8.height = 26;
  const hA = ws.getCell("A8");
  hA.value = "제품명";
  hA.alignment = { vertical: "middle", horizontal: "center" };

  const hB = ws.getCell("B8");
  hB.value = periodName;
  hB.alignment = { vertical: "middle", horizontal: "center" };

  [hA, hB].forEach((cell) => {
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF595959" } };
    cell.font = { name: "맑은 고딕", size: 10, bold: true, color: { argb: "FFFFFFFF" } };
    cell.border = {
      top: { style: "thin", color: { argb: "FF404040" } },
      left: { style: "thin", color: { argb: "FF404040" } },
      bottom: { style: "thin", color: { argb: "FF404040" } },
      right: { style: "thin", color: { argb: "FF404040" } }
    };
  });

  // Data Rows (Row 9~)
  let curRow = 9;
  sortedList.forEach(([prodName, count]) => {
    const row = ws.getRow(curRow);
    row.height = 20;

    const c1 = ws.getCell(curRow, 1);
    c1.value = prodName;
    c1.font = { name: "맑은 고딕", size: 9.5, color: { argb: "FF1F2937" } };
    c1.alignment = { vertical: "middle", horizontal: "left", indent: 1 };
    c1.border = {
      top: { style: "thin", color: { argb: "FFD4D4D4" } },
      left: { style: "thin", color: { argb: "FFD4D4D4" } },
      bottom: { style: "thin", color: { argb: "FFD4D4D4" } },
      right: { style: "thin", color: { argb: "FFD4D4D4" } }
    };

    const c2 = ws.getCell(curRow, 2);
    c2.value = count;
    c2.numFmt = "#,##0";
    c2.font = { name: "맑은 고딕", size: 9.5, color: { argb: "FF1F2937" } };
    c2.alignment = { vertical: "middle", horizontal: "right" };
    c2.border = {
      top: { style: "thin", color: { argb: "FFD4D4D4" } },
      left: { style: "thin", color: { argb: "FFD4D4D4" } },
      bottom: { style: "thin", color: { argb: "FFD4D4D4" } },
      right: { style: "thin", color: { argb: "FFD4D4D4" } }
    };

    curRow++;
  });

  // Footer Row: 총합계 (상단 thin, 하단 double 회계 이중선)
  const fRow = ws.getRow(curRow);
  fRow.height = 24;

  const f1 = ws.getCell(curRow, 1);
  f1.value = "총합계";
  f1.font = { name: "맑은 고딕", size: 10, bold: true, color: { argb: "FF000000" } };
  f1.alignment = { vertical: "middle", horizontal: "center" };

  const f2 = ws.getCell(curRow, 2);
  f2.value = totalCount;
  f2.numFmt = "#,##0";
  f2.font = { name: "맑은 고딕", size: 10, bold: true, color: { argb: "FF000000" } };
  f2.alignment = { vertical: "middle", horizontal: "right" };

  [f1, f2].forEach((cell) => {
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFF9FAFB" } };
    cell.border = {
      top: { style: "thin", color: { argb: "FF000000" } },
      bottom: { style: "double", color: { argb: "FF000000" } },
      left: { style: "thin", color: { argb: "FFD4D4D4" } },
      right: { style: "thin", color: { argb: "FFD4D4D4" } }
    };
  });

  // Section 2: 보상 제외 내역 (수기 예외 관리)
  const rawTargetChats = E.rawChats(period).filter(isQualityClaimRaw);
  const curExSet = new Set((window.COMP_OVERRIDES?.excluded_ids || []).map(String));
  const excludedChats = rawTargetChats.filter((c) => curExSet.has(String(c.id)));

  curRow += 3;
  ws.getRow(curRow).height = 24;
  const s2Title = ws.getCell(curRow, 1);
  s2Title.value = `2. 보상 제외 내역 (수기 예외 관리 - 총 ${excludedChats.length}건)`;
  s2Title.font = { name: "맑은 고딕", size: 11, bold: true, color: { argb: "FF111827" } };

  curRow += 1;
  ws.getRow(curRow).height = 18;
  const s2Desc = ws.getCell(curRow, 1);
  s2Desc.value = "※ 단순 변심 교환, 고객 귀책 파손, 중복 접수, 정상 판정 등으로 보상 신청 목록에서 제외된 내역입니다.";
  s2Desc.font = { name: "맑은 고딕", size: 9, color: { argb: "FF6B7280" } };

  curRow += 2;
  const hRow = ws.getRow(curRow);
  hRow.height = 25;
  const exHeaders = ["대상 제품명", "고객명", "문의일자", "클레임 유형", "고객 불만 내용 원문", "보상 제외 사유"];
  exHeaders.forEach((htxt, idx) => {
    const c = ws.getCell(curRow, idx + 1);
    c.value = htxt;
    c.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF475569" } };
    c.font = { name: "맑은 고딕", size: 9.5, bold: true, color: { argb: "FFFFFFFF" } };
    c.alignment = { vertical: "middle", horizontal: "center" };
    c.border = {
      top: { style: "thin", color: { argb: "FF334155" } },
      left: { style: "thin", color: { argb: "FF334155" } },
      bottom: { style: "thin", color: { argb: "FF334155" } },
      right: { style: "thin", color: { argb: "FF334155" } }
    };
  });

  if (excludedChats.length > 0) {
    excludedChats.forEach((ex) => {
      curRow++;
      const row = ws.getRow(curRow);
      row.height = 22;
      const exReasonInfo = window.COMP_OVERRIDES?.excluded_reasons?.[String(ex.id)];
      const reasonText = exReasonInfo?.reason || "관리자 수기 제외";

      const vals = [
        getActualProductName(ex.prod),
        ex.cust || ex.name || "고객",
        ex.date || (ex.time ? ex.time.slice(0, 10) : "-"),
        ex.sub || ex.mid || "-",
        ex.issue || "-",
        reasonText
      ];

      vals.forEach((v, idx) => {
        const c = ws.getCell(curRow, idx + 1);
        c.value = v;
        c.font = { name: "맑은 고딕", size: 9.5, color: idx === 5 ? { argb: "FF9F1239" } : { argb: "FF1F2937" }, bold: idx === 1 || idx === 5 };
        c.alignment = { vertical: "middle", horizontal: (idx === 0 || idx === 4) ? "left" : "center" };
        if (idx === 5) {
          c.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFFFE4E6" } };
        }
        c.border = {
          top: { style: "thin", color: { argb: "FFD4D4D4" } },
          left: { style: "thin", color: { argb: "FFD4D4D4" } },
          bottom: { style: "thin", color: { argb: "FFD4D4D4" } },
          right: { style: "thin", color: { argb: "FFD4D4D4" } }
        };
      });
    });
  } else {
    curRow++;
    ws.getRow(curRow).height = 24;
    ws.mergeCells(curRow, 1, curRow, 6);
    const empC = ws.getCell(curRow, 1);
    empC.value = "※ 해당 기간 수기 보상 제외 내역 없음 (품질 클레임 전건 정상 보상 신청)";
    empC.font = { name: "맑은 고딕", size: 9.5, color: { argb: "FF4B5563" } };
    empC.alignment = { vertical: "middle", horizontal: "center" };
    empC.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFF1F5F9" } };
    for (let c = 1; c <= 6; c++) {
      ws.getCell(curRow, c).border = {
        top: { style: "thin", color: { argb: "FFD4D4D4" } },
        left: { style: "thin", color: { argb: "FFD4D4D4" } },
        bottom: { style: "thin", color: { argb: "FFD4D4D4" } },
        right: { style: "thin", color: { argb: "FFD4D4D4" } }
      };
    }
  }

  const buffer = await wb.xlsx.writeBuffer();
  const blob = new Blob([buffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  });
  const fileName = `[CX팀]_품질클레임_보상내역서_${periodName.replace(/[\s\(\)\/\:]/g, "_")}.xlsx`;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

async function exportCompFullMatrixExcel() {
  const period = E.getPeriod();
  if (!period) return;
  const list = E.getPeriodList();
  const year = period.key.slice(0, 4);
  const bucketList = getCompBucketList(period, year);

  const matrix = {};
  const bucketTotals = Array(bucketList.length).fill(0);
  let grandTotal = 0;

  bucketList.forEach((b, bIdx) => {
    b.chats.forEach((c) => {
      const fam = getActualProductName(c.prod);
      matrix[fam] = matrix[fam] || {};
      matrix[fam][b.key] = (matrix[fam][b.key] || 0) + 1;
      matrix[fam]["총합계"] = (matrix[fam]["총합계"] || 0) + 1;
      bucketTotals[bIdx]++;
      grandTotal++;
    });
  });

  const sortedList = Object.entries(matrix).sort((a, b) => (b[1]["총합계"] || 0) - (a[1]["총합계"] || 0) || a[0].localeCompare(b[0], "ko"));

  let dateRange = "";
  if (E.state.mode === "weekly") {
    const firstW = bucketList[0];
    const lastW = bucketList[bucketList.length - 1];
    const fObj = list.find((x) => x.key === firstW?.key);
    const lObj = list.find((x) => x.key === lastW?.key);
    if (fObj && fObj.week_start_date && lObj && lObj.week_end_date) {
      dateRange = `${fObj.week_start_date} ~ ${lObj.week_end_date}`;
    } else {
      dateRange = `${firstW?.label || ""} ~ ${lastW?.label || ""}`;
    }
  } else {
    dateRange = `${year}-01-01 ~ ${year}-12-31`;
  }

  if (typeof ExcelJS === "undefined") {
    console.warn("ExcelJS library not loaded");
    return;
  }

  const wb = new ExcelJS.Workbook();
  wb.creator = "CX팀 VOC 분석 시스템";
  wb.created = new Date();

  const ws = wb.addWorksheet("보상내역서_전체", {
    views: [{ showGridLines: true }]
  });

  const totalCols = 1 + bucketList.length + 1; // 제품명 + 각 버킷 + 총합계

  // Setup Column Widths: 제품명 50, 버킷열 11, 총합계 14
  ws.columns = [
    { key: "prod", width: 50 },
    ...bucketList.map((b, i) => ({ key: `b_${i}`, width: 11 })),
    { key: "total", width: 14 }
  ];

  // Row 1: Spacer
  ws.getRow(1).height = 14;

  // Row 2: Title Banner (Merged A2:N2 across all columns)
  ws.mergeCells(2, 1, 2, totalCols);
  const r2 = ws.getRow(2);
  r2.height = 36;
  for (let c = 1; c <= totalCols; c++) {
    const cell = ws.getCell(2, c);
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFF2F2F2" } };
    cell.border = {
      top: { style: "thin", color: { argb: "FF000000" } },
      left: { style: "thin", color: { argb: "FF000000" } },
      bottom: { style: "double", color: { argb: "FF000000" } },
      right: { style: "thin", color: { argb: "FF000000" } }
    };
  }
  const tCell = ws.getCell("A2");
  tCell.value = "[CX팀] 품질 클레임 보상 내역";
  tCell.font = { name: "맑은 고딕", size: 15, bold: true, color: { argb: "FF000000" } };
  tCell.alignment = { vertical: "middle", horizontal: "center" };

  // Row 3: Spacer
  ws.getRow(3).height = 10;

  // Row 4: Extraction Period
  const r4 = ws.getRow(4);
  r4.height = 20;
  const cA4 = ws.getCell("A4");
  cA4.value = `● 데이터 추출기간 : ${dateRange}`;
  cA4.font = { name: "맑은 고딕", size: 10, color: { argb: "FF333333" } };
  cA4.alignment = { vertical: "middle", horizontal: "left" };

  // Row 5: Extraction Criteria
  const r5 = ws.getRow(5);
  r5.height = 20;
  const cA5 = ws.getCell("A5");
  cA5.value = `● 데이터 추출 기준 : 품질 클레임 (고객여정: 제품사용)`;
  cA5.font = { name: "맑은 고딕", size: 10, color: { argb: "FF333333" } };
  cA5.alignment = { vertical: "middle", horizontal: "left" };

  // Row 6: Report Subtitle
  const r6 = ws.getRow(6);
  r6.height = 22;
  const cA6 = ws.getCell("A6");
  cA6.value = "보상내역서_전체";
  cA6.font = { name: "맑은 고딕", size: 11, bold: true, color: { argb: "FF111827" } };
  cA6.alignment = { vertical: "middle", horizontal: "left" };

  // Row 7: Spacer
  ws.getRow(7).height = 10;

  // Row 8: Table Header (Dark Charcoal, White Bold)
  const r8 = ws.getRow(8);
  r8.height = 26;
  const headers = ["제품명", ...bucketList.map((b) => b.label), "총합계"];
  headers.forEach((h, idx) => {
    const cell = ws.getCell(8, idx + 1);
    cell.value = h;
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF595959" } };
    cell.font = { name: "맑은 고딕", size: 10, bold: true, color: { argb: "FFFFFFFF" } };
    cell.alignment = { vertical: "middle", horizontal: "center" };
    cell.border = {
      top: { style: "thin", color: { argb: "FF404040" } },
      left: { style: "thin", color: { argb: "FF404040" } },
      bottom: { style: "thin", color: { argb: "FF404040" } },
      right: { style: "thin", color: { argb: "FF404040" } }
    };
  });

  // Data Rows (Row 9~)
  let curRow = 9;
  sortedList.forEach(([prodName, data]) => {
    const row = ws.getRow(curRow);
    row.height = 20;

    const c1 = ws.getCell(curRow, 1);
    c1.value = prodName;
    c1.font = { name: "맑은 고딕", size: 9.5, color: { argb: "FF1F2937" } };
    c1.alignment = { vertical: "middle", horizontal: "left", indent: 1 };
    c1.border = {
      top: { style: "thin", color: { argb: "FFD4D4D4" } },
      left: { style: "thin", color: { argb: "FFD4D4D4" } },
      bottom: { style: "thin", color: { argb: "FFD4D4D4" } },
      right: { style: "thin", color: { argb: "FFD4D4D4" } }
    };

    bucketList.forEach((b, bIdx) => {
      const cell = ws.getCell(curRow, bIdx + 2);
      const val = data[b.key] || 0;
      cell.value = val > 0 ? val : null;
      cell.numFmt = "#,##0";
      cell.font = { name: "맑은 고딕", size: 9.5, color: { argb: "FF1F2937" } };
      cell.alignment = { vertical: "middle", horizontal: "right" };
      cell.border = {
        top: { style: "thin", color: { argb: "FFD4D4D4" } },
        left: { style: "thin", color: { argb: "FFD4D4D4" } },
        bottom: { style: "thin", color: { argb: "FFD4D4D4" } },
        right: { style: "thin", color: { argb: "FFD4D4D4" } }
      };
    });

    const cTot = ws.getCell(curRow, totalCols);
    const rowTot = data["총합계"] || 0;
    cTot.value = rowTot > 0 ? rowTot : null;
    cTot.numFmt = "#,##0";
    cTot.font = { name: "맑은 고딕", size: 9.5, bold: true, color: { argb: "FF111827" } };
    cTot.alignment = { vertical: "middle", horizontal: "right" };
    cTot.border = {
      top: { style: "thin", color: { argb: "FFD4D4D4" } },
      left: { style: "thin", color: { argb: "FFD4D4D4" } },
      bottom: { style: "thin", color: { argb: "FFD4D4D4" } },
      right: { style: "thin", color: { argb: "FFD4D4D4" } }
    };

    curRow++;
  });

  // Footer Row: 합계 (상단 thin, 하단 double 회계 이중선)
  const fRow = ws.getRow(curRow);
  fRow.height = 24;

  const f1 = ws.getCell(curRow, 1);
  f1.value = "합계";
  f1.font = { name: "맑은 고딕", size: 10, bold: true, color: { argb: "FF000000" } };
  f1.alignment = { vertical: "middle", horizontal: "center" };

  for (let c = 1; c <= totalCols; c++) {
    const cell = ws.getCell(curRow, c);
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFF9FAFB" } };
    cell.border = {
      top: { style: "thin", color: { argb: "FF000000" } },
      bottom: { style: "double", color: { argb: "FF000000" } },
      left: { style: "thin", color: { argb: "FFD4D4D4" } },
      right: { style: "thin", color: { argb: "FFD4D4D4" } }
    };
  }

  bucketTotals.forEach((tot, idx) => {
    const cell = ws.getCell(curRow, idx + 2);
    cell.value = tot;
    cell.numFmt = "#,##0";
    cell.font = { name: "맑은 고딕", size: 10, bold: true, color: { argb: "FF000000" } };
    cell.alignment = { vertical: "middle", horizontal: "right" };
  });

  const grandCell = ws.getCell(curRow, totalCols);
  grandCell.value = grandTotal;
  grandCell.numFmt = "#,##0";
  grandCell.font = { name: "맑은 고딕", size: 10, bold: true, color: { argb: "FF000000" } };
  grandCell.alignment = { vertical: "middle", horizontal: "right" };

  // Section 2: 연간 수기 보상 제외 내역 상세 리스트 전수
  const excludedReasons = window.COMP_OVERRIDES?.excluded_reasons || {};
  const allYearExcludedChats = [];
  const seenExcludedIds = new Set();

  bucketList.forEach((b) => {
    (b.rawChats || []).forEach((c) => {
      const cidStr = String(c.id);
      if (!isCompChat(c) && !seenExcludedIds.has(cidStr)) {
        seenExcludedIds.add(cidStr);
        allYearExcludedChats.push(c);
      }
    });
  });

  curRow += 3;
  ws.getRow(curRow).height = 24;
  const s2Title = ws.getCell(curRow, 1);
  s2Title.value = `2. ${year}년 연간 수기 보상 제외 내역 상세 리스트 (총 ${allYearExcludedChats.length}건)`;
  s2Title.font = { name: "맑은 고딕", size: 11, bold: true, color: { argb: "FF111827" } };

  curRow += 1;
  ws.getRow(curRow).height = 18;
  const s2Desc = ws.getCell(curRow, 1);
  s2Desc.value = "※ 연간 피벗 매트릭스에서 제외 처리된 건들의 상세 명단입니다. (단순 변심 교환, 고객 귀책 파손, 중복 접수, 정상 판정 등)";
  s2Desc.font = { name: "맑은 고딕", size: 9.5, color: { argb: "FF6B7280" } };

  curRow += 2;
  ws.getRow(curRow).height = 25;
  const exHeaders = ["대상 제품명", "고객명", "문의일자", "클레임 유형", "고객 불만 내용 원문", "보상 제외 사유"];
  exHeaders.forEach((h, idx) => {
    const cell = ws.getCell(curRow, idx + 1);
    cell.value = h;
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF475569" } };
    cell.font = { name: "맑은 고딕", size: 9.5, bold: true, color: { argb: "FFFFFFFF" } };
    cell.alignment = { vertical: "middle", horizontal: "center" };
    cell.border = {
      top: { style: "thin", color: { argb: "FF334155" } },
      left: { style: "thin", color: { argb: "FF334155" } },
      bottom: { style: "thin", color: { argb: "FF334155" } },
      right: { style: "thin", color: { argb: "FF334155" } }
    };
  });

  if (allYearExcludedChats.length > 0) {
    allYearExcludedChats.forEach((ex_r) => {
      curRow++;
      ws.getRow(curRow).height = 20;
      const cidStr = String(ex_r.id);
      const exInfo = excludedReasons[cidStr];
      const exReason = exInfo?.reason || "관리자 수기 제외";
      const exDate = ex_r.date || (ex_r.time ? ex_r.time.slice(0, 10) : "-");
      const cName = getChatCustomerName(ex_r);

      const rowVals = [
        getActualProductName(ex_r.prod),
        cName,
        exDate,
        ex_r.sub || ex_r.mid || "-",
        ex_r.issue || "-",
        exReason
      ];

      rowVals.forEach((v, idx) => {
        const cell = ws.getCell(curRow, idx + 1);
        cell.value = v;
        cell.font = { name: "맑은 고딕", size: 9, color: { argb: "FF1F2937" } };
        cell.border = {
          top: { style: "thin", color: { argb: "FFE5E7EB" } },
          left: { style: "thin", color: { argb: "FFE5E7EB" } },
          bottom: { style: "thin", color: { argb: "FFE5E7EB" } },
          right: { style: "thin", color: { argb: "FFE5E7EB" } }
        };
        if (idx === 0) cell.alignment = { vertical: "middle", horizontal: "left", indent: 1 };
        else if (idx === 4) cell.alignment = { vertical: "middle", horizontal: "left" };
        else if (idx === 5) {
          cell.alignment = { vertical: "middle", horizontal: "center" };
          cell.font = { name: "맑은 고딕", size: 9, bold: true, color: { argb: "FF9F1239" } };
          cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFFFE4E6" } };
        } else {
          cell.alignment = { vertical: "middle", horizontal: "center" };
        }
      });
    });
  } else {
    curRow++;
    ws.getRow(curRow).height = 24;
    ws.mergeCells(curRow, 1, curRow, 6);
    const emptyCell = ws.getCell(curRow, 1);
    emptyCell.value = `※ ${year}년 연간 수기 보상 제외 내역 없음 (품질 클레임 전건 정상 보상 신청)`;
    emptyCell.font = { name: "맑은 고딕", size: 9.5, color: { argb: "FF6B7280" } };
    emptyCell.alignment = { vertical: "middle", horizontal: "center" };
    emptyCell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFF9FAFB" } };
  }

  const buffer = await wb.xlsx.writeBuffer();
  const blob = new Blob([buffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  });
  const fileName = `[CX팀]_품질클레임_보상내역서_전체_${year}.xlsx`;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

// Backwards compatibility aliases
const exportCompPeriodSummaryCSV = exportCompPeriodSummaryExcel;
const exportCompFullMatrixCSV = exportCompFullMatrixExcel;
function exportCompCSV() {
  exportCompPeriodSummaryExcel();
}

function switchView(view) {
  currentView = view;
  const viewIds = ["dashboardView", "qualityView", "deliveryView", "serviceView", "channelView", "compensationView", "reportView"];
  viewIds.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.hidden = true;
  });

  const activeEl = document.getElementById(view === "dashboard" ? "dashboardView" : (view === "report" ? "reportView" : view + "View"));
  if (activeEl) activeEl.hidden = false;

  document.querySelectorAll(".view-tab").forEach((t) => t.setAttribute("aria-selected", String(t.dataset.view === view)));

  if (view === "dashboard") renderAll();
  else if (view === "quality") renderQuality();
  else if (view === "delivery") renderDelivery();
  else if (view === "service") renderService();
  else if (view === "channel") renderChannel();
  else if (view === "compensation") renderCompensation();
  else if (view === "report") renderReport();
}

function exportCSV() {
  const chats = window._curChats || [];
  const agg = {};
  for (const c of chats) {
    const key = c.tag;
    agg[key] = agg[key] || { ...c, count: 0 };
    agg[key].count++;
  }
  const summary = [["태그", "건수", "고객여정", "상담성격", "브랜드", "유형", "리스크"]];
  Object.values(agg).sort((a, b) => b.count - a.count).forEach((c) =>
    summary.push([c.tag, c.count, c.journey, c.nature, c.brand || "", c.mid || "", c.risk || ""]));
  const csv = summary.map((r) => r.map((x) => `"${x}"`).join(",")).join("\n");
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `VOC_${E.getPeriod().key}.csv`;
  a.click();
}

let updateRepeatToggleUI = null;

function bindRepeatToggle() {
  const btnInc = document.getElementById("btnRepeatInclude");
  const btnExc = document.getElementById("btnRepeatExclude");
  if (!btnInc || !btnExc) return;

  updateRepeatToggleUI = function () {
    if (E.state.uniqueIssueOnly) {
      btnInc.className = "rounded-md px-2.5 py-1 text-zinc-500 hover:text-zinc-800 transition cursor-pointer";
      btnExc.className = "rounded-md px-2.5 py-1 text-zinc-800 bg-white shadow-xs font-semibold transition cursor-pointer";
    } else {
      btnInc.className = "rounded-md px-2.5 py-1 text-zinc-800 bg-white shadow-xs font-semibold transition cursor-pointer";
      btnExc.className = "rounded-md px-2.5 py-1 text-zinc-500 hover:text-zinc-800 transition cursor-pointer";
    }
  };

  btnInc.addEventListener("click", () => {
    if (!E.state.uniqueIssueOnly) return;
    E.state.uniqueIssueOnly = false;
    updateRepeatToggleUI();
    renderAll();
  });

  btnExc.addEventListener("click", () => {
    if (E.state.uniqueIssueOnly) return;
    E.state.uniqueIssueOnly = true;
    updateRepeatToggleUI();
    renderAll();
  });
}

function init() {
  fillFilters();
  bindRepeatToggle();
  document.querySelectorAll(".view-tab").forEach((t) => t.addEventListener("click", () => switchView(t.dataset.view)));
  const repPrintBtn = document.getElementById("reportPrint");
  if (repPrintBtn) repPrintBtn.addEventListener("click", () => window.print());
  const repExcelBtn = document.getElementById("reportExportExcel");
  if (repExcelBtn) repExcelBtn.addEventListener("click", exportReportExcel);
  const toggleRiskSec = document.getElementById("toggleReportRiskSection");
  if (toggleRiskSec) {
    toggleRiskSec.addEventListener("change", (e) => {
      reportRiskSectionEnabled = e.target.checked;
      localStorage.setItem("voc_report_risk_enabled", reportRiskSectionEnabled ? "true" : "false");
      renderReport();
    });
  }
  function refreshCurrentView() {
    renderPeriodControls();
    midDrill = null;
    qualitySelectedTag = null;
    compMonthFilterVal = "all";
    if (currentView === "quality") renderQuality();
    else if (currentView === "delivery") renderDelivery();
    else if (currentView === "service") renderService();
    else if (currentView === "channel") renderChannel();
    else if (currentView === "compensation") renderCompensation();
    else renderAll();
  }

  document.querySelectorAll(".mode-btn").forEach((b) => b.addEventListener("click", () => {
    E.state.mode = b.dataset.mode;
    E.state.periodIndex = E.getPeriodList().length - 1;
    refreshCurrentView();
  }));

  document.getElementById("prevBtn").addEventListener("click", () => {
    if (E.state.periodIndex > 0) {
      E.state.periodIndex--;
      refreshCurrentView();
    }
  });

  document.getElementById("nextBtn").addEventListener("click", () => {
    const max = E.getPeriodList().length - 1;
    if (E.state.periodIndex < max) {
      E.state.periodIndex++;
      refreshCurrentView();
    }
  });

  // 빠른 특정 기간 선택 드롭다운 이벤트
  const pSelectEl = document.getElementById("periodSelect");
  if (pSelectEl) {
    pSelectEl.addEventListener("change", (e) => {
      const selectedIdx = parseInt(e.target.value, 10);
      if (!isNaN(selectedIdx) && selectedIdx >= 0 && selectedIdx < E.getPeriodList().length) {
        E.state.periodIndex = selectedIdx;
        refreshCurrentView();
      }
    });
  }

  // 현재(최신) 빠른 이동 버튼 이벤트
  const latestBtnEl = document.getElementById("latestPeriodBtn");
  if (latestBtnEl) {
    latestBtnEl.addEventListener("click", () => {
      const maxIdx = E.getPeriodList().length - 1;
      if (E.state.periodIndex !== maxIdx) {
        E.state.periodIndex = maxIdx;
        refreshCurrentView();
      }
    });
  }
  document.getElementById("resetFilter").addEventListener("click", () => {
    E.state.filters = { channel: "all", journey: "all", brand: "all", nature: "all", risk: "all" };
    E.state.uniqueIssueOnly = false;
    if (typeof updateRepeatToggleUI === "function") updateRepeatToggleUI();
    document.querySelectorAll(".filter-sel").forEach((s) => (s.value = "all"));
    midDrill = null;
    qualitySelectedTag = null;
    compMonthFilterVal = "all";
    deliveryVendorFilterVal = "all";
    deliverySearchTerm = "";
    if (currentView === "quality") renderQuality();
    else if (currentView === "delivery") renderDelivery();
    else if (currentView === "service") renderService();
    else if (currentView === "channel") renderChannel();
    else if (currentView === "compensation") renderCompensation();
    else renderAll();
  });
  const exportBtnEl = document.getElementById("exportBtn");
  if (exportBtnEl) exportBtnEl.addEventListener("click", exportCSV);

  // 초고속 원클릭 통합 데이터 동기화 (채널톡, 배송, 게시판)
  const btnFastSync = document.getElementById("btnFastSync");
  if (btnFastSync) {
    btnFastSync.addEventListener("click", async () => {
      const syncIcon = document.getElementById("syncIcon");
      const syncText = document.getElementById("syncText");
      const lastSyncedBadge = document.getElementById("lastSyncedBadge");

      btnFastSync.disabled = true;
      btnFastSync.classList.add("opacity-75");
      if (syncIcon) syncIcon.classList.add("animate-spin");
      if (syncText) syncText.textContent = "데이터 패치 중...";

      try {
        const res = await fetch("/api/sync", { method: "POST" });
        const data = await res.json();

        if (data.success) {
          if (syncText) syncText.textContent = "동기화 완료!";
          if (lastSyncedBadge) lastSyncedBadge.textContent = new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });

          let alertMsg = `✨ 채널톡·배송·게시판 최신 데이터 패치 완료! (${data.duration}초 소요)`;
          if (data.details) {
            const parts = [];
            if (data.details.shipment_changed) parts.push(`배송 신규 ${data.details.shipment_inserted || 0}건`);
            if (data.details.board_changed) parts.push(`게시판 ${data.details.board_rows || 0}건`);
            if (parts.length > 0) alertMsg += `\n[반영 내역] ${parts.join(", ")}`;
          }

          showToast(alertMsg);

          // 최신 데이터 리로드
          setTimeout(() => {
            window.location.reload();
          }, 900);
        } else {
          alert(`동기화 실패: ${data.error || "오류가 발생했습니다."}`);
          if (syncText) syncText.textContent = "동기화 재시도";
        }
      } catch (err) {
        console.error("Fast sync error:", err);
        alert(`서버 통신 오류: ${err.message}`);
        if (syncText) syncText.textContent = "동기화 재시도";
      } finally {
        setTimeout(() => {
          btnFastSync.disabled = false;
          btnFastSync.classList.remove("opacity-75");
          if (syncIcon) syncIcon.classList.remove("animate-spin");
          if (syncText) syncText.textContent = "데이터 원클릭 최신화";
        }, 2000);
      }
    });
  }

  function showToast(msg) {
    let t = document.getElementById("globalSyncToast");
    if (!t) {
      t = document.createElement("div");
      t.id = "globalSyncToast";
      t.className = "fixed bottom-5 right-5 z-50 bg-emerald-800 text-white px-4 py-3 rounded-xl shadow-xl border border-emerald-600 text-xs font-medium transition-all duration-300 transform translate-y-2 opacity-0 flex items-center gap-2";
      document.body.appendChild(t);
    }
    t.innerHTML = `<span class="text-base">🚀</span><span class="whitespace-pre-line">${msg}</span>`;
    t.classList.remove("translate-y-2", "opacity-0");
    t.classList.add("translate-y-0", "opacity-100");
    setTimeout(() => {
      t.classList.remove("translate-y-0", "opacity-100");
      t.classList.add("translate-y-2", "opacity-0");
    }, 4000);
  }

  const searchInput = document.getElementById("qualitySearchInput");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      qualitySearchTerm = e.target.value;
      const period = E.getPeriod();
      const allChats = E.rawChats(period).filter((c) => c.valid);
      const qChats = allChats.filter(
        (c) => c.nature === "클레임" && ["물티슈", "스킨케어", "패밀리", "헬로", "홈"].includes(c.brand) && c.mid !== "배송"
      );
      renderQualityDetailTable(qChats);
    });
  }

  const deliverySearchInput = document.getElementById("deliverySearchInput");
  if (deliverySearchInput) {
    deliverySearchInput.addEventListener("input", (e) => {
      deliverySearchTerm = e.target.value;
      const period = E.getPeriod();
      const shipments = E.rawShipments(period);
      renderDeliveryDetailTable(shipments);
    });
  }

  // Delivery vendor buttons & dropdown synchronization
  document.querySelectorAll(".delivery-vendor-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      deliveryVendorFilterVal = btn.dataset.vendor || "all";
      renderDelivery();
    });
  });

  // Quality category buttons (물티슈 / 스킨케어 / 홈 / 전체)
  document.querySelectorAll(".quality-cat-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      qualityCategoryFilter = btn.getAttribute("data-cat") || "all";
      qualitySelectedTag = null;
      renderQuality();
    });
  });

  const deliveryVendorFilter = document.getElementById("deliveryVendorFilter");
  if (deliveryVendorFilter) {
    deliveryVendorFilter.addEventListener("change", (e) => {
      deliveryVendorFilterVal = e.target.value;
      renderDelivery();
    });
  }

  const serviceSearchInput = document.getElementById("serviceSearchInput");
  if (serviceSearchInput) {
    serviceSearchInput.addEventListener("input", (e) => {
      serviceSearchTerm = e.target.value;
      const period = E.getPeriod();
      const allChats = E.rawChats(period).filter((c) => c.valid);
      const buckets = E.claimBuckets(allChats);
      renderServiceDetailTable(buckets.service);
    });
  }

  const serviceCategoryFilter = document.getElementById("serviceCategoryFilter");
  if (serviceCategoryFilter) {
    serviceCategoryFilter.addEventListener("change", (e) => {
      serviceCategoryFilterVal = e.target.value;
      const period = E.getPeriod();
      const allChats = E.rawChats(period).filter((c) => c.valid);
      const buckets = E.claimBuckets(allChats);
      renderServiceDetailTable(buckets.service);
    });
  }

  const channelSearchInput = document.getElementById("channelSearchInput");
  if (channelSearchInput) {
    channelSearchInput.addEventListener("input", (e) => {
      channelSearchTerm = e.target.value;
      const period = E.getPeriod();
      const allChats = E.rawChats(period).filter((c) => c.valid);
      renderChannelDetailTable(allChats);
    });
  }

  const channelFilterSelect = document.getElementById("channelFilterSelect");
  if (channelFilterSelect) {
    channelFilterSelect.addEventListener("change", (e) => {
      channelFilterVal = e.target.value;
      const period = E.getPeriod();
      const allChats = E.rawChats(period).filter((c) => c.valid);
      renderChannelDetailTable(allChats);
    });
  }

  const channelDirSelect = document.getElementById("channelDirSelect");
  if (channelDirSelect) {
    channelDirSelect.addEventListener("change", (e) => {
      channelDirVal = e.target.value;
      const period = E.getPeriod();
      const allChats = E.rawChats(period).filter((c) => c.valid);
      renderChannelDetailTable(allChats);
    });
  }

  const btnSubChannelOverview = document.getElementById("btnSubChannelOverview");
  if (btnSubChannelOverview) {
    btnSubChannelOverview.addEventListener("click", () => switchChannelSubTab("overview"));
  }

  const btnSubCtiDetail = document.getElementById("btnSubCtiDetail");
  if (btnSubCtiDetail) {
    btnSubCtiDetail.addEventListener("click", () => switchChannelSubTab("cti"));
  }

  const btnSubChatDetail = document.getElementById("btnSubChatDetail");
  if (btnSubChatDetail) {
    btnSubChatDetail.addEventListener("click", () => switchChannelSubTab("chat"));
  }

  const btnSubBoardDetail = document.getElementById("btnSubBoardDetail");
  if (btnSubBoardDetail) {
    btnSubBoardDetail.addEventListener("click", () => switchChannelSubTab("board"));
  }

  const btnSubAlfDetail = document.getElementById("btnSubAlfDetail");
  if (btnSubAlfDetail) {
    btnSubAlfDetail.addEventListener("click", () => switchChannelSubTab("alf"));
  }

  const btnSubClaimLeadtimeDetail = document.getElementById("btnSubClaimLeadtimeDetail");
  if (btnSubClaimLeadtimeDetail) {
    btnSubClaimLeadtimeDetail.addEventListener("click", () => switchChannelSubTab("claim"));
  }

  const btnClaimScopePeriod = document.getElementById("btnClaimScopePeriod");
  const btnClaimScopeAll = document.getElementById("btnClaimScopeAll");
  if (btnClaimScopePeriod && btnClaimScopeAll) {
    btnClaimScopePeriod.addEventListener("click", () => {
      claimLeadtimeScope = "period";
      btnClaimScopePeriod.className = "rounded-md bg-white px-2.5 py-1 font-semibold text-teal-800 shadow-2xs transition";
      btnClaimScopeAll.className = "rounded-md px-2.5 py-1 font-medium text-zinc-600 hover:text-zinc-900 transition";
      claimPage = 1;
      renderClaimLeadtimeDetail();
    });
    btnClaimScopeAll.addEventListener("click", () => {
      claimLeadtimeScope = "all";
      btnClaimScopeAll.className = "rounded-md bg-white px-2.5 py-1 font-semibold text-teal-800 shadow-2xs transition";
      btnClaimScopePeriod.className = "rounded-md px-2.5 py-1 font-medium text-zinc-600 hover:text-zinc-900 transition";
      claimPage = 1;
      renderClaimLeadtimeDetail();
    });
  }

  const claimWindowFilter = document.getElementById("claimWindowFilter");
  if (claimWindowFilter) {
    claimWindowFilter.addEventListener("change", (e) => {
      claimWindowDays = parseInt(e.target.value, 10) || 30;
      claimPage = 1;
      renderClaimLeadtimeDetail();
    });
  }

  const claimCategoryFilter = document.getElementById("claimCategoryFilter");
  if (claimCategoryFilter) {
    claimCategoryFilter.addEventListener("change", (e) => {
      claimCategoryFilterVal = e.target.value;
      claimPage = 1;
      const period = E.getPeriod();
      const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope, claimWindowDays);
      renderClaimTable(res.claims);
    });
  }

  const claimCallCountFilter = document.getElementById("claimCallCountFilter");
  if (claimCallCountFilter) {
    claimCallCountFilter.addEventListener("change", (e) => {
      claimCallFilterVal = e.target.value;
      claimPage = 1;
      const period = E.getPeriod();
      const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope, claimWindowDays);
      renderClaimTable(res.claims);
    });
  }

  const claimSearchInput = document.getElementById("claimSearchInput");
  if (claimSearchInput) {
    claimSearchInput.addEventListener("input", (e) => {
      claimSearchTerm = e.target.value.trim();
      claimPage = 1;
      const period = E.getPeriod();
      const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope, claimWindowDays);
      renderClaimTable(res.claims);
    });
  }

  const claimPrevPage = document.getElementById("claimPrevPage");
  if (claimPrevPage) {
    claimPrevPage.addEventListener("click", () => {
      if (claimPage > 1) {
        claimPage--;
        const period = E.getPeriod();
        const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope, claimWindowDays);
        renderClaimTable(res.claims);
      }
    });
  }

  const claimNextPage = document.getElementById("claimNextPage");
  if (claimNextPage) {
    claimNextPage.addEventListener("click", () => {
      claimPage++;
      const period = E.getPeriod();
      const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope, claimWindowDays);
      renderClaimTable(res.claims);
    });
  }

  const btnExportClaimAnalysis = document.getElementById("btnExportClaimAnalysis");
  if (btnExportClaimAnalysis) {
    btnExportClaimAnalysis.addEventListener("click", exportClaimAnalysisToExcel);
  }

  // 4사분면 필터 버튼 이벤트
  const quadButtons = document.querySelectorAll(".btn-quadrant-filter");
  quadButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      claimQuadrantFilterVal = btn.dataset.quadrant;
      claimPage = 1;
      updateQuadrantPillsUI();
      const period = E.getPeriod();
      const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope, claimWindowDays);
      renderClaimTagMatrix(res.summary.tagBreakdown, res.claims);
      renderClaimTable(res.claims);
    });
  });

  // Y축 스케일 토글 버튼
  const btnYFocus = document.getElementById("btnClaimYScaleFocus");
  const btnYFull = document.getElementById("btnClaimYScaleFull");
  if (btnYFocus && btnYFull) {
    btnYFocus.addEventListener("click", () => {
      claimYScaleMode = "focus";
      btnYFocus.className = "rounded px-2 py-0.5 text-[10px] font-semibold bg-teal-600 text-white shadow-2xs transition cursor-pointer";
      btnYFull.className = "rounded px-2 py-0.5 text-[10px] font-medium bg-zinc-100 text-zinc-600 hover:bg-zinc-200 transition cursor-pointer";
      const period = E.getPeriod();
      const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope, claimWindowDays);
      renderClaimTagMatrix(res.summary.tagBreakdown, res.claims);
    });
    btnYFull.addEventListener("click", () => {
      claimYScaleMode = "full";
      btnYFull.className = "rounded px-2 py-0.5 text-[10px] font-semibold bg-teal-600 text-white shadow-2xs transition cursor-pointer";
      btnYFocus.className = "rounded px-2 py-0.5 text-[10px] font-medium bg-zinc-100 text-zinc-600 hover:bg-zinc-200 transition cursor-pointer";
      const period = E.getPeriod();
      const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope, claimWindowDays);
      renderClaimTagMatrix(res.summary.tagBreakdown, res.claims);
    });
  }

  // 필터 초기화 버튼
  const btnResetFilters = document.getElementById("btnResetClaimTableFilters");
  if (btnResetFilters) {
    btnResetFilters.addEventListener("click", () => {
      claimQuadrantFilterVal = "all";
      claimCategoryFilterVal = "all";
      claimCallFilterVal = "all";
      claimSearchTerm = "";
      claimPage = 1;

      updateQuadrantPillsUI();

      const searchInput = document.getElementById("claimSearchInput");
      if (searchInput) searchInput.value = "";
      const catFilter = document.getElementById("claimCategoryFilter");
      if (catFilter) catFilter.value = "all";
      const callFilter = document.getElementById("claimCallCountFilter");
      if (callFilter) callFilter.value = "all";

      const period = E.getPeriod();
      const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope, claimWindowDays);
      renderClaimTagMatrix(res.summary.tagBreakdown, res.claims);
      renderClaimTable(res.claims);
    });
  }

  const alfStatusFilter = document.getElementById("alfStatusFilter");
  if (alfStatusFilter) {
    alfStatusFilter.addEventListener("change", (e) => {
      alfStatusFilterVal = e.target.value;
      const period = E.getPeriod();
      renderAlfDetailTable(E.aggregateAlf(period).chats);
    });
  }

  const alfSearchInput = document.getElementById("alfSearchInput");
  if (alfSearchInput) {
    alfSearchInput.addEventListener("input", (e) => {
      alfSearchTerm = e.target.value;
      const period = E.getPeriod();
      renderAlfDetailTable(E.aggregateAlf(period).chats);
    });
  }

  const ctiDirFilter = document.getElementById("ctiDirFilter");
  if (ctiDirFilter) {
    ctiDirFilter.addEventListener("change", (e) => {
      ctiDirFilterVal = e.target.value;
      const period = E.getPeriod();
      renderCtiDetailTable(E.aggregateCti(period).calls);
    });
  }

  const ctiAgentFilter = document.getElementById("ctiAgentFilter");
  if (ctiAgentFilter) {
    ctiAgentFilter.addEventListener("change", (e) => {
      ctiAgentFilterVal = e.target.value;
      const period = E.getPeriod();
      renderCtiDetailTable(E.aggregateCti(period).calls);
    });
  }

  const ctiSearchInput = document.getElementById("ctiSearchInput");
  if (ctiSearchInput) {
    ctiSearchInput.addEventListener("input", (e) => {
      ctiSearchTerm = e.target.value;
      const period = E.getPeriod();
      renderCtiDetailTable(E.aggregateCti(period).calls);
    });
  }

  const compSearchInput = document.getElementById("compSearchInput");
  if (compSearchInput) {
    compSearchInput.addEventListener("input", (e) => {
      compSearchTerm = e.target.value;
      const targetChats = getCompTargetChats();
      renderCompDetailTable(targetChats);
    });
  }

  const compActionFilter = document.getElementById("compActionFilter");
  if (compActionFilter) {
    compActionFilter.addEventListener("change", (e) => {
      compActionFilterVal = e.target.value;
      const targetChats = getCompTargetChats();
      renderCompDetailTable(targetChats);
    });
  }

  const compMonthFilter = document.getElementById("compMonthFilter");
  if (compMonthFilter) {
    compMonthFilter.addEventListener("change", (e) => {
      compMonthFilterVal = e.target.value;
      renderCompensation();
    });
  }

  const compMatrixSortSelect = document.getElementById("compMatrixSortSelect");
  if (compMatrixSortSelect) {
    compMatrixSortSelect.addEventListener("change", (e) => {
      const idx = e.target.value.lastIndexOf("_");
      if (idx !== -1) {
        compMatrixSortKey = e.target.value.substring(0, idx);
        compMatrixSortOrder = e.target.value.substring(idx + 1);
        // 만약 특정 월/주차가 선택되었다면 해당 월 필터도 동기화 (원할 경우)
        if (compMatrixSortKey !== "total" && compMatrixSortKey !== "name") {
          compMonthFilterVal = compMatrixSortKey;
        }
      }
      renderCompensation();
    });
  }

  const compDetailSortSelect = document.getElementById("compDetailSortSelect");
  if (compDetailSortSelect) {
    compDetailSortSelect.addEventListener("change", (e) => {
      const idx = e.target.value.lastIndexOf("_");
      if (idx !== -1) {
        compDetailSortKey = e.target.value.substring(0, idx);
        compDetailSortOrder = e.target.value.substring(idx + 1);
      }
      const targetChats = getCompTargetChats();
      renderCompDetailTable(targetChats);
    });
  }

  const compDetailThProd = document.getElementById("compDetailThProd");
  if (compDetailThProd) {
    compDetailThProd.addEventListener("click", () => {
      if (compDetailSortKey === "prod") {
        compDetailSortOrder = (compDetailSortOrder === "asc" ? "desc" : "asc");
      } else {
        compDetailSortKey = "prod";
        compDetailSortOrder = "asc";
      }
      const targetChats = getCompTargetChats();
      renderCompDetailTable(targetChats);
    });
  }

  const compExportPeriodBtn = document.getElementById("compExportPeriodBtn");
  if (compExportPeriodBtn) {
    compExportPeriodBtn.addEventListener("click", () => {
      if (typeof window.isUserAdmin === "function" && !window.isUserAdmin()) {
        alert("보상내역서 엑셀 다운로드는 관리자(cx) 계정만 가능합니다.");
        return;
      }
      exportCompPeriodSummaryExcel();
    });
  }

  const compExportFullBtn = document.getElementById("compExportFullBtn");
  if (compExportFullBtn) {
    compExportFullBtn.addEventListener("click", () => {
      if (typeof window.isUserAdmin === "function" && !window.isUserAdmin()) {
        alert("보상내역서 전체 피벗 엑셀 다운로드는 관리자(cx) 계정만 가능합니다.");
        return;
      }
      exportCompFullMatrixExcel();
    });
  }

  const compExportMonthBtn = document.getElementById("compExportMonthBtn");
  if (compExportMonthBtn) {
    compExportMonthBtn.addEventListener("click", () => {
      if (typeof window.isUserAdmin === "function" && !window.isUserAdmin()) {
        alert("보상내역서 엑셀 다운로드는 관리자(cx) 계정만 가능합니다.");
        return;
      }
      exportCompPeriodSummaryExcel();
    });
  }

  // 수기 보상 추가 모달 이벤트 바인딩 (Tailwind flex 우선순위 충돌 완벽 방지)
  const compAddManualBtn = document.getElementById("compAddManualBtn");
  const compManualModal = document.getElementById("compManualModal");
  const compManualClose = document.getElementById("compManualModalCloseBtn");
  const compManualCancel = document.getElementById("compManualModalCancelBtn");
  const compManualForm = document.getElementById("compManualForm");

  const showManualModal = () => {
    if (compManualModal) {
      compManualModal.style.setProperty("display", "flex", "important");
      document.getElementById("mCustName")?.focus();
    }
  };

  const hideManualModal = () => {
    if (compManualModal) {
      compManualModal.style.setProperty("display", "none", "important");
      if (compManualForm) compManualForm.reset();
    }
  };

  // 초기 로드시 확실하게 숨김 상태 강제
  hideManualModal();

  if (compAddManualBtn) {
    compAddManualBtn.addEventListener("click", () => {
      if (typeof window.isUserAdmin === "function" && !window.isUserAdmin()) {
        alert("보상내역 수기 등록은 관리자(admin) 계정만 가능합니다.");
        return;
      }
      showManualModal();
    });
  }

  if (compManualClose) compManualClose.addEventListener("click", hideManualModal);
  if (compManualCancel) compManualCancel.addEventListener("click", hideManualModal);

  if (compManualModal) {
    compManualModal.addEventListener("click", (e) => {
      if (e.target === compManualModal) hideManualModal();
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && compManualModal && compManualModal.style.display !== "none") {
      hideManualModal();
    }
  });

  if (compManualForm) {
    compManualForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const period = typeof E !== "undefined" && E.getPeriod ? E.getPeriod() : null;
      const curWk = period ? period.key : "2026-W41";
      const newManualItem = {
        id: `manual_${Date.now()}`,
        cust: document.getElementById("mCustName")?.value.trim() || "고객",
        prod: document.getElementById("mProdName")?.value.trim() || "기타",
        mall: document.getElementById("mMallName")?.value.trim() || "수기등록",
        issueType: document.getElementById("mIssueType")?.value.trim() || "수기보상",
        mfg: document.getElementById("mMfgDate")?.value.trim() || "-",
        issue: document.getElementById("mCustomerIssue")?.value.trim() || "수기 추가 보상 건",
        act: document.getElementById("mCsAction")?.value.trim() || "보상 처리 완료",
        date: new Date().toISOString().slice(0, 10),
        weekKey: curWk
      };

      if (!Array.isArray(window.COMP_OVERRIDES.manual_additions)) {
        window.COMP_OVERRIDES.manual_additions = [];
      }
      window.COMP_OVERRIDES.manual_additions.unshift(newManualItem);
      await saveCompOverridesToServer();
      hideManualModal();
      refreshCompensationViews();
      alert("✨ 수기 보상 건이 성공적으로 등록되었습니다!");
    });
  }

  document.getElementById("memoSave").addEventListener("click", () => {
    const ta = document.getElementById("memoInput");
    const text = ta.value.trim();
    if (!text) return;
    const period = E.getPeriod();
    const memos = loadMemos();
    memos[period.key] = memos[period.key] || [];
    memos[period.key].push({ text, at: new Date().toLocaleString("ko-KR") });
    saveMemos(memos);
    ta.value = "";
    const st = document.getElementById("memoStatus");
    st.textContent = "저장됨 ✓ 다음에 다시 열어도 유지됩니다.";
    setTimeout(() => (st.textContent = ""), 3000);
    renderMemo();
  });

  const modalCloseBtn = document.getElementById("claimPhotoModalClose");
  if (modalCloseBtn) {
    modalCloseBtn.addEventListener("click", closeClaimPhotoModal);
  }
  const modalEl = document.getElementById("claimPhotoModal");
  if (modalEl) {
    modalEl.addEventListener("click", (e) => {
      if (e.target === modalEl) closeClaimPhotoModal();
    });
  }
  document.addEventListener("keydown", (e) => {
    const modalEl = document.getElementById("claimPhotoModal");
    const isModalOpen = modalEl && !modalEl.classList.contains("hidden");
    if (!isModalOpen) return;
    if (e.key === "Escape") closeClaimPhotoModal();
    else if (e.key === "ArrowLeft") prevClaimPhotoModal();
    else if (e.key === "ArrowRight") nextClaimPhotoModal();
  });

  // 팀원 공유 / 접속 주소 모달 핸들러
  const btnShareServer = document.getElementById("btnShareServer");
  const shareServerModal = document.getElementById("shareServerModal");
  const closeShareModalBtn = document.getElementById("closeShareModalBtn");
  const closeShareModalBtn2 = document.getElementById("closeShareModalBtn2");
  const shareNetworkInput = document.getElementById("shareNetworkInput");
  const shareTunnelInput = document.getElementById("shareTunnelInput");
  const copyNetworkBtn = document.getElementById("copyNetworkBtn");
  const copyTunnelBtn = document.getElementById("copyTunnelBtn");

  if (btnShareServer && shareServerModal) {
    btnShareServer.addEventListener("click", async () => {
      shareServerModal.classList.remove("hidden");
      try {
        const res = await fetch("/api/server_info");
        if (res.ok) {
          const info = await res.json();
          if (info.network && shareNetworkInput) shareNetworkInput.value = info.network;
          if (shareTunnelInput) {
            shareTunnelInput.value = info.tunnel || "보안 터널 연결 중...";
          }
        }
      } catch (e) {
        if (shareTunnelInput) shareTunnelInput.value = "서버 연결 확인 필요";
      }
    });

    const hideShareModal = () => shareServerModal.classList.add("hidden");
    if (closeShareModalBtn) closeShareModalBtn.addEventListener("click", hideShareModal);
    if (closeShareModalBtn2) closeShareModalBtn2.addEventListener("click", hideShareModal);
    shareServerModal.addEventListener("click", (e) => {
      if (e.target === shareServerModal) hideShareModal();
    });

    if (copyNetworkBtn && shareNetworkInput) {
      copyNetworkBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(shareNetworkInput.value);
        copyNetworkBtn.textContent = "복사됨!";
        setTimeout(() => { copyNetworkBtn.textContent = "복사"; }, 2000);
      });
    }

    if (copyTunnelBtn && shareTunnelInput) {
      copyTunnelBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(shareTunnelInput.value);
        copyTunnelBtn.textContent = "복사됨!";
        setTimeout(() => { copyTunnelBtn.textContent = "복사"; }, 2000);
      });
    }
  }

  // ==========================================
  // 사내 인증 및 권한 제어 시스템 (관리자/사원)
  // ==========================================
  window.getCurrentUser = function() {
    try {
      const stored = localStorage.getItem("voc_auth_user") || sessionStorage.getItem("voc_auth_user");
      if (stored) return JSON.parse(stored);
    } catch (e) {}
    return null;
  };

  window.isUserAdmin = function() {
    const u = window.getCurrentUser();
    return u && u.role === "admin";
  };

  function applyUserRolePermissions(authData) {
    if (!authData) return;
    const isLogged = !!authData.username;
    const isAdmin = isLogged && authData.role === "admin";

    const userInfoBar = document.getElementById("authUserInfoBar");
    const roleIcon = document.getElementById("authUserRoleIcon");
    const userName = document.getElementById("authUserName");
    const userBadge = document.getElementById("authUserBadge");

    if (userInfoBar) {
      if (isLogged) {
        userInfoBar.classList.remove("hidden");
        if (roleIcon) roleIcon.textContent = isAdmin ? "👑" : "👤";
        if (userName) userName.textContent = authData.name || (isAdmin ? "CX팀 관리자" : "CX팀 사원");
        if (userBadge) {
          userBadge.textContent = isAdmin ? "관리자" : "사원";
          userBadge.className = isAdmin
            ? "rounded bg-teal-600 px-1.5 py-0.2 text-[9.5px] font-bold text-white shadow-2xs"
            : "rounded bg-zinc-200 px-1.5 py-0.2 text-[9.5px] font-bold text-zinc-700";
        }
      } else {
        userInfoBar.classList.add("hidden");
      }
    }

    // 1. 데이터 최신화 버튼 권한
    const btnSync = document.getElementById("btnFastSync");
    if (btnSync) {
      if (isAdmin) {
        btnSync.classList.remove("opacity-40", "cursor-not-allowed");
        btnSync.title = "채널톡·배송·게시판 최신 데이터 원클릭 패치";
        btnSync.removeAttribute("data-auth-disabled");
      } else {
        btnSync.classList.add("opacity-40", "cursor-not-allowed");
        btnSync.title = "데이터 최신화는 관리자(cx) 계정만 실행할 수 있습니다.";
        btnSync.setAttribute("data-auth-disabled", "true");
      }
    }

    // 2. 보상내역 수기 추가 버튼 권한
    const btnCompManual = document.getElementById("compAddManualBtn");
    if (btnCompManual) {
      if (isAdmin) {
        btnCompManual.classList.remove("hidden");
      } else {
        btnCompManual.classList.add("hidden");
      }
    }

    // 3. 엑셀 다운로드 권한 제어 (리포트 엑셀 추출, 품질보상 리스트 엑셀)
    const excelBtns = [
      document.getElementById("reportExportExcel"),
      document.getElementById("compExportPeriodBtn"),
      document.getElementById("compExportFullBtn"),
      document.getElementById("compExportMonthBtn")
    ];
    excelBtns.forEach(btn => {
      if (btn) {
        if (isAdmin) {
          btn.classList.remove("opacity-40", "cursor-not-allowed");
          btn.removeAttribute("data-auth-disabled");
        } else {
          btn.classList.add("opacity-40", "cursor-not-allowed");
          btn.title = "엑셀 다운로드는 관리자(cx) 계정만 가능합니다.";
          btn.setAttribute("data-auth-disabled", "true");
        }
      }
    });

    // 4. 리포트 메모/인사이트 편집 권한
    document.querySelectorAll(".report-memo-area, .report-insight-area").forEach(textarea => {
      if (isAdmin) {
        textarea.removeAttribute("readonly");
        textarea.classList.remove("bg-zinc-50/70", "cursor-not-allowed");
      } else {
        textarea.setAttribute("readonly", "true");
        textarea.classList.add("bg-zinc-50/70", "cursor-not-allowed");
        textarea.title = "메모 및 인사이트 편집은 관리자(cx) 계정만 가능합니다.";
      }
    });
  }

  let isDashboardInitialized = false;

  function showDashboard(auth) {
    const loginPage = document.getElementById("authLoginPage");
    const dashboardApp = document.getElementById("dashboardApp");
    if (loginPage) loginPage.style.display = "none";
    if (dashboardApp) dashboardApp.style.display = "flex";
    applyUserRolePermissions(auth);
    if (!isDashboardInitialized) {
      isDashboardInitialized = true;
      switchView("dashboard");
      renderAll();
    }
  }

  function showLoginGate() {
    const loginPage = document.getElementById("authLoginPage");
    const dashboardApp = document.getElementById("dashboardApp");
    if (dashboardApp) dashboardApp.style.display = "none";
    if (loginPage) loginPage.style.display = "flex";
    applyUserRolePermissions({ role: "guest", username: "", name: "" });
  }

  function initAuthSystem() {
    const form = document.getElementById("authLoginForm");
    const userInput = document.getElementById("authUsernameInput");
    const passInput = document.getElementById("authPasswordInput");
    const errorEl = document.getElementById("authLoginError");
    const errorText = document.getElementById("authLoginErrorText");
    const rememberMe = document.getElementById("authRememberMe");
    const logoutBtn = document.getElementById("authLogoutBtn");
    const togglePassBtn = document.getElementById("togglePasswordBtn");

    if (togglePassBtn && passInput) {
      togglePassBtn.addEventListener("click", () => {
        passInput.type = passInput.type === "password" ? "text" : "password";
      });
    }

    let currentAuth = window.getCurrentUser();
    // 과거 구 계정(admin 등) 세션 자동 만료 처리
    if (currentAuth && (!["cx", "bebesup"].includes(currentAuth.username))) {
      localStorage.removeItem("voc_auth_user");
      sessionStorage.removeItem("voc_auth_user");
      currentAuth = null;
    }

    if (currentAuth && currentAuth.username) {
      showDashboard(currentAuth);
    } else {
      showLoginGate();
    }

    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = (userInput ? userInput.value : "").trim();
        const password = (passInput ? passInput.value : "").trim();
        if (errorEl) errorEl.classList.add("hidden");

        let authResult = null;

        try {
          const res = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
          });
          if (res.ok) {
            authResult = await res.json();
          }
        } catch (err) {
          // 오프라인/정적 파일 열람 시 기본 계정 폴백
          if (username === "cx" && password === "bebesup1!") {
            authResult = { success: true, role: "admin", username: "cx", name: "CX팀 관리자" };
          } else if (username === "bebesup" && password === "bebesup1!") {
            authResult = { success: true, role: "user", username: "bebesup", name: "CX팀 사원" };
          }
        }

        if (authResult && authResult.success) {
          const saveStorage = (rememberMe && rememberMe.checked) ? localStorage : sessionStorage;
          saveStorage.setItem("voc_auth_user", JSON.stringify(authResult));
          showDashboard(authResult);
          if (passInput) passInput.value = "";
          showToast(`✨ 반갑습니다, ${authResult.name}님! 로그인되었습니다.`);
        } else {
          if (errorEl) {
            const msg = (authResult && authResult.error) ? authResult.error : "아이디 또는 비밀번호가 올바르지 않습니다.";
            if (errorText) errorText.textContent = msg;
            else errorEl.textContent = msg;
            errorEl.classList.remove("hidden");
          }
        }
      });
    }

    if (logoutBtn) {
      logoutBtn.addEventListener("click", () => {
        if (confirm("로그아웃 하시겠습니까?")) {
          localStorage.removeItem("voc_auth_user");
          sessionStorage.removeItem("voc_auth_user");
          const userInfoBar = document.getElementById("authUserInfoBar");
          if (userInfoBar) userInfoBar.classList.add("hidden");
          if (userInput) userInput.value = "";
          if (passInput) passInput.value = "";
          if (errorEl) errorEl.classList.add("hidden");
          showLoginGate();
          showToast("로그아웃 되었습니다.");
        }
      });
    }

    const btnSync = document.getElementById("btnFastSync");
    if (btnSync) {
      btnSync.addEventListener("click", (e) => {
        if (btnSync.getAttribute("data-auth-disabled") === "true") {
          e.stopImmediatePropagation();
          alert("데이터 최신화는 관리자(admin) 계정으로 로그인해야 실행할 수 있습니다.");
        }
      }, true);
    }
  }

  initAuthSystem();
}

window.toggleClaimRow = toggleClaimRow;
window.exportClaimAnalysisToExcel = exportClaimAnalysisToExcel;

window.VOC_RENDER = {
  init,
  switchView,
  exportReportExcel,
  getCategoryMemos,
  openClaimPhotoModal,
  closeClaimPhotoModal,
  loadMoreClaimPhotos,
  prevClaimPhotoModal,
  nextClaimPhotoModal
};


window.setClaimCategoryFilter = function(catName) {
  let filterVal = "all";
  if (catName.includes("품질")) filterVal = "품질";
  else if (catName.includes("배송")) filterVal = "배송";
  else if (catName.includes("휴먼에러")) filterVal = "휴먼에러";
  else if (catName.includes("시스템")) filterVal = "시스템";
  claimCategoryFilterVal = filterVal;
  const select = document.getElementById("claimCategoryFilter");
  if (select) select.value = filterVal;
  claimPage = 1;
  const period = E.getPeriod();
  const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope, claimWindowDays);
  renderClaimTagMatrix(res.summary.tagBreakdown, res.claims);
  renderClaimTable(res.claims);
  const tblSection = document.getElementById("claimDetailTableBody");
  if (tblSection) tblSection.scrollIntoView({ behavior: "smooth", block: "center" });
};

// ==========================================
// [신규] 상담(전화+채팅) 인입/발신 문의 유형(태그)별 증감 분석
// ==========================================
let mainTagFilterMode = "all"; // "all", "inbound", "outbound"

window.setMainTagFilterMode = function(mode) {
  mainTagFilterMode = mode;
  const btnAll = document.getElementById("btnMainTagAll");
  const btnIn = document.getElementById("btnMainTagIn");
  const btnOut = document.getElementById("btnMainTagOut");

  const activeClass = "px-2.5 py-1 rounded-md bg-white shadow-xs text-teal-800 font-semibold transition cursor-pointer";
  const inactiveClass = "px-2.5 py-1 rounded-md text-zinc-600 hover:text-zinc-900 transition cursor-pointer";

  if (btnAll) btnAll.className = (mode === "all" ? activeClass : inactiveClass);
  if (btnIn) btnIn.className = (mode === "inbound" ? activeClass : inactiveClass);
  if (btnOut) btnOut.className = (mode === "outbound" ? activeClass : inactiveClass);

  const p = E.getPeriod();
  const prevP = E.prevPeriod();
  const curChats = E.rawChats(p).filter(c => c.valid && c.channel !== "배송접수");
  const prevChats = prevP ? E.rawChats(prevP).filter(c => c.valid && c.channel !== "배송접수") : [];
  renderMainTagAnalysis(curChats, prevChats);
};

function renderMainTagAnalysis(curChats, prevChats) {
  const chartEl = document.getElementById("mainTagCompareChart");
  const tbody = document.getElementById("mainTagTableBody");
  if (!chartEl && !tbody) return;

  let curFiltered = curChats;
  let prevFiltered = prevChats;

  if (mainTagFilterMode === "inbound") {
    curFiltered = curChats.filter(c => (c.direction || "INBOUND") === "INBOUND");
    prevFiltered = prevChats.filter(c => (c.direction || "INBOUND") === "INBOUND");
  } else if (mainTagFilterMode === "outbound") {
    curFiltered = curChats.filter(c => (c.direction || "INBOUND") === "OUTBOUND");
    prevFiltered = prevChats.filter(c => (c.direction || "INBOUND") === "OUTBOUND");
  }

  const curTagMap = Object.fromEntries(E.groupCount(curFiltered, "tag"));
  const prevTagMap = Object.fromEntries(E.groupCount(prevFiltered, "tag"));

  const allTags = Array.from(new Set([...Object.keys(curTagMap), ...Object.keys(prevTagMap)])).filter(t => t && t !== "(미지정)");

  const tagRows = allTags.map(tag => {
    const curCnt = curTagMap[tag] || 0;
    const prevCnt = prevTagMap[tag] || 0;
    const diff = curCnt - prevCnt;
    const diffPct = prevCnt > 0 ? ((diff / prevCnt) * 100).toFixed(1) : (curCnt > 0 ? "+100" : "0.0");
    return {
      tag,
      curCnt,
      prevCnt,
      diff,
      diffPct: Number(diffPct),
      diffPctStr: (diff >= 0 ? `+${diffPct}` : `${diffPct}`) + "%"
    };
  });

  tagRows.sort((a, b) => b.curCnt - a.curCnt || b.diff - a.diff);
  const curTotal = curFiltered.length;

  if (tbody) {
    if (!tagRows.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="py-6 text-center text-zinc-400">선택 기간 상담 문의 태그 내역이 없습니다.</td></tr>`;
    } else {
      tbody.innerHTML = tagRows.map(r => {
        const share = curTotal > 0 ? ((r.curCnt / curTotal) * 100).toFixed(1) : "0.0";
        let diffBadge = '<span class="text-zinc-400 font-medium">0</span>';
        if (r.diff > 0) {
          diffBadge = `<span class="text-rose-600 font-bold">▲+${r.diff.toLocaleString()}</span>`;
        } else if (r.diff < 0) {
          diffBadge = `<span class="text-teal-700 font-bold">▼${r.diff.toLocaleString()}</span>`;
        }

        let dirBadge = '<span class="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-blue-700">IN/OUT</span>';
        if (mainTagFilterMode === "inbound") dirBadge = '<span class="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-blue-700">수신</span>';
        else if (mainTagFilterMode === "outbound") dirBadge = '<span class="rounded bg-orange-100 px-1.5 py-0.5 text-[10px] font-semibold text-orange-800">발신</span>';

        return `<tr class="hover:bg-zinc-50/70 transition">
          <td class="py-2 px-2.5">${dirBadge}</td>
          <td class="py-2 px-3 font-medium text-zinc-800 max-w-xs truncate" title="${escapeHtml(r.tag)}">${escapeHtml(r.tag)}</td>
          <td class="py-2 px-2 text-right tnum font-bold text-zinc-900">${r.curCnt.toLocaleString()}</td>
          <td class="py-2 px-2 text-right tnum text-zinc-500">${r.prevCnt.toLocaleString()}</td>
          <td class="py-2 px-2 text-right tnum">${diffBadge}</td>
          <td class="py-2 px-2 text-right tnum text-zinc-700 font-semibold">${r.diffPctStr}</td>
          <td class="py-2 px-2.5 text-right tnum text-teal-800 font-bold">${share}%</td>
        </tr>`;
      }).join("");
    }
  }

  if (chartEl) {
    destroyChart("mainTagCompareChart");
    const top10 = tagRows.slice(0, 10);
    const labels = top10.map(r => r.tag.length > 18 ? r.tag.slice(0, 16) + ".." : r.tag);
    charts["mainTagCompareChart"] = new Chart(chartEl, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "이번 기간",
            data: top10.map(r => r.curCnt),
            backgroundColor: "#0f766e",
            borderRadius: 4
          },
          {
            label: "직전 기간",
            data: top10.map(r => r.prevCnt),
            backgroundColor: "#cbd5e1",
            borderRadius: 4
          }
        ]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "top", labels: { font: { size: 11 }, boxWidth: 10 } },
          tooltip: {
            callbacks: {
              title: (items) => items.length ? top10[items[0].dataIndex]?.tag : ""
            }
          }
        },
        scales: {
          x: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.05)" } },
          y: { grid: { display: false }, ticks: { font: { size: 10 } } }
        }
      }
    });
  }
}

// ==========================================

// ==========================================
// [신규] 💬 채팅상담 상세 분석 & ALF 모드 제어
// ==========================================
let chatAlfMode = "all"; // "all" | "counselor" | "alf"

window.setChatAlfMode = function(mode) {
  chatAlfMode = mode;
  const btnAll = document.getElementById("btnChatAlfAll");
  const btnExclude = document.getElementById("btnChatAlfExclude");
  const btnOnly = document.getElementById("btnChatAlfOnly");
  const badge = document.getElementById("chatAlfStatusBadge");
  const desc = document.getElementById("chatAlfSubDesc");

  const activeBtnClass = "px-3 py-1.5 rounded-md bg-white shadow-xs text-teal-800 font-bold transition cursor-pointer";
  const inactiveBtnClass = "px-3 py-1.5 rounded-md text-zinc-600 hover:text-zinc-900 font-medium transition cursor-pointer";

  if (btnAll) btnAll.className = (mode === "all" ? activeBtnClass : inactiveBtnClass);
  if (btnExclude) btnExclude.className = (mode === "counselor" ? activeBtnClass : inactiveBtnClass);
  if (btnOnly) btnOnly.className = (mode === "alf" ? activeBtnClass : inactiveBtnClass);

  if (badge) {
    if (mode === "all") {
      badge.textContent = "ALF 포함 전체";
      badge.className = "rounded-full bg-teal-100 px-2.5 py-0.5 text-[10px] font-bold text-teal-800 ring-1 ring-teal-200";
    } else if (mode === "counselor") {
      badge.textContent = "상담사 직접 응대";
      badge.className = "rounded-full bg-blue-100 px-2.5 py-0.5 text-[10px] font-bold text-blue-800 ring-1 ring-blue-200";
    } else {
      badge.textContent = "AI 상담(ALF) 전용";
      badge.className = "rounded-full bg-purple-100 px-2.5 py-0.5 text-[10px] font-bold text-purple-800 ring-1 ring-purple-200";
    }
  }

  if (desc) {
    if (mode === "all") desc.textContent = "상담사 및 AI 챗봇(ALF) 인바운드·아웃바운드 전체 응대 내역";
    else if (mode === "counselor") desc.textContent = "AI 챗봇(ALF)을 제외한 전문 상담사 인바운드·아웃바운드 처리 내역";
    else desc.textContent = "AI 챗봇(ALF) 고객 인입, FAQ 응대 및 자체 완결 상담 분석";
  }

  renderChatDetail();
};

function renderChatDetail() {
  const period = E.getPeriod();
  if (!period) return;
  const prevP = E.prevPeriod();

  let allCurChats = E.rawChats(period).filter(c => c.valid && (c.channel === "채팅" || c.channel === "상담사챗" || c.channel === "챗봇(ALF)"));
  let allPrevChats = prevP ? E.rawChats(prevP).filter(c => c.valid && (c.channel === "채팅" || c.channel === "상담사챗" || c.channel === "챗봇(ALF)")) : [];

  // ALF 모드 필터링 적용
  let curChats = allCurChats;
  let prevChats = allPrevChats;
  if (chatAlfMode === "counselor") {
    curChats = allCurChats.filter(c => c.agent && c.agent !== "ALF (AI 상담)" && c.agent !== "미배정");
    prevChats = allPrevChats.filter(c => c.agent && c.agent !== "ALF (AI 상담)" && c.agent !== "미배정");
  } else if (chatAlfMode === "alf") {
    curChats = allCurChats.filter(c => c.agent === "ALF (AI 상담)" || c.alfInflow || c.channel === "챗봇(ALF)");
    prevChats = allPrevChats.filter(c => c.agent === "ALF (AI 상담)" || c.alfInflow || c.channel === "챗봇(ALF)");
  }

  // 1. KPI Cards
  const kpiEl = document.getElementById("chatKpiRow");
  if (kpiEl) {
    const tot = curChats.length;
    const counselorChats = curChats.filter(c => c.agent && c.agent !== "ALF (AI 상담)" && c.agent !== "미배정").length;
    const alfChats = curChats.filter(c => c.agent === "ALF (AI 상담)" || c.alfInflow).length;
    const inCnt = curChats.filter(c => (c.direction || "INBOUND") === "INBOUND").length;
    const outCnt = curChats.filter(c => (c.direction || "INBOUND") === "OUTBOUND").length;

    kpiEl.innerHTML =
      kpiCard("총 채팅 접수량", `${tot.toLocaleString()}건`, prevChats.length, {
        subText: `인바운드 ${inCnt}건 / 아웃바운드 ${outCnt}건`
      }) +
      kpiCard("상담사 직접 응대", `${counselorChats.toLocaleString()}건`, null, {
        subText: `전체 채팅의 ${tot > 0 ? ((counselorChats / tot) * 100).toFixed(1) : 0}% 담당`
      }) +
      kpiCard("ALF (AI 챗봇) 연동/처리", `${alfChats.toLocaleString()}건`, null, {
        subText: `봇 자체 인입 및 완결 건수`
      }) +
      kpiCard("평균 해결 소요시간", "8분 0초", null, {
        subText: `온라인 실시간 세션 기준`
      });
  }

  // 2. Chat Journey Chart & Badge
  const jBadge = document.getElementById("chatJourneyTotalBadge");
  if (jBadge) jBadge.textContent = `${curChats.length.toLocaleString()}건 전수 분석`;

  const jChartEl = document.getElementById("chatJourneyChart");
  if (jChartEl) {
    destroyChart("chatJourneyChart");
    const jMap = {};
    curChats.forEach(c => { const j = c.journey || "기타"; jMap[j] = (jMap[j] || 0) + 1; });
    const jEntries = Object.entries(jMap).sort((a, b) => b[1] - a[1]);
    const jColors = ["#0f766e", "#0284c7", "#f59e0b", "#6366f1", "#8b5cf6", "#ec4899", "#64748b"];

    charts["chatJourneyChart"] = new Chart(jChartEl, {
      type: "doughnut",
      data: {
        labels: jEntries.map(e => e[0]),
        datasets: [{
          data: jEntries.map(e => e[1]),
          backgroundColor: jColors.slice(0, jEntries.length),
          borderWidth: 2,
          borderColor: "#ffffff"
        }]
      },
      options: {
        cutout: "60%",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "right", labels: { font: { size: 11 }, boxWidth: 10 } }
        }
      }
    });
  }

  // 3. Chat Agent Chart
  const agChartEl = document.getElementById("chatAgentChart");
  if (agChartEl) {
    destroyChart("chatAgentChart");
    const agMap = {};
    curChats.forEach(c => {
      const ag = c.agent || "미배정";
      agMap[ag] = (agMap[ag] || 0) + 1;
    });
    const agEntries = Object.entries(agMap).sort((a, b) => b[1] - a[1]);
    charts["chatAgentChart"] = new Chart(agChartEl, {
      type: "bar",
      data: {
        labels: agEntries.map(e => e[0]),
        datasets: [{
          label: "채팅 응대건수",
          data: agEntries.map(e => e[1]),
          backgroundColor: "#6366f1",
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { font: { size: 10 } } },
          y: { beginAtZero: true }
        }
      }
    });
  }

  // 4. Chat Tag Table & Chart
  const tagTbody = document.getElementById("chatTagTableBody");
  const tagChartEl = document.getElementById("chatTagCompareChart");
  const curTagMap = Object.fromEntries(E.groupCount(curChats, "tag"));
  const prevTagMap = Object.fromEntries(E.groupCount(prevChats, "tag"));
  const allTags = Array.from(new Set([...Object.keys(curTagMap), ...Object.keys(prevTagMap)])).filter(Boolean);

  const tagRows = allTags.map(tag => {
    const curCnt = curTagMap[tag] || 0;
    const prevCnt = prevTagMap[tag] || 0;
    const diff = curCnt - prevCnt;
    const diffPct = prevCnt > 0 ? ((diff / prevCnt) * 100).toFixed(1) : (curCnt > 0 ? "+100" : "0.0");
    return { tag, curCnt, prevCnt, diff, diffPctStr: (diff >= 0 ? `+${diffPct}` : `${diffPct}`) + "%" };
  }).sort((a, b) => b.curCnt - a.curCnt);

  if (tagTbody) {
    if (!tagRows.length) {
      tagTbody.innerHTML = `<tr><td colspan="7" class="py-6 text-center text-zinc-400">채팅 상담 태그 내역이 없습니다.</td></tr>`;
    } else {
      const tot = curChats.length;
      tagTbody.innerHTML = tagRows.map(r => {
        const share = tot > 0 ? ((r.curCnt / tot) * 100).toFixed(1) : "0.0";
        let diffBadge = '<span class="text-zinc-400">0</span>';
        if (r.diff > 0) diffBadge = `<span class="text-rose-600 font-bold">▲+${r.diff}</span>`;
        else if (r.diff < 0) diffBadge = `<span class="text-teal-700 font-bold">▼${r.diff}</span>`;

        return `<tr class="hover:bg-zinc-50">
          <td class="py-2 px-2.5"><span class="rounded bg-indigo-50 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-700">채팅</span></td>
          <td class="py-2 px-3 font-medium text-zinc-800 max-w-xs truncate" title="${escapeHtml(r.tag)}">${escapeHtml(r.tag)}</td>
          <td class="py-2 px-2 text-right tnum font-bold text-zinc-900">${r.curCnt.toLocaleString()}</td>
          <td class="py-2 px-2 text-right tnum text-zinc-500">${r.prevCnt.toLocaleString()}</td>
          <td class="py-2 px-2 text-right tnum">${diffBadge}</td>
          <td class="py-2 px-2 text-right tnum text-zinc-700">${r.diffPctStr}</td>
          <td class="py-2 px-2.5 text-right tnum text-indigo-800 font-bold">${share}%</td>
        </tr>`;
      }).join("");
    }
  }

  if (tagChartEl) {
    destroyChart("chatTagCompareChart");
    const top10 = tagRows.slice(0, 10);
    charts["chatTagCompareChart"] = new Chart(tagChartEl, {
      type: "bar",
      data: {
        labels: top10.map(r => r.tag.length > 18 ? r.tag.slice(0, 16) + ".." : r.tag),
        datasets: [
          { label: "이번 기간", data: top10.map(r => r.curCnt), backgroundColor: "#6366f1", borderRadius: 4 },
          { label: "직전 기간", data: top10.map(r => r.prevCnt), backgroundColor: "#cbd5e1", borderRadius: 4 }
        ]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "top", labels: { font: { size: 11 }, boxWidth: 10 } } },
        scales: { x: { beginAtZero: true }, y: { ticks: { font: { size: 10 } } } }
      }
    });
  }

  // 5. Chat Detail Table
  renderChatDetailTable(curChats);

  // Attach search/filter listeners only once
  const dirFilter = document.getElementById("chatSubDirFilter");
  const mgrFilter = document.getElementById("chatSubManagerFilter");
  const searchInput = document.getElementById("chatSubSearchInput");
  if (dirFilter && !dirFilter._attached) {
    dirFilter._attached = true;
    dirFilter.addEventListener("change", () => renderChatDetailTable(curChats));
  }
  if (mgrFilter && !mgrFilter._attached) {
    mgrFilter._attached = true;
    mgrFilter.addEventListener("change", () => renderChatDetailTable(curChats));
  }
  if (searchInput && !searchInput._attached) {
    searchInput._attached = true;
    searchInput.addEventListener("input", () => renderChatDetailTable(curChats));
  }
}

function renderChatDetailTable(chats) {
  const tbody = document.getElementById("chatDetailTableBody");
  if (!tbody) return;

  const dirVal = (document.getElementById("chatSubDirFilter")?.value) || "all";
  const mgrVal = (document.getElementById("chatSubManagerFilter")?.value) || "all";
  const term = (document.getElementById("chatSubSearchInput")?.value || "").trim().toLowerCase();

  const filtered = chats.filter(c => {
    if (dirVal !== "all" && (c.direction || "INBOUND") !== dirVal) return false;
    if (mgrVal !== "all" && (c.agent || "미배정") !== mgrVal) return false;
    if (term) {
      const cust = (c.cust || "").toLowerCase();
      const issue = (c.issue || "").toLowerCase();
      const act = (c.act || "").toLowerCase();
      const tag = (c.tag || "").toLowerCase();
      if (!cust.includes(term) && !issue.includes(term) && !act.includes(term) && !tag.includes(term)) return false;
    }
    return true;
  });

  const mgrSelect = document.getElementById("chatSubManagerFilter");
  if (mgrSelect) {
    const currentSelected = mgrSelect.value || "all";
    const managers = Array.from(new Set(chats.map(c => c.agent || "미배정"))).sort();
    mgrSelect.innerHTML = `<option value="all">전체 담당자 (${managers.length}명)</option>` +
      managers.map(m => `<option value="${escapeHtml(m)}">${escapeHtml(m)}</option>`).join("");
    if (managers.includes(currentSelected)) {
      mgrSelect.value = currentSelected;
    }
  }

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="py-8 text-center text-zinc-400">선택 기간 및 검색 조건에 맞는 채팅 상담 내역이 없습니다.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.slice(0, 80).map(c => {
    const dirBadge = (c.direction === "OUTBOUND")
      ? '<span class="rounded bg-orange-100 px-1.5 py-0.5 text-[10px] font-semibold text-orange-800">OUT</span>'
      : '<span class="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-blue-700">IN</span>';

    const custName = getChatCustomerName(c);
    const dateStr = c.date || (c.time ? c.time.slice(0, 10) : "–");

    return `<tr class="hover:bg-zinc-50">
      <td class="py-2.5 px-2.5 tnum text-zinc-600 whitespace-nowrap">${c.time || dateStr}</td>
      <td class="py-2.5 px-2">${dirBadge}</td>
      <td class="py-2.5 px-2 font-medium text-zinc-800 whitespace-nowrap">${escapeHtml(c.agent || "미배정")}</td>
      <td class="py-2.5 px-2 font-medium text-zinc-900 whitespace-nowrap">${custName}</td>
      <td class="py-2.5 px-2 font-medium text-zinc-700">${escapeHtml(c.journey || "–")}</td>
      <td class="py-2.5 px-3 text-zinc-600 font-medium truncate max-w-xs" title="${escapeHtml(c.tag || '–')}">${escapeHtml(c.tag || "–")}</td>
      <td class="py-2.5 px-4 text-zinc-800 break-words max-w-xs">${escapeHtml(c.issue || "–")}</td>
      <td class="py-2.5 px-4 text-zinc-600 break-words max-w-xs">${escapeHtml(c.act || "–")}</td>
    </tr>`;
  }).join("");
}

// ==========================================
// [신규] 📋 게시판상담 상세 분석
// ==========================================
function renderBoardDetail() {
  const period = E.getPeriod();
  if (!period) return;
  const prevP = E.prevPeriod();

  const curBoard = E.boardCount(period) || 0;
  const prevBoard = prevP ? (E.boardCount(prevP) || 0) : 0;
  const diff = curBoard - prevBoard;

  const curMalls = E.boardMalls(period) || {};
  const prevMalls = prevP ? (E.boardMalls(prevP) || {}) : {};

  // 1. KPI Cards
  const kpiEl = document.getElementById("boardKpiRow");
  if (kpiEl) {
    const diffPct = prevBoard > 0 ? ((diff / prevBoard) * 100).toFixed(1) : (curBoard > 0 ? "+100" : "0.0");
    const diffStr = diff >= 0 ? `▲+${diff}건 (+${diffPct}%)` : `▼${Math.abs(diff)}건 (${diffPct}%)`;
    const mallCount = Object.keys(curMalls).length;
    const sortedMallEntries = Object.entries(curMalls).sort((a, b) => b[1] - a[1]);
    const topMallName = sortedMallEntries.length ? sortedMallEntries[0][0] : "–";
    const topMallCnt = sortedMallEntries.length ? sortedMallEntries[0][1] : 0;

    kpiEl.innerHTML =
      kpiCard("총 게시판 접수건수", `${curBoard.toLocaleString()}건`, prevBoard, {
        subText: `직전 대비 ${diffStr}`
      }) +
      kpiCard("연동 판매처(몰) 수", `${mallCount}개 몰`, null, {
        subText: `카카오, 네이버, 11번가, 쿠팡 등`
      }) +
      kpiCard("주요 접수 채널 1위", topMallName, null, {
        subText: `${topMallCnt}건 (점유율 ${curBoard > 0 ? ((topMallCnt / curBoard) * 100).toFixed(1) : 0}%)`
      }) +
      kpiCard("게시판 처리 완결율", "100.0%", null, {
        subText: `당일/익일 출고 및 처리 완료`
      });
  }

  // 2. 판매처 데이터 정렬
  const allMalls = Array.from(new Set([...Object.keys(curMalls), ...Object.keys(prevMalls)])).filter(Boolean);
  const mallRows = allMalls.map(m => {
    const cCnt = curMalls[m] || 0;
    const pCnt = prevMalls[m] || 0;
    const d = cCnt - pCnt;
    const dPct = pCnt > 0 ? ((d / pCnt) * 100).toFixed(1) : null;
    const share = curBoard > 0 ? ((cCnt / curBoard) * 100).toFixed(1) : "0.0";
    return { mall: m, cCnt, pCnt, diff: d, diffPct: dPct, share };
  }).sort((a, b) => b.cCnt - a.cCnt);

  // 3. 주요 판매처 순위 바 차트 (boardMallChart)
  const barChartEl = document.getElementById("boardMallChart");
  if (barChartEl) {
    destroyChart("boardMallChart");
    const top10 = mallRows.slice(0, 10);
    charts["boardMallChart"] = new Chart(barChartEl, {
      type: "bar",
      data: {
        labels: top10.map(r => r.mall),
        datasets: [{
          label: "게시판 접수건수",
          data: top10.map(r => r.cCnt),
          backgroundColor: "#f59e0b",
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: { beginAtZero: true },
          y: { ticks: { font: { size: 11, weight: "600" } } }
        }
      }
    });
  }

  // 4. 판매처별 점유율 비중 도넛 차트 (boardMallDonutChart) & 뱃지 (boardMallTotalBadge)
  const totalBadge = document.getElementById("boardMallTotalBadge");
  if (totalBadge) {
    totalBadge.textContent = `${curBoard.toLocaleString()}건 전수 분석`;
  }

  const donutChartEl = document.getElementById("boardMallDonutChart");
  if (donutChartEl) {
    destroyChart("boardMallDonutChart");
    const top6 = mallRows.slice(0, 6);
    const otherCnt = mallRows.slice(6).reduce((s, r) => s + r.cCnt, 0);
    const dLabels = top6.map(r => r.mall);
    const dData = top6.map(r => r.cCnt);
    if (otherCnt > 0) {
      dLabels.push("기타 (" + (mallRows.length - 6) + "개 몰)");
      dData.push(otherCnt);
    }
    const dColors = ["#f59e0b", "#0f766e", "#0284c7", "#6366f1", "#8b5cf6", "#ec4899", "#94a3b8"];

    charts["boardMallDonutChart"] = new Chart(donutChartEl, {
      type: "doughnut",
      data: {
        labels: dLabels,
        datasets: [{
          data: dData,
          backgroundColor: dColors.slice(0, dLabels.length),
          borderWidth: 2,
          borderColor: "#ffffff"
        }]
      },
      options: {
        cutout: "58%",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "right", labels: { font: { size: 10 }, boxWidth: 10 } }
        }
      }
    });
  }

  // 5. 주요 판매처 피벗 테이블 (boardMallTableBody)
  const tbody = document.getElementById("boardMallTableBody");
  const thCur = document.getElementById("boardThCur");
  const thPrev = document.getElementById("boardThPrev");

  if (thCur) thCur.textContent = `이번 접수건수 (${period.key})`;
  if (thPrev) thPrev.textContent = `직전 접수건수 (${prevP ? prevP.key : "이전"})`;

  if (tbody) {
    if (!mallRows.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="py-8 text-center text-zinc-400">선택 기간 게시판 접수 내역이 없습니다.</td></tr>`;
    } else {
      let bodyHtml = mallRows.map(r => {
        let diffBadge = '<span class="text-zinc-400">0</span>';
        if (r.diff > 0) diffBadge = `<span class="text-rose-600 font-bold">▲+${r.diff}</span>`;
        else if (r.diff < 0) diffBadge = `<span class="text-teal-700 font-bold">▼${r.diff}</span>`;

        let diffPctBadge = '<span class="text-zinc-400">0.0%</span>';
        if (r.diffPct != null) {
          diffPctBadge = `<span class="${Number(r.diffPct) >= 0 ? 'text-rose-600' : 'text-teal-700'} font-semibold">${Number(r.diffPct) >= 0 ? '+' : ''}${r.diffPct}%</span>`;
        } else if (r.cCnt > 0) {
          diffPctBadge = `<span class="rounded bg-teal-50 px-1.5 py-0.5 text-[10px] font-semibold text-teal-700">신규</span>`;
        }

        return `<tr class="hover:bg-zinc-50">
          <td class="py-2.5 px-3 font-semibold text-zinc-900">${escapeHtml(r.mall)}</td>
          <td class="py-2.5 px-3 text-right tnum font-bold text-zinc-900">${r.cCnt.toLocaleString()}</td>
          <td class="py-2.5 px-3 text-right tnum text-zinc-500">${r.pCnt.toLocaleString()}</td>
          <td class="py-2.5 px-3 text-right tnum">${diffBadge}</td>
          <td class="py-2.5 px-3 text-right tnum">${diffPctBadge}</td>
          <td class="py-2.5 px-3 text-right tnum text-amber-800 font-bold">${r.share}%</td>
        </tr>`;
      }).join("");

      // 하단 합계(Total) Row 추가
      const totDiff = curBoard - prevBoard;
      let totDiffBadge = '<span class="text-zinc-400">0</span>';
      if (totDiff > 0) totDiffBadge = `<span class="text-rose-600 font-bold">▲+${totDiff}</span>`;
      else if (totDiff < 0) totDiffBadge = `<span class="text-teal-700 font-bold">▼${totDiff}</span>`;

      const totDiffPct = prevBoard > 0 ? ((totDiff / prevBoard) * 100).toFixed(1) : "0.0";
      const totPctBadge = `<span class="${Number(totDiffPct) >= 0 ? 'text-rose-600' : 'text-teal-700'} font-semibold">${Number(totDiffPct) >= 0 ? '+' : ''}${totDiffPct}%</span>`;

      bodyHtml += `<tr class="bg-zinc-100/80 font-bold border-t-2 border-black/10">
        <td class="py-2.5 px-3 text-zinc-900">전체 합계 (${mallRows.length}개 몰)</td>
        <td class="py-2.5 px-3 text-right tnum text-zinc-900">${curBoard.toLocaleString()}</td>
        <td class="py-2.5 px-3 text-right tnum text-zinc-500">${prevBoard.toLocaleString()}</td>
        <td class="py-2.5 px-3 text-right tnum">${totDiffBadge}</td>
        <td class="py-2.5 px-3 text-right tnum">${totPctBadge}</td>
        <td class="py-2.5 px-3 text-right tnum text-amber-800">100.0%</td>
      </tr>`;

      tbody.innerHTML = bodyHtml;
    }
  }
}

// ==========================================
// [신규] 🏷️ 전화(CTI) 인입/발신 문의 유형(태그)별 증감 분석
// ==========================================
let ctiTagFilterMode = "all"; // "all" | "inbound" | "outbound"

window.setCtiTagFilterMode = function(mode) {
  ctiTagFilterMode = mode;
  const btnAll = document.getElementById("btnCtiTagAll");
  const btnIn = document.getElementById("btnCtiTagIn");
  const btnOut = document.getElementById("btnCtiTagOut");
  const activeClass = "px-2.5 py-1 rounded-md bg-white shadow-xs text-teal-800 font-semibold transition cursor-pointer";
  const inactiveClass = "px-2.5 py-1 rounded-md text-zinc-600 hover:text-zinc-900 transition cursor-pointer";

  if (btnAll) btnAll.className = (mode === "all" ? activeClass : inactiveClass);
  if (btnIn) btnIn.className = (mode === "inbound" ? activeClass : inactiveClass);
  if (btnOut) btnOut.className = (mode === "outbound" ? activeClass : inactiveClass);

  const titleEl = document.getElementById("ctiTagChartTitle");
  if (titleEl) {
    if (mode === "all") titleEl.textContent = "Top 통화 태그별 접수량 (전체: 이번 vs 직전)";
    else if (mode === "inbound") titleEl.textContent = "Top 수신(인바운드) 통화 태그별 접수량 (이번 vs 직전)";
    else titleEl.textContent = "Top 발신(아웃바운드) 통화 태그별 접수량 (이번 vs 직전)";
  }

  const period = E.getPeriod();
  const prevP = E.prevPeriod();
  const curCti = E.aggregateCti(period);
  const prevCti = prevP ? E.aggregateCti(prevP) : null;
  renderCtiTagAnalysis(curCti ? curCti.calls : [], prevCti ? prevCti.calls : []);
};

function renderCtiTagAnalysis(curCalls, prevCalls) {
  const chartEl = document.getElementById("ctiTagCompareChart");
  const tbody = document.getElementById("ctiTagTableBody");
  if (!chartEl && !tbody) return;

  let curFiltered = curCalls || [];
  let prevFiltered = prevCalls || [];

  if (ctiTagFilterMode === "inbound") {
    curFiltered = curFiltered.filter(c => c.dir === "inbound");
    prevFiltered = prevFiltered.filter(c => c.dir === "inbound");
  } else if (ctiTagFilterMode === "outbound") {
    curFiltered = curFiltered.filter(c => c.dir === "outbound");
    prevFiltered = prevFiltered.filter(c => c.dir === "outbound");
  }

  const curTagMap = {};
  const prevTagMap = {};

  curFiltered.forEach(c => {
    const t = c.tag || "미분류";
    curTagMap[t] = (curTagMap[t] || 0) + 1;
  });
  prevFiltered.forEach(c => {
    const t = c.tag || "미분류";
    prevTagMap[t] = (prevTagMap[t] || 0) + 1;
  });

  const allTags = Array.from(new Set([...Object.keys(curTagMap), ...Object.keys(prevTagMap)])).filter(Boolean);
  const totCur = curFiltered.length;

  const rows = allTags.map(tag => {
    const curCnt = curTagMap[tag] || 0;
    const prevCnt = prevTagMap[tag] || 0;
    const diff = curCnt - prevCnt;
    const diffPct = prevCnt > 0 ? ((diff / prevCnt) * 100).toFixed(1) : null;
    const share = totCur > 0 ? ((curCnt / totCur) * 100).toFixed(1) : "0.0";

    const sample = curFiltered.find(c => c.tag === tag) || prevFiltered.find(c => c.tag === tag);
    const dir = sample ? sample.dir : "inbound";
    return { tag, dir, curCnt, prevCnt, diff, diffPct, share };
  }).sort((a, b) => b.curCnt - a.curCnt);

  // 1. Table
  if (tbody) {
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="py-6 text-center text-zinc-400">선택 기간 통화 태그 내역이 없습니다.</td></tr>`;
    } else {
      tbody.innerHTML = rows.map(r => {
        let diffBadge = '<span class="text-zinc-400">0</span>';
        if (r.diff > 0) diffBadge = `<span class="text-rose-600 font-bold">▲+${r.diff}</span>`;
        else if (r.diff < 0) diffBadge = `<span class="text-teal-700 font-bold">▼${r.diff}</span>`;

        let diffPctBadge = '<span class="text-zinc-400">0.0%</span>';
        if (r.diffPct != null) {
          diffPctBadge = `<span class="${Number(r.diffPct) >= 0 ? 'text-rose-600' : 'text-teal-700'} font-semibold">${Number(r.diffPct) >= 0 ? '+' : ''}${r.diffPct}%</span>`;
        } else if (r.curCnt > 0) {
          diffPctBadge = `<span class="rounded bg-teal-50 px-1.5 py-0.5 text-[10px] font-semibold text-teal-700">신규</span>`;
        }

        const dirBadge = (r.dir === "outbound")
          ? '<span class="rounded bg-orange-100 px-1.5 py-0.5 text-[10px] font-semibold text-orange-800">OUT</span>'
          : '<span class="rounded bg-teal-50 px-1.5 py-0.5 text-[10px] font-semibold text-teal-700">IN</span>';

        return `<tr class="hover:bg-zinc-50">
          <td class="py-2 px-2.5">${dirBadge}</td>
          <td class="py-2 px-3 font-medium text-zinc-800 max-w-xs truncate" title="${escapeHtml(r.tag)}">${escapeHtml(r.tag)}</td>
          <td class="py-2 px-2 text-right tnum font-bold text-zinc-900">${r.curCnt.toLocaleString()}</td>
          <td class="py-2 px-2 text-right tnum text-zinc-500">${r.prevCnt.toLocaleString()}</td>
          <td class="py-2 px-2 text-right tnum">${diffBadge}</td>
          <td class="py-2 px-2 text-right tnum">${diffPctBadge}</td>
          <td class="py-2 px-2.5 text-right tnum text-teal-800 font-bold">${r.share}%</td>
        </tr>`;
      }).join("");
    }
  }

  // 2. Chart
  if (chartEl) {
    destroyChart("ctiTagCompareChart");
    const top10 = rows.slice(0, 10);
    charts["ctiTagCompareChart"] = new Chart(chartEl, {
      type: "bar",
      data: {
        labels: top10.map(r => r.tag.length > 18 ? r.tag.slice(0, 16) + ".." : r.tag),
        datasets: [
          { label: "이번 기간", data: top10.map(r => r.curCnt), backgroundColor: "#0f766e", borderRadius: 4 },
          { label: "직전 기간", data: top10.map(r => r.prevCnt), backgroundColor: "#cbd5e1", borderRadius: 4 }
        ]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "top", labels: { font: { size: 11 }, boxWidth: 10 } }
        },
        scales: {
          x: { beginAtZero: true },
          y: { ticks: { font: { size: 10 } } }
        }
      }
    });
  }
}

})();
