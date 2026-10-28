# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('dashboard/render.js', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Clean up stray functions around line 2547 (renderClaimCategoryBreakdown, renderClaimTable, etc.)
# Let's find where barChart ends
pos_barchart = text.find('function barChart(')
if pos_barchart != -1:
    pos_onclick = text.find('onClick: opts.onClick,', pos_barchart)
    pos_barchart_end = text.find('function doughnutChart(', pos_onclick)
    if pos_barchart_end != -1:
        # Check if stray claim functions were inside here
        mid_chunk = text[pos_onclick:pos_barchart_end]
        if 'renderClaim' in mid_chunk:
            print("Found stray claim functions inside barChart region! Cleaning...")
            clean_barchart_end = """onClick: opts.onClick,
      responsive: true,
      maintainAspectRatio: false
    }
  });
}

"""
            text = text[:pos_onclick] + clean_barchart_end + text[pos_barchart_end:]

# 2. Check if any other stray renderClaim functions exist before switchChannelSubTab
pos_switch = text.find('function switchChannelSubTab(')
pos_switch_end = text.find('function renderCtiAnswerRateTrendChart(')

# Clean out anything between switchChannelSubTab and renderCtiAnswerRateTrendChart
# First let's inspect switchChannelSubTab
pos_switch_brace = text.find('}', pos_switch)
# Find matching brace for switchChannelSubTab
depth = 0
in_switch = False
switch_end_idx = -1
for i in range(pos_switch, len(text)):
    if text[i] == '{':
        depth += 1
        in_switch = True
    elif text[i] == '}':
        depth -= 1
        if in_switch and depth == 0:
            switch_end_idx = i + 1
            break

print("switchChannelSubTab ends at:", switch_end_idx)

# Remove everything between switch_end_idx and pos_switch_end
text = text[:switch_end_idx] + "\n\n" + text[pos_switch_end:]

