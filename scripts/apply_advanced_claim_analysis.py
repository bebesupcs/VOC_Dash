# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. Update engine.js
with open('dashboard/engine.js', 'r', encoding='utf-8') as f:
    engine_code = f.read()

engine_target = """  const avgCalls = totalClaims > 0 ? (sumCalls / totalClaims).toFixed(2) : "0.0";
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
  };"""

engine_replacement = """  const avgCalls = totalClaims > 0 ? (sumCalls / totalClaims).toFixed(2) : "0.0";
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
      categoryBreakdown
    }
  };"""

engine_norm = engine_code.replace('\r\n', '\n')
engine_target_norm = engine_target.replace('\r\n', '\n')
engine_replacement_norm = engine_replacement.replace('\r\n', '\n')

if engine_target_norm in engine_norm:
    engine_norm = engine_norm.replace(engine_target_norm, engine_replacement_norm, 1)
    with open('dashboard/engine.js', 'w', encoding='utf-8') as f:
        f.write(engine_norm.replace('\n', '\r\n'))
    print("[1/3] engine.js updated with categoryBreakdown & FCR metrics!")
else:
    print("[1/3] Warning: engine_target not found in engine.js")

# 2. Update index.html section with enhanced layout
with open('dashboard/index.html', 'r', encoding='utf-8') as f:
    html_code = f.read()

# Replace the claimLeadtimeSection with the advanced version
old_claim_sec_start = '<div id="claimLeadtimeSection" hidden>'
old_claim_sec_end = '</div> <!-- End claimLeadtimeSection -->'
pos_s = html_code.find(old_claim_sec_start)
pos_e = html_code.find(old_claim_sec_end)

