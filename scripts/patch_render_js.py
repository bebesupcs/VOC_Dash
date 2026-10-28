# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('dashboard/render.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update switchChannelSubTab
subtab_target = """  const overviewSec = document.getElementById("channelOverviewSection");
  const ctiSec = document.getElementById("ctiDetailSection");
  const chatSec = document.getElementById("chatDetailSection");
  const boardSec = document.getElementById("boardDetailSection");

  const btnOverview = document.getElementById("btnSubChannelOverview");
  const btnCti = document.getElementById("btnSubCtiDetail");
  const btnChat = document.getElementById("btnSubChatDetail");
  const btnBoard = document.getElementById("btnSubBoardDetail");
  const btnAlf = document.getElementById("btnSubAlfDetail");"""

subtab_replacement = """  const overviewSec = document.getElementById("channelOverviewSection");
  const ctiSec = document.getElementById("ctiDetailSection");
  const chatSec = document.getElementById("chatDetailSection");
  const boardSec = document.getElementById("boardDetailSection");
  const claimSec = document.getElementById("claimLeadtimeSection");

  const btnOverview = document.getElementById("btnSubChannelOverview");
  const btnCti = document.getElementById("btnSubCtiDetail");
  const btnChat = document.getElementById("btnSubChatDetail");
  const btnBoard = document.getElementById("btnSubBoardDetail");
  const btnAlf = document.getElementById("btnSubAlfDetail");
  const btnClaim = document.getElementById("btnSubClaimLeadtimeDetail");"""

subtab_hide_target = """  if (overviewSec) overviewSec.hidden = (tab !== "overview");
  if (ctiSec) ctiSec.hidden = (tab !== "cti");
  if (chatSec) chatSec.hidden = (tab !== "chat");
  if (boardSec) boardSec.hidden = (tab !== "board");

  if (btnOverview) btnOverview.className = (tab === "overview" ? activeBtnClass : inactiveBtnClass);
  if (btnCti) btnCti.className = (tab === "cti" ? activeBtnClass : inactiveBtnClass);
  if (btnChat) btnChat.className = (tab === "chat" ? activeBtnClass : inactiveBtnClass);
  if (btnBoard) btnBoard.className = (tab === "board" ? activeBtnClass : inactiveBtnClass);
  if (btnAlf) btnAlf.className = inactiveBtnClass;"""

subtab_hide_replacement = """  if (overviewSec) overviewSec.hidden = (tab !== "overview");
  if (ctiSec) ctiSec.hidden = (tab !== "cti");
  if (chatSec) chatSec.hidden = (tab !== "chat");
  if (boardSec) boardSec.hidden = (tab !== "board");
  if (claimSec) claimSec.hidden = (tab !== "claim");

  if (btnOverview) btnOverview.className = (tab === "overview" ? activeBtnClass : inactiveBtnClass);
  if (btnCti) btnCti.className = (tab === "cti" ? activeBtnClass : inactiveBtnClass);
  if (btnChat) btnChat.className = (tab === "chat" ? activeBtnClass : inactiveBtnClass);
  if (btnBoard) btnBoard.className = (tab === "board" ? activeBtnClass : inactiveBtnClass);
  if (btnClaim) btnClaim.className = (tab === "claim" ? activeBtnClass : inactiveBtnClass);
  if (btnAlf) btnAlf.className = inactiveBtnClass;"""

subtab_render_target = """  } else if (tab === "board") {
    renderSubBoardDetail();
  }
}"""

subtab_render_replacement = """  } else if (tab === "board") {
    renderSubBoardDetail();
  } else if (tab === "claim") {
    renderClaimLeadtimeDetail();
  }
}"""

# 2. Update renderChannel subtab call
render_channel_target = """  if (channelSubTab === "cti") renderCti();
  else if (channelSubTab === "chat") {
    if (chatAlfMode === "alf") renderAlf();
    else renderSubChatDetail();
  }"""

render_channel_replacement = """  if (channelSubTab === "cti") renderCti();
  else if (channelSubTab === "chat") {
    if (chatAlfMode === "alf") renderAlf();
    else renderSubChatDetail();
  } else if (channelSubTab === "board") {
    renderSubBoardDetail();
  } else if (channelSubTab === "claim") {
    renderClaimLeadtimeDetail();
  }"""