# 3. Now insert the complete, verified claim module right after switchChannelSubTab!
complete_claim_module = """
// ============================================================================
// 클레임 처리 리드타임 & 세부 태그별 4사분면 리스크 분석 모듈 (고도화 도식화 완성)
// ============================================================================
let claimLeadtimeScope = "period"; // "period" or "all"
let claimWindowDays = 30;          // 한 달(30일) 추적 기본
let claimCallFilterVal = "all";    // "all", "1", "2-3", "4+"
let claimCategoryFilterVal = "all";// "all", "품질", "배송", "휴먼에러", "시스템"
let claimSearchTerm = "";
let claimPage = 1;
const CLAIM_PAGE_SIZE = 20;

function escapeHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function renderClaimLeadtimeDetail() {
  const period = E.getPeriod();
  const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope, claimWindowDays);
  const s = res.summary;

  // 1. 상단 4대 핵심 메트릭 카드 (FCR 1회 종결율 포함)
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
  renderClaimTagMatrix(res.summary.tagBreakdown, res.claims);

  // 5. 통화 횟수별 분포 막대차트 (1회 vs 2~3회 vs 4회+)
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
            color: (ctx) => ["#059669", "#0284c7", "#d97706", "#dc2626"][ctx.dataIndex],
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

  // 7. 상세 원장 테이블 렌더링
  renderClaimTable(res.claims);
}

function renderClaimProcessFlow(s) {
  const elTot = document.getElementById("flowTotalClaims");
  const elFcr = document.getElementById("flowFcrRate");
  const elC1 = document.getElementById("flowCount1");
  const elRep = document.getElementById("flowRepeatRate");
  const elC23 = document.getElementById("flowCount23");
  const elRisk = document.getElementById("flowRiskRate");
  const elC4 = document.getElementById("flowCount4Plus");

  if (elTot) elTot.textContent = `${s.totalClaims.toLocaleString()}건`;
  if (elFcr) elFcr.textContent = `FCR ${s.fcrRate}%`;
  if (elC1) elC1.textContent = `${s.callDist.count1.toLocaleString()}건 (${s.fcrRate}%)`;
  if (elRep) elRep.textContent = `재통화 ${s.repeatRate}%`;
  if (elC23) elC23.textContent = `${s.callDist.count2_3.toLocaleString()}건`;
  const riskRate = s.totalClaims > 0 ? ((s.callDist.count4_plus / s.totalClaims) * 100).toFixed(1) : "0.0";
  if (elRisk) elRisk.textContent = `위험 ${riskRate}%`;
  if (elC4) elC4.textContent = `${s.callDist.count4_plus.toLocaleString()}건 (${riskRate}%)`;
}

function renderClaimCategoryBreakdown(categories) {
  const tbody = document.getElementById("claimCategoryTableBody");
  if (!tbody || !categories) return;

  tbody.innerHTML = categories.map((c, idx) => `
    <tr class="${idx % 2 === 1 ? 'bg-zinc-50/50' : 'bg-white'} hover:bg-zinc-100/60 transition">
      <td class="py-2 px-2.5 font-medium text-zinc-900">${escapeHtml(c.category)}</td>
      <td class="py-2 px-2 text-right tnum font-semibold text-zinc-800">${Number(c.total).toLocaleString()}건</td>
      <td class="py-2 px-2 text-right tnum text-zinc-600">${Number(c.repeats).toLocaleString()}건</td>
      <td class="py-2 px-2 text-right tnum font-bold ${Number(c.repeatRate) >= 20 ? 'text-rose-600 bg-rose-50/40' : 'text-zinc-700'}">${c.repeatRate}%</td>
      <td class="py-2 px-2 text-right tnum text-zinc-700">${c.avgCalls}회</td>
      <td class="py-2 px-2 text-right tnum font-bold ${Number(c.avgLeadHours) >= 24 ? 'text-amber-700' : 'text-teal-800'}">${c.avgLeadHours}h (${c.avgLeadDays}일)</td>
      <td class="py-2 px-2 text-right tnum text-zinc-600">${c.avgDurationMin}분</td>
    </tr>
  `).join("");

  destroyChart("claimCategoryBarChart");
  const catChartEl = document.getElementById("claimCategoryBarChart");
  if (catChartEl && categories.length > 0) {
    const labels = categories.map(c => c.category.split(" ")[0]);
    const repeatRates = categories.map(c => Number(c.repeatRate));
    const colors = categories.map(c => Number(c.repeatRate) >= 20 ? "#e11d48" : "#0f766e");

    charts["claimCategoryBarChart"] = new Chart(catChartEl, {
      type: "bar",
      data: {
        labels,
        datasets: [{
          label: "재통화율 (%)",
          data: repeatRates,
          backgroundColor: colors,
          borderRadius: 4,
          maxBarThickness: 24
        }]
      },
      options: {
        indexAxis: "y",
        layout: { padding: { right: 35 } },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `재통화율: ${ctx.raw}% (평균리드: ${categories[ctx.dataIndex].avgLeadHours}h)`
            }
          },
          datalabels: {
            display: true,
            anchor: "end",
            align: "right",
            font: { weight: "bold", size: 10 },
            color: (ctx) => colors[ctx.dataIndex],
            formatter: (v) => `${v}%`
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            max: Math.max(...repeatRates, 50) + 10,
            grid: { color: "rgba(0,0,0,.05)" },
            ticks: { font: { size: 10 }, callback: (v) => `${v}%` }
          },
          y: { grid: { display: false }, ticks: { font: { size: 11, weight: "500" } } }
        },
        responsive: true,
        maintainAspectRatio: false
      }
    });
  }
}

function renderClaimTagMatrix(tagBreakdown, claims) {
  const tbody = document.getElementById("claimTagTableBody");
  if (!tbody || !tagBreakdown) return;

  tbody.innerHTML = tagBreakdown.map((t) => {
    let qBadge = "";
    if (t.quadrant === "1") qBadge = `<span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold bg-rose-100 text-rose-800 ring-1 ring-rose-600/20">🚨 1사분면 최우선</span>`;
    else if (t.quadrant === "2") qBadge = `<span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold bg-amber-100 text-amber-800 ring-1 ring-amber-600/20">⏱️ 2사분면 장기</span>`;
    else if (t.quadrant === "4") qBadge = `<span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold bg-sky-100 text-sky-800 ring-1 ring-sky-600/20">🔁 4사분면 핑퐁</span>`;
    else qBadge = `<span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-emerald-100 text-emerald-800 ring-1 ring-emerald-600/20">✅ 3사분면 신속</span>`;

    return `
      <tr class="hover:bg-zinc-50 transition">
        <td class="py-2 px-2.5 font-medium text-zinc-800 max-w-[170px] truncate" title="${escapeHtml(t.tag)}">
          ${escapeHtml(t.tag)}
        </td>
        <td class="py-2 px-2 text-right tnum font-semibold text-zinc-900">${t.total}건</td>
        <td class="py-2 px-2 text-right tnum font-bold ${t.repeatRate >= 20 ? 'text-rose-600' : 'text-zinc-700'}">${t.repeatRate}%</td>
        <td class="py-2 px-2 text-right tnum font-semibold ${t.avgLeadHours >= 24 ? 'text-amber-700' : 'text-teal-800'}">${t.avgLeadHours}h</td>
        <td class="py-2 px-2 text-center">${qBadge}</td>
        <td class="py-2 px-2 text-center">
          <button type="button" class="btn-tag-filter rounded bg-zinc-100 px-2 py-0.5 text-[10px] font-semibold text-teal-800 hover:bg-teal-600 hover:text-white transition cursor-pointer" data-tag="${escapeHtml(t.tag)}">
            필터
          </button>
        </td>
      </tr>
    `;
  }).join("");

  tbody.querySelectorAll(".btn-tag-filter").forEach(b => {
    b.addEventListener("click", (e) => {
      e.stopPropagation();
      const targetTag = b.getAttribute("data-tag");
      const searchInput = document.getElementById("claimSearchInput");
      if (searchInput) searchInput.value = targetTag;
      claimSearchTerm = targetTag;
      claimPage = 1;
      renderClaimTable(claims);

      const tblSection = document.getElementById("claimDetailTableBody");
      if (tblSection) tblSection.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  });

  destroyChart("claimTagMatrixChart");
  const chartEl = document.getElementById("claimTagMatrixChart");
  if (!chartEl || tagBreakdown.length === 0) return;

  const bubbleData = tagBreakdown.map(t => ({
    x: t.repeatRate,
    y: t.avgLeadHours,
    r: t.r,
    tag: t.tag,
    total: t.total,
    quadrant: t.quadrant,
    avgCalls: t.avgCalls
  }));

  const bgColors = bubbleData.map(d => {
    if (d.quadrant === "1") return "rgba(225, 29, 72, 0.75)";
    if (d.quadrant === "2") return "rgba(245, 158, 11, 0.75)";
    if (d.quadrant === "4") return "rgba(2, 132, 199, 0.75)";
    return "rgba(16, 185, 129, 0.75)";
  });

  const borderColors = bubbleData.map(d => {
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
        borderWidth: 1.5
      }]
    },
    options: {
      layout: { padding: 12 },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (items) => items.length ? items[0].raw.tag : "",
            label: (ctx) => [
              `총 건수: ${ctx.raw.total.toLocaleString()}건 (평균통화: ${ctx.raw.avgCalls}회)`,
              `재통화율: ${ctx.raw.x}%`,
              `평균 리드타임: ${ctx.raw.y}시간`
            ]
          }
        },
        datalabels: {
          display: (ctx) => {
            const d = ctx.dataset.data[ctx.dataIndex];
            return d.total >= 40 || d.quadrant === "1";
          },
          align: "top",
          offset: 2,
          font: { weight: "600", size: 10 },
          color: (ctx) => borderColors[ctx.dataIndex],
          formatter: (v) => {
            const parts = v.tag.split("/");
            return parts[parts.length - 1];
          }
        }
      },
      scales: {
        x: {
          min: 0,
          max: Math.max(...bubbleData.map(d => d.x), 75) + 5,
          title: { display: true, text: "재통화율 (%) ➔", font: { size: 11, weight: "bold" }, color: "#64748b" },
          grid: { color: "rgba(0,0,0,.06)" },
          ticks: { font: { size: 10 }, callback: (v) => `${v}%` }
        },
        y: {
          beginAtZero: true,
          title: { display: true, text: "평균 리드타임 (시간) ➔", font: { size: 11, weight: "bold" }, color: "#64748b" },
          grid: { color: "rgba(0,0,0,.06)" },
          ticks: { font: { size: 10 }, callback: (v) => `${v}h` }
        }
      },
      responsive: true,
      maintainAspectRatio: false
    }
  });
}

function renderClaimTable(claims) {
  const tbody = document.getElementById("claimDetailTableBody");
  const countBadge = document.getElementById("claimTableCountBadge");
  const paginationEl = document.getElementById("claimPagination");
  if (!tbody) return;

  let filtered = claims.filter(c => {
    if (claimCallFilterVal === "1" && c.call_count !== 1) return false;
    if (claimCallFilterVal === "2-3" && (c.call_count < 2 || c.call_count > 3)) return false;
    if (claimCallFilterVal === "4+" && c.call_count < 4) return false;

    if (claimCategoryFilterVal !== "all") {
      if (claimCategoryFilterVal === "품질" && !c.category.includes("품질")) return false;
      if (claimCategoryFilterVal === "배송" && !c.category.includes("배송")) return false;
      if (claimCategoryFilterVal === "휴먼에러" && !c.category.includes("휴먼에러")) return false;
      if (claimCategoryFilterVal === "시스템" && !c.category.includes("시스템")) return false;
    }

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

  const totalPages = Math.max(1, Math.ceil(filtered.length / CLAIM_PAGE_SIZE));
  if (claimPage > totalPages) claimPage = 1;
  const startIdx = (claimPage - 1) * CLAIM_PAGE_SIZE;
  const pageItems = filtered.slice(startIdx, startIdx + CLAIM_PAGE_SIZE);

  if (pageItems.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" class="py-8 text-center text-zinc-400">조회된 클레임 통화 내역이 없습니다.</td></tr>`;
    if (paginationEl) paginationEl.innerHTML = "";
    return;
  }

  tbody.innerHTML = pageItems.map((c) => {
    let callBadgeClass = "bg-teal-50 text-teal-700 ring-teal-600/20";
    if (c.call_count >= 4) callBadgeClass = "bg-rose-50 text-rose-700 ring-rose-600/20 font-bold";
    else if (c.call_count >= 2) callBadgeClass = "bg-amber-50 text-amber-700 ring-amber-600/20 font-semibold";

    let leadBadge = "";
    if (c.lead_time_hours <= 24.0) {
      leadBadge = `<span class="inline-flex items-center rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">당일(${c.lead_time_hours}h)</span>`;
    } else {
      leadBadge = `<span class="inline-flex items-center rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-800 ring-1 ring-inset ring-amber-600/20">${c.lead_time_days}일(${c.lead_time_hours}h)</span>`;
    }

    const issueSnippet = (c.issue || "-").replace(/\\n/g, " ");
    const actSnippet = (c.act || "-").replace(/\\n/g, " ");

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
            <span class="text-zinc-400 font-medium">문의:</span> ${escapeHtml((call.issue || "-").replace(/\\n/g, " "))}
            <span class="text-teal-600 font-medium ml-2">조치:</span> ${escapeHtml((call.act || "-").replace(/\\n/g, " "))}
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
  if (row) {
    row.classList.toggle("hidden");
    if (chevron) {
      chevron.textContent = row.classList.contains("hidden") ? "▶" : "▼";
    }
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

  const ws = wb.addWorksheet("클레임_리드타임_원장");
  ws.columns = [
    { header: "Claim ID", key: "claim_id", width: 22 },
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

  ws.getRow(1).font = { bold: true, color: { argb: "FFFFFFFF" } };
  ws.getRow(1).fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF0F766E" } };
  ws.getRow(1).alignment = { vertical: "middle", horizontal: "center" };

  claims.forEach((c) => {
    ws.addRow({
      claim_id: c.claim_id,
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
"""

text = text[:switch_end_idx] + complete_claim_module + text[switch_end_idx:]

with open('dashboard/render.js', 'w', encoding='utf-8') as f:
    f.write(text)

print("Successfully cleaned and installed complete claim module into render.js!")