if pos_s != -1 and pos_e != -1:
    advanced_claim_html = """<div id="claimLeadtimeSection" hidden>
      <!-- 1. 필터 및 컨트롤 바 -->
      <div class="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white p-3.5 ring-1 ring-black/5 shadow-2xs">
        <div class="flex items-center gap-2.5">
          <span class="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-teal-100 text-teal-800 text-lg font-bold">⏱️</span>
          <div>
            <div class="flex items-center gap-2">
              <h2 class="text-sm font-bold text-zinc-900">클레임 처리 리드타임 & 통화 심층 분석</h2>
              <span class="rounded-full bg-teal-50 px-2 py-0.5 text-[10px] font-semibold text-teal-700 ring-1 ring-teal-600/20">고도화 지표</span>
            </div>
            <p class="text-xs text-zinc-500 mt-0.5">최초 클레임 인입 후 14일 이내 재통화를 그룹화하여 FCR(1회해결율), 병목 유형, 타임라인을 추적합니다.</p>
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <!-- 범위 선택: 현재 기간 vs 전체 누적 -->
          <div class="flex items-center rounded-lg bg-zinc-100 p-0.5 text-xs">
            <button id="btnClaimScopePeriod" type="button" class="rounded-md bg-white px-2.5 py-1 font-semibold text-teal-800 shadow-2xs transition">선택 기간</button>
            <button id="btnClaimScopeAll" type="button" class="rounded-md px-2.5 py-1 font-medium text-zinc-600 hover:text-zinc-900 transition">전체 누적</button>
          </div>
          <!-- 통화횟수 필터 -->
          <select id="claimCallCountFilter" class="rounded-lg border border-black/10 bg-white px-2.5 py-1 text-xs text-zinc-700 focus:outline-none focus:ring-1 focus:ring-teal-500">
            <option value="all">통화횟수: 전체</option>
            <option value="1">1회 해결 (FCR)</option>
            <option value="2-3">2~3회 재통화</option>
            <option value="4+">4회 이상 다회 (위험군)</option>
          </select>
          <!-- 클레임 유형 필터 -->
          <select id="claimCategoryFilter" class="rounded-lg border border-black/10 bg-white px-2.5 py-1 text-xs text-zinc-700 focus:outline-none focus:ring-1 focus:ring-teal-500">
            <option value="all">유형: 전체</option>
            <option value="품질">제품 품질 클레임</option>
            <option value="배송">배송 클레임</option>
            <option value="휴먼에러">휴먼에러</option>
            <option value="시스템">시스템/판매처</option>
          </select>
          <!-- 검색창 -->
          <div class="relative">
            <input id="claimSearchInput" type="text" placeholder="고객명, 연락처, 태그, 상담사..." class="w-44 rounded-lg border border-black/10 bg-white pl-8 pr-3 py-1 text-xs text-zinc-800 placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-teal-500">
            <svg class="pointer-events-none absolute left-2.5 top-1.5 h-3.5 w-3.5 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
          </div>
          <button id="btnExportClaimAnalysis" type="button" class="inline-flex items-center gap-1 rounded-lg bg-teal-50 px-2.5 py-1 text-xs font-semibold text-teal-700 ring-1 ring-teal-600/20 hover:bg-teal-100 transition">
            <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
            Excel 다운로드
          </button>
        </div>
      </div>

      <!-- 2. 상단 메트릭 카드 4개 (FCR 지표 추가) -->
      <section id="claimAnalysisKpiRow" class="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4"></section>

      <!-- 3. 고도화 분석: 클레임 유형별 리드타임 & 재통화율 병목 매트릭스 -->
      <section class="mt-4 rounded-xl bg-white p-4 ring-1 ring-black/5 shadow-2xs">
        <div class="flex items-center justify-between pb-3 border-b border-black/5">
          <div class="flex items-center gap-2">
            <span class="inline-flex h-6 w-6 items-center justify-center rounded-md bg-rose-100 text-rose-700 text-xs font-bold">⚠️</span>
            <h3 class="text-sm font-semibold text-zinc-800">클레임 유형별 리드타임 & 재통화 병목 분석 (어디서 지연되는가?)</h3>
          </div>
          <span class="text-xs text-zinc-400">* 제품 품질 클레임은 회수/출고 절차로 인해 재통화율과 리드타임이 가장 높게 형성됩니다.</span>
        </div>
        <div class="mt-3 grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
          <!-- 좌측 가로 막대 차트 (유형별 재통화율 vs 리드타임) -->
          <div class="lg:col-span-5 h-56 relative">
            <canvas id="claimCategoryBarChart"></canvas>
          </div>
          <!-- 우측 유형별 세부 지표 피벗 테이블 -->
          <div class="lg:col-span-7 overflow-x-auto">
            <table class="w-full text-left text-xs">
              <thead class="bg-zinc-50 text-[11px] font-semibold text-zinc-600 border-b border-black/10">
                <tr>
                  <th class="py-2 px-2.5">클레임 유형</th>
                  <th class="py-2 px-2 text-right">총 건수</th>
                  <th class="py-2 px-2 text-right">재통화 건수</th>
                  <th class="py-2 px-2 text-right text-rose-700 font-bold">재통화율</th>
                  <th class="py-2 px-2 text-right">건당 통화수</th>
                  <th class="py-2 px-2 text-right text-teal-800 font-bold">평균 리드타임</th>
                  <th class="py-2 px-2 text-right">평균 통화시간</th>
                </tr>
              </thead>
              <tbody id="claimCategoryTableBody" class="divide-y divide-black/5 font-normal"></tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- 4. 통화 횟수별 분포 vs 리드타임 구간별 히스토그램 (차트 2종) -->
      <section class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div class="rounded-xl bg-white p-4 ring-1 ring-black/5 shadow-2xs">
          <div class="flex items-center justify-between pb-2 border-b border-black/5">
            <div>
              <h3 class="text-sm font-semibold text-zinc-800">통화 횟수별 분포 (1회 종결 vs 재통화)</h3>
              <p class="text-xs text-zinc-400 mt-0.5">클레임 1회 종결(FCR) 비중과 다회 통화 리스크</p>
            </div>
            <span id="claimCallCountBadge" class="rounded-full bg-teal-50 px-2.5 py-0.5 text-[11px] font-semibold text-teal-800 ring-1 ring-teal-600/20"></span>
          </div>
          <div class="relative h-60 mt-3">
            <canvas id="claimCallCountChart"></canvas>
          </div>
        </div>

        <div class="rounded-xl bg-white p-4 ring-1 ring-black/5 shadow-2xs">
          <div class="flex items-center justify-between pb-2 border-b border-black/5">
            <div>
              <h3 class="text-sm font-semibold text-zinc-800">해결 기간(리드타임) 구간별 분포</h3>
              <p class="text-xs text-zinc-400 mt-0.5">최초 접수부터 최종 재통화 완료까지 소요시간 구간</p>
            </div>
            <span id="claimLeadtimeBadge" class="rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-800 ring-1 ring-emerald-600/20"></span>
          </div>
          <div class="relative h-60 mt-3">
            <canvas id="claimLeadtimeChart"></canvas>
          </div>
        </div>
      </section>

      <!-- 5. 하단 상세 원장 테이블 (행 클릭 시 타임라인 아코디언 제공) -->
      <section class="mt-4 rounded-xl bg-white p-4 ring-1 ring-black/5 shadow-2xs">
        <div class="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-black/5">
          <div class="flex items-center gap-2">
            <h3 class="text-sm font-semibold text-zinc-800">클레임 그룹별 통화 이력 및 처리 상세 원장</h3>
            <span id="claimTableCountBadge" class="rounded-full bg-teal-50 text-teal-800 px-2.5 py-0.5 text-xs font-semibold ring-1 ring-teal-600/20">0건</span>
          </div>
          <div class="text-xs text-zinc-500">
            💡 행을 클릭하면 해당 클레임의 **전체 통화 여정 타임라인(Journey)**이 상세하게 펼쳐집니다.
          </div>
        </div>
        <div class="mt-3 overflow-x-auto max-h-[560px]">
          <table class="w-full text-left text-xs text-zinc-600">
            <thead class="sticky top-0 z-10 bg-zinc-50 text-[11px] font-semibold text-zinc-700 uppercase border-b border-black/10">
              <tr>
                <th class="py-2.5 px-3">Claim ID</th>
                <th class="py-2.5 px-3">고객명 / 연락처</th>
                <th class="py-2.5 px-3">최초 접수일시</th>
                <th class="py-2.5 px-3">최종 통화일시</th>
                <th class="py-2.5 px-3">소요 리드타임</th>
                <th class="py-2.5 px-3 text-center">총 통화횟수</th>
                <th class="py-2.5 px-3 text-right">총 통화시간</th>
                <th class="py-2.5 px-3">클레임 유형 (태그)</th>
                <th class="py-2.5 px-3">담당자</th>
                <th class="py-2.5 px-3">상담 문의 / 조치내용</th>
              </tr>
            </thead>
            <tbody id="claimDetailTableBody" class="divide-y divide-black/5 font-normal"></tbody>
          </table>
        </div>
        <!-- 페이지네이션 -->
        <div id="claimPagination" class="mt-3 flex items-center justify-between pt-2 border-t border-black/5 text-xs text-zinc-500"></div>
      </section>
    </div> <!-- End claimLeadtimeSection -->"""

    html_code = html_code[:pos_s] + advanced_claim_html + html_code[pos_e + len(old_claim_sec_end):]
    with open('dashboard/index.html', 'w', encoding='utf-8') as f:
        f.write(html_code)
    print("[2/3] index.html updated with advanced UI layout!")
else:
    print("[2/3] Warning: claimLeadtimeSection not found in index.html")
