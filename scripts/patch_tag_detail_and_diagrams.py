# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. Update engine.js to include tagBreakdown in summary
with open('dashboard/engine.js', 'r', encoding='utf-8') as f:
    engine_code = f.read()

target_str = """  const categoryBreakdown = Object.values(catMap).map(m => ({
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

replacement_str = """  const categoryBreakdown = Object.values(catMap).map(m => ({
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
    const t = c.first_tag || "기타";
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
    let quadrant = "3"; // 1: 최우선개선, 2: 장기검수, 3: 빠른해결, 4: 단기핑퐁
    if (repeatRate >= 20.0 && avgLeadHours >= 24.0) quadrant = "1";
    else if (repeatRate < 20.0 && avgLeadHours >= 24.0) quadrant = "2";
    else if (repeatRate < 20.0 && avgLeadHours < 24.0) quadrant = "3";
    else quadrant = "4";

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
      r: Math.max(5, Math.min(24, Math.round(Math.sqrt(m.total) * 2.2)))
    };
  }).sort((a, b) => b.total - a.total);

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
  };"""

engine_norm = engine_code.replace('\r\n', '\n')
target_str_norm = target_str.replace('\r\n', '\n')
replacement_str_norm = replacement_str.replace('\r\n', '\n')

if target_str_norm in engine_norm:
    engine_norm = engine_norm.replace(target_str_norm, replacement_str_norm, 1)
    with open('dashboard/engine.js', 'w', encoding='utf-8') as f:
        f.write(engine_norm.replace('\n', '\r\n'))
    print("[1/3] engine.js patched with tagBreakdown & 4-quadrant categorization!")
else:
    print("Warning: target_str not found in engine.js")


# 2. Update index.html to add Process Flow Diagram & Tag Matrix
with open('dashboard/index.html', 'r', encoding='utf-8') as f:
    html_code = f.read()

# Locate section 3 in claimLeadtimeSection (category breakdown)
cat_sec_anchor = '<!-- 3. 고도화 분석: 클레임 유형별 리드타임 & 재통화율 병목 매트릭스 -->'
pos_cat = html_code.find(cat_sec_anchor)

if pos_cat != -1:
    diagram_html = """<!-- 2.5. 도식화 다이어그램: 클레임 해결 프로세스 플로우 (Process Flow Pipeline) -->
      <section class="mt-4 rounded-xl bg-gradient-to-r from-teal-900 via-teal-800 to-slate-900 p-4 text-white shadow-sm ring-1 ring-black/10">
        <div class="flex items-center justify-between pb-2.5 border-b border-white/10">
          <div class="flex items-center gap-2">
            <span class="inline-flex h-6 w-6 items-center justify-center rounded-md bg-teal-500/20 text-teal-300 text-xs font-bold">🗺️</span>
            <h3 class="text-xs font-bold tracking-wide text-teal-100 uppercase">클레임 해결 프로세스 여정 도식화 (Resolution Journey Flow)</h3>
          </div>
          <span class="text-[11px] text-teal-200/70">고객 클레임 접수부터 해결 완료까지의 병목 단계 시각화</span>
        </div>

        <div class="mt-3.5 grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
          <!-- 단계 1: 최초 인입 -->
          <div class="rounded-lg bg-white/10 p-3 backdrop-blur-xs border border-white/10 relative">
            <div class="flex items-center justify-between text-teal-200 text-[11px] font-semibold">
              <span>STEP 1. 접수</span>
              <span class="rounded bg-teal-500/30 px-1.5 py-0.2">100% 인입</span>
            </div>
            <div class="text-base font-extrabold mt-1 text-white" id="flowTotalClaims">0건</div>
            <p class="text-[11px] text-zinc-300 mt-1 leading-relaxed">최초 클레임 VOC 인입<br>상담원 원인 파악 및 조치 계획 수립</p>
            <div class="mt-2 text-[10px] text-teal-300 font-medium">평균 최초 상담: 약 3분</div>
          </div>

          <!-- 단계 2: 1차 종결 (FCR) -->
          <div class="rounded-lg bg-emerald-500/15 p-3 backdrop-blur-xs border border-emerald-400/30">
            <div class="flex items-center justify-between text-emerald-300 text-[11px] font-semibold">
              <span>STEP 2-A. 즉시 해결</span>
              <span class="rounded bg-emerald-500/30 px-1.5 py-0.2" id="flowFcrRate">FCR 0.0%</span>
            </div>
            <div class="text-base font-extrabold mt-1 text-emerald-200" id="flowCount1">0건</div>
            <p class="text-[11px] text-zinc-300 mt-1 leading-relaxed"><strong class="text-emerald-300">1회 통화로 당일 완결</strong><br>단순 파손 교환, 지연 안내, 단순 반품</p>
            <div class="mt-2 text-[10px] text-emerald-300 font-medium">평균 리드타임: 당일 (약 3시간)</div>
          </div>

          <!-- 단계 3: 재통화 발생 -->
          <div class="rounded-lg bg-amber-500/15 p-3 backdrop-blur-xs border border-amber-400/30">
            <div class="flex items-center justify-between text-amber-300 text-[11px] font-semibold">
              <span>STEP 2-B. 재통화 발생</span>
              <span class="rounded bg-amber-500/30 px-1.5 py-0.2" id="flowRepeatRate">재통화 0.0%</span>
            </div>
            <div class="text-base font-extrabold mt-1 text-amber-200" id="flowCount23">0건</div>
            <p class="text-[11px] text-zinc-300 mt-1 leading-relaxed"><strong class="text-amber-300">2~3회 재통화 발생</strong><br>회수 진행 확인, 출고 지연 안내, 미수취 추적</p>
            <div class="mt-2 text-[10px] text-amber-300 font-medium">평균 리드타임: 1일 ~ 3일</div>
          </div>

          <!-- 단계 4: 고위험 장기 해결군 -->
          <div class="rounded-lg bg-rose-500/15 p-3 backdrop-blur-xs border border-rose-400/30">
            <div class="flex items-center justify-between text-rose-300 text-[11px] font-semibold">
              <span>STEP 3. 고위험 장기군</span>
              <span class="rounded bg-rose-500/30 px-1.5 py-0.2" id="flowRiskRate">위험 0.0%</span>
            </div>
            <div class="text-base font-extrabold mt-1 text-rose-200" id="flowCount4Plus">0건</div>
            <p class="text-[11px] text-zinc-300 mt-1 leading-relaxed"><strong class="text-rose-300">4회 이상 다회 통화</strong><br>약품 냄새/이취, 원단 이물 검수, 강성 불만</p>
            <div class="mt-2 text-[10px] text-rose-300 font-medium">평균 리드타임: 4일 ~ 최대 4주</div>
          </div>
        </div>
      </section>

      <!-- 3. 고도화 분석: 클레임 유형별 리드타임 & 재통화율 병목 매트릭스 -->"""

    html_code = html_code.replace(cat_sec_anchor, diagram_html, 1)

# Now add Section 3.5: 4-Quadrant Tag Risk Matrix
tag_matrix_section = """      <!-- 3.5. 세부 태그별 리스크 & 병목 4사분면 매트릭스 도식화 (Tag Risk Matrix) -->
      <section class="mt-4 rounded-xl bg-white p-4 ring-1 ring-black/5 shadow-2xs">
        <div class="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-black/5">
          <div class="flex items-center gap-2">
            <span class="inline-flex h-6 w-6 items-center justify-center rounded-md bg-indigo-100 text-indigo-700 text-xs font-bold">🎯</span>
            <div>
              <h3 class="text-sm font-semibold text-zinc-800">세부 태그별 리스크 & 병목 4사분면 매트릭스 도식화 (Tag Risk Matrix)</h3>
              <p class="text-xs text-zinc-400 mt-0.5">X축: 재통화율(%) · Y축: 평균 해결시간(h) · 원 크기: 발생건수 · 클릭 시 하단 원장 자동 필터링</p>
            </div>
          </div>
          <!-- 4대 사분면 가이드 배지 -->
          <div class="flex flex-wrap items-center gap-1.5 text-[10px]">
            <span class="rounded px-2 py-0.5 font-semibold bg-rose-100 text-rose-800 ring-1 ring-rose-600/20">🚨 1사분면: 최우선 개선 (재통화↑·시간↑)</span>
            <span class="rounded px-2 py-0.5 font-semibold bg-amber-100 text-amber-800 ring-1 ring-amber-600/20">⏱️ 2사분면: 장기 검수형 (시간↑)</span>
            <span class="rounded px-2 py-0.5 font-semibold bg-sky-100 text-sky-800 ring-1 ring-sky-600/20">🔁 4사분면: 단기 핑퐁 (재통화↑)</span>
            <span class="rounded px-2 py-0.5 font-semibold bg-emerald-100 text-emerald-800 ring-1 ring-emerald-600/20">✅ 3사분면: 빠른 종결 (우수)</span>
          </div>
        </div>

        <div class="mt-3.5 grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
          <!-- 좌측 4사분면 버블 차트 -->
          <div class="lg:col-span-6 h-72 relative">
            <canvas id="claimTagMatrixChart"></canvas>
          </div>
          <!-- 우측 세부 태그 상세 실적 테이블 -->
          <div class="lg:col-span-6 overflow-x-auto max-h-72">
            <table class="w-full text-left text-xs">
              <thead class="sticky top-0 bg-zinc-50 text-[11px] font-semibold text-zinc-600 border-b border-black/10">
                <tr>
                  <th class="py-2 px-2.5">세부 태그명</th>
                  <th class="py-2 px-2 text-right">건수</th>
                  <th class="py-2 px-2 text-right text-rose-700 font-bold">재통화율</th>
                  <th class="py-2 px-2 text-right text-teal-800 font-bold">평균 리드타임</th>
                  <th class="py-2 px-2 text-center">사분면</th>
                  <th class="py-2 px-2 text-center">원장필터</th>
                </tr>
              </thead>
              <tbody id="claimTagTableBody" class="divide-y divide-black/5 font-normal"></tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- 4. 통화 횟수별 분포 vs 리드타임 구간별 히스토그램 (차트 2종) -->"""

sec4_anchor = '<!-- 4. 통화 횟수별 분포 vs 리드타임 구간별 히스토그램 (차트 2종) -->'
if sec4_anchor in html_code:
    html_code = html_code.replace(sec4_anchor, tag_matrix_section, 1)

with open('dashboard/index.html', 'w', encoding='utf-8') as f:
    f.write(html_code)
print("[2/3] index.html updated with Process Flow & 4-Quadrant Tag Matrix!")
