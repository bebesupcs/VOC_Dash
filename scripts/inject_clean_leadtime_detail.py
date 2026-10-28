# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('dashboard/render.js', 'r', encoding='utf-8') as f:
    text = f.read()

pos = text.find('function renderClaimCategoryBreakdown(categories) {')
if pos == -1:
    print("Target not found!")
    sys.exit()

claim_leadtime_code = """let claimLeadtimeScope = "period"; // "period" or "all"
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

"""

text = text[:pos] + claim_leadtime_code + text[pos:]

# Add window.toggleClaimRow = toggleClaimRow if not present
if 'window.toggleClaimRow = toggleClaimRow;' not in text:
    text = text.replace('exportClaimAnalysisToExcel();', 'exportClaimAnalysisToExcel();\nwindow.toggleClaimRow = toggleClaimRow;')

with open('dashboard/render.js', 'w', encoding='utf-8') as f:
    f.write(text)

print("Successfully injected clean claim leadtime detail into render.js!")