# 3. Claim analysis rendering logic
claim_logic = """
// ==========================================
// 클레임 처리 리드타임 및 통화 분석 (신규 기능)
// ==========================================
let claimLeadtimeScope = "period"; // "period" or "all"
let claimCallFilterVal = "all";    // "all", "1", "2-3", "4+"
let claimSearchTerm = "";
let claimPage = 1;
const CLAIM_PAGE_SIZE = 20;

function renderClaimLeadtimeDetail() {
  const period = E.getPeriod();
  const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope);

  // 1. 상단 메트릭 카드 3개
  const kpiEl = document.getElementById("claimAnalysisKpiRow");
  if (kpiEl) {
    const s = res.summary;
    const durMinInt = Math.floor(s.avgDurationMin);
    const durSecInt = Math.round((s.avgDurationMin - durMinInt) * 60);
    const durDisplay = durMinInt > 0 ? `${durMinInt}분 ${durSecInt}초` : `${durSecInt}초`;

    const multiCalls = s.callDist.count2_3 + s.callDist.count4_plus;
    const multiRate = s.totalClaims > 0 ? ((multiCalls / s.totalClaims) * 100).toFixed(1) : "0.0";

    kpiEl.innerHTML =
      kpiCard("평균 통화 횟수", `건당 ${s.avgCalls}회`, null, {
        subText: `총 클레임 ${s.totalClaims.toLocaleString()}건 중 재통화 발생 ${multiCalls.toLocaleString()}건 (${multiRate}%)`,
        alert: Number(s.avgCalls) >= 1.5
      }) +
      kpiCard("평균 총 통화 시간", `건당 ${s.avgDurationMin}분`, null, {
        subText: `평균 상담시간: ${durDisplay} (원장 실통화 시간 기준)`
      }) +
      kpiCard("평균 클레임 해결 리드타임", `${s.avgLeadTimeHours}시간 (${s.avgLeadTimeDays}일)`, null, {
        subText: `최초 클레임 접수부터 최종 재통화 완료까지 소요`
      });
  }

  // 2. 통화 횟수별 분포 막대차트 (1회 vs 2~3회 vs 4회 이상)
  destroyChart("claimCallCountChart");
  const callChartEl = document.getElementById("claimCallCountChart");
  if (callChartEl) {
    const s = res.summary;
    const tot = s.totalClaims || 1;
    const countData = [s.callDist.count1, s.callDist.count2_3, s.callDist.count4_plus];
    const pctData = countData.map(v => ((v / tot) * 100).toFixed(1));

    const badgeEl = document.getElementById("claimCallCountBadge");
    if (badgeEl) {
      const oneRate = ((s.callDist.count1 / tot) * 100).toFixed(1);
      badgeEl.textContent = `1회 종결율: ${oneRate}%`;
    }

    charts["claimCallCountChart"] = new Chart(callChartEl, {
      type: "bar",
      data: {
        labels: ["1회 해결 (단일 통화)", "2~3회 재통화", "4회 이상 다회 통화"],
        datasets: [{
          label: "클레임 건수",
          data: countData,
          backgroundColor: ["#0f766e", "#f59e0b", "#e11d48"],
          borderRadius: 6,
          maxBarThickness: 56
        }]
      },
      options: {
        layout: { padding: { top: 24 } },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.raw.toLocaleString()}건 (${pctData[ctx.dataIndex]}%)`
            }
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

  // 3. 해결 기간(리드타임) 구간별 건수 히스토그램
  destroyChart("claimLeadtimeChart");
  const ltChartEl = document.getElementById("claimLeadtimeChart");
  if (ltChartEl) {
    const s = res.summary;
    const tot = s.totalClaims || 1;
    const ltData = [s.leadDist.sameDay, s.leadDist.days1_3, s.leadDist.days4_7, s.leadDist.gt7Days];
    const ltPct = ltData.map(v => ((v / tot) * 100).toFixed(1));

    const badgeEl = document.getElementById("claimLeadtimeBadge");
    if (badgeEl) {
      const sameDayRate = ((s.leadDist.sameDay / tot) * 100).toFixed(1);
      badgeEl.textContent = `당일 해결율: ${sameDayRate}%`;
    }

    charts["claimLeadtimeChart"] = new Chart(ltChartEl, {
      type: "bar",
      data: {
        labels: ["당일 해결 (24시간 이내)", "1~3일 (24~72시간)", "4~7일 (72~168시간)", "7일 초과 (최대 14일)"],
        datasets: [{
          label: "클레임 건수",
          data: ltData,
          backgroundColor: ["#10b981", "#0284c7", "#f59e0b", "#ef4444"],
          borderRadius: 6,
          maxBarThickness: 56
        }]
      },
      options: {
        layout: { padding: { top: 24 } },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.raw.toLocaleString()}건 (${ltPct[ctx.dataIndex]}%)`
            }
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

  // 4. 상세 원장 테이블 렌더링
  renderClaimTable(res.claims);
}

function renderClaimTable(claims) {
  const tbody = document.getElementById("claimDetailTableBody");
  const countBadge = document.getElementById("claimTableCountBadge");
  const paginationEl = document.getElementById("claimPagination");
  if (!tbody) return;

  // 필터링 적용
  let filtered = claims.filter(c => {
    if (claimCallFilterVal === "1" && c.call_count !== 1) return false;
    if (claimCallFilterVal === "2-3" && (c.call_count < 2 || c.call_count > 3)) return false;
    if (claimCallFilterVal === "4+" && c.call_count < 4) return false;

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
    tbody.innerHTML = `<tr><td colspan="10" class="py-8 text-center text-zinc-400">조회된 클레임 통화 내역이 없습니다.</td></tr>`;
    if (paginationEl) paginationEl.innerHTML = "";
    return;
  }

  tbody.innerHTML = pageItems.map((c, idx) => {
    let callBadgeClass = "bg-teal-50 text-teal-700 ring-teal-600/20";
    if (c.call_count >= 4) callBadgeClass = "bg-rose-50 text-rose-700 ring-rose-600/20 font-bold";
    else if (c.call_count >= 2) callBadgeClass = "bg-amber-50 text-amber-700 ring-amber-600/20 font-semibold";

    let leadBadge = "";
    if (c.lead_time_hours <= 24.0) {
      leadBadge = `<span class="inline-flex items-center rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">당일(${c.lead_time_hours}h)</span>`;
    } else {
      leadBadge = `<span class="inline-flex items-center rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] font-medium text-zinc-700 ring-1 ring-inset ring-zinc-500/20">${c.lead_time_days}일(${c.lead_time_hours}h)</span>`;
    }

    const issueSnippet = (c.issue || "-").replace(/\\n/g, " ");
    const actSnippet = (c.act || "-").replace(/\\n/g, " ");

    return `
      <tr class="hover:bg-zinc-50/80 transition">
        <td class="py-2.5 px-3 font-mono text-[11px] text-zinc-500">${c.claim_id}</td>
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
        <td class="py-2.5 px-3 text-[11px] text-zinc-700 max-w-[160px] truncate" title="${escapeHtml(c.first_tag)}">
          ${escapeHtml(c.first_tag || "-")}
        </td>
        <td class="py-2.5 px-3 text-[11px] text-zinc-600 whitespace-nowrap">${escapeHtml(c.agent || "-")}</td>
        <td class="py-2.5 px-3 text-[11px] text-zinc-500 max-w-[280px]">
          <div class="truncate text-zinc-800" title="${escapeHtml(issueSnippet)}"><span class="font-medium text-zinc-400">Q:</span> ${escapeHtml(issueSnippet)}</div>
          <div class="truncate text-zinc-500 text-[10px]" title="${escapeHtml(actSnippet)}"><span class="font-medium text-teal-600">A:</span> ${escapeHtml(actSnippet)}</div>
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

async function exportClaimAnalysisToExcel() {
  const period = E.getPeriod();
  const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope);
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
    { header: "고객명", key: "cust", width: 14 },
    { header: "연락처", key: "phone", width: 16 },
    { header: "최초 클레임 일시", key: "first_time", width: 20 },
    { header: "최종 통화 일시", key: "last_time", width: 20 },
    { header: "소요 리드타임(시간)", key: "lead_time_hours", width: 18 },
    { header: "소요 리드타임(일)", key: "lead_time_days", width: 16 },
    { header: "총 통화횟수(회)", key: "call_count", width: 14 },
    { header: "총 통화시간(분)", key: "total_call_duration", width: 16 },
    { header: "클레임 유형(태그)", key: "first_tag", width: 28 },
    { header: "담당 상담사", key: "agent", width: 14 },
    { header: "고객 문의내용", key: "issue", width: 36 },
    { header: "상담원 조치내용", key: "act", width: 36 }
  ];

  // Header style
  ws.getRow(1).font = { bold: true, color: { argb: "FFFFFFFF" } };
  ws.getRow(1).fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF0F766E" } };
  ws.getRow(1).alignment = { vertical: "middle", horizontal: "center" };

  claims.forEach((c) => {
    ws.addRow({
      claim_id: c.claim_id,
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

# 4. Event listener wiring
listener_target = """  const btnSubBoardDetail = document.getElementById("btnSubBoardDetail");
  if (btnSubBoardDetail) {
    btnSubBoardDetail.addEventListener("click", () => switchChannelSubTab("board"));
  }"""

listener_replacement = """  const btnSubBoardDetail = document.getElementById("btnSubBoardDetail");
  if (btnSubBoardDetail) {
    btnSubBoardDetail.addEventListener("click", () => switchChannelSubTab("board"));
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

  const claimCallCountFilter = document.getElementById("claimCallCountFilter");
  if (claimCallCountFilter) {
    claimCallCountFilter.addEventListener("change", (e) => {
      claimCallFilterVal = e.target.value;
      claimPage = 1;
      const period = E.getPeriod();
      const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope);
      renderClaimTable(res.claims);
    });
  }

  const claimSearchInput = document.getElementById("claimSearchInput");
  if (claimSearchInput) {
    claimSearchInput.addEventListener("input", (e) => {
      claimSearchTerm = e.target.value.trim();
      claimPage = 1;
      const period = E.getPeriod();
      const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope);
      renderClaimTable(res.claims);
    });
  }

  const btnExportClaimAnalysis = document.getElementById("btnExportClaimAnalysis");
  if (btnExportClaimAnalysis) {
    btnExportClaimAnalysis.addEventListener("click", exportClaimAnalysisToExcel);
  }"""

# Apply replacements
content_norm = content.replace('\r\n', '\n')
subtab_target_norm = subtab_target.replace('\r\n', '\n')
subtab_replacement_norm = subtab_replacement.replace('\r\n', '\n')
subtab_hide_target_norm = subtab_hide_target.replace('\r\n', '\n')
subtab_hide_replacement_norm = subtab_hide_replacement.replace('\r\n', '\n')
subtab_render_target_norm = subtab_render_target.replace('\r\n', '\n')
subtab_render_replacement_norm = subtab_render_replacement.replace('\r\n', '\n')
render_channel_target_norm = render_channel_target.replace('\r\n', '\n')
render_channel_replacement_norm = render_channel_replacement.replace('\r\n', '\n')
listener_target_norm = listener_target.replace('\r\n', '\n')
listener_replacement_norm = listener_replacement.replace('\r\n', '\n')

ok = True
if subtab_target_norm in content_norm:
    content_norm = content_norm.replace(subtab_target_norm, subtab_replacement_norm, 1)
else:
    print("subtab_target not found")
    ok = False

if subtab_hide_target_norm in content_norm:
    content_norm = content_norm.replace(subtab_hide_target_norm, subtab_hide_replacement_norm, 1)
else:
    print("subtab_hide_target not found")
    ok = False

if subtab_render_target_norm in content_norm:
    content_norm = content_norm.replace(subtab_render_target_norm, subtab_render_replacement_norm, 1)
else:
    print("subtab_render_target not found")
    ok = False

if render_channel_target_norm in content_norm:
    content_norm = content_norm.replace(render_channel_target_norm, render_channel_replacement_norm, 1)
else:
    print("render_channel_target not found")
    ok = False

if listener_target_norm in content_norm:
    content_norm = content_norm.replace(listener_target_norm, listener_replacement_norm, 1)
else:
    print("listener_target not found")
    ok = False

# Insert claim_logic right before renderCtiAnswerRateTrendChart
trend_chart_anchor = "function renderCtiAnswerRateTrendChart() {"
if trend_chart_anchor in content_norm:
    content_norm = content_norm.replace(trend_chart_anchor, claim_logic.replace('\r\n', '\n') + "\n" + trend_chart_anchor, 1)
else:
    print("trend_chart_anchor not found")
    ok = False

if ok:
    with open('dashboard/render.js', 'w', encoding='utf-8') as f:
        f.write(content_norm.replace('\n', '\r\n'))
    print("Successfully patched dashboard/render.js!")
else:
    print("Failed to patch render.js")
