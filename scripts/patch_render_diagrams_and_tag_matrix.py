# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('dashboard/render.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Locate renderClaimLeadtimeDetail
pos = text.find('function renderClaimLeadtimeDetail() {')
if pos == -1:
    print("renderClaimLeadtimeDetail not found")
    sys.exit()

# We can replace the renderClaimCategoryBreakdown section to include Process Flow, Category Breakdown, and Tag Matrix
target_anchor = "function renderClaimCategoryBreakdown(categories) {"
pos_target = text.find(target_anchor)
if pos_target == -1:
    print("renderClaimCategoryBreakdown not found")
    sys.exit()

# In renderClaimLeadtimeDetail, add calls to renderClaimProcessFlow and renderClaimTagMatrix
call_anchor = "renderClaimCategoryBreakdown(res.summary.categoryBreakdown);"
new_calls = """renderClaimProcessFlow(res.summary);
  renderClaimCategoryBreakdown(res.summary.categoryBreakdown);
  renderClaimTagMatrix(res.summary.tagBreakdown, res.claims);"""

text = text.replace(call_anchor, new_calls, 1)

new_functions = """function renderClaimProcessFlow(s) {
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

  // Attach filter events to tag buttons
  tbody.querySelectorAll(".btn-tag-filter").forEach(b => {
    b.addEventListener("click", (e) => {
      e.stopPropagation();
      const targetTag = b.getAttribute("data-tag");
      const searchInput = document.getElementById("claimSearchInput");
      if (searchInput) searchInput.value = targetTag;
      claimSearchTerm = targetTag;
      claimPage = 1;
      renderClaimTable(claims);

      // Scroll to table smoothly
      const tblSection = document.getElementById("claimDetailTableBody");
      if (tblSection) tblSection.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  });

  // Render 4-Quadrant Bubble Chart
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
            return d.total >= 40 || d.quadrant === "1"; // Show labels for significant or high-risk tags
          },
          align: "top",
          offset: 2,
          font: { weight: "600", size: 10 },
          color: (ctx) => borderColors[ctx.dataIndex],
          formatter: (v) => {
            const parts = v.tag.split("/");
            return parts[parts.length - 1]; // Short tag name
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

text = text[:pos_target] + new_functions + text[pos_target:]

with open('dashboard/render.js', 'w', encoding='utf-8') as f:
    f.write(text)
print("Successfully patched render.js with Process Flow & 4-Quadrant Bubble Chart!")
