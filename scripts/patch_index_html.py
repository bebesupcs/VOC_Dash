# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('dashboard/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Subtab button
btn_target = """        <button id="btnSubBoardDetail" type="button" class="inline-flex items-center gap-1.5 rounded-lg bg-zinc-100 px-3.5 py-1.5 text-xs font-medium text-zinc-600 transition hover:bg-zinc-200 hover:text-zinc-900">
          <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/></svg>
          📋 게시판상담 상세 분석
        </button>"""

btn_replacement = """        <button id="btnSubBoardDetail" type="button" class="inline-flex items-center gap-1.5 rounded-lg bg-zinc-100 px-3.5 py-1.5 text-xs font-medium text-zinc-600 transition hover:bg-zinc-200 hover:text-zinc-900">
          <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/></svg>
          📋 게시판상담 상세 분석
        </button>
        <button id="btnSubClaimLeadtimeDetail" type="button" class="inline-flex items-center gap-1.5 rounded-lg bg-zinc-100 px-3.5 py-1.5 text-xs font-medium text-zinc-600 transition hover:bg-zinc-200 hover:text-zinc-900">
          <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          ⏱️ 클레임 분석 (리드타임/통화)
        </button>"""

# 2. Section container
sec_target = """    </div> <!-- End boardDetailSection -->
  </div> <!-- End channelView -->"""

claim_section_html = """    </div> <!-- End boardDetailSection -->

    <!-- 5. 클레임 처리 리드타임 및 통화 분석 상세 영역 -->
    <div id="claimLeadtimeSection" hidden>
      <!-- 필터 및 컨트롤 바 -->
      <div class="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white p-3.5 ring-1 ring-black/5 shadow-2xs">
        <div class="flex items-center gap-2">
          <span class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-teal-100 text-teal-800 text-base font-bold">⏱️</span>
          <div>
            <h2 class="text-sm font-semibold text-zinc-900">클레임 처리 리드타임 & 통화 분석</h2>
            <p class="text-xs text-zinc-500">최초 클레임 인입 후 14일 이내 재통화를 동일 Claim ID로 자동 그룹화하여 소요시간 및 통화패턴을 분석합니다.</p>
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
            <option value="1">1회 해결 (단일 통화)</option>
            <option value="2-3">2~3회 재통화</option>
            <option value="4+">4회 이상 다회 통화</option>
          </select>
          <!-- 검색창 -->
          <div class="relative">
            <input id="claimSearchInput" type="text" placeholder="고객명, 연락처, 태그 검색..." class="w-48 rounded-lg border border-black/10 bg-white pl-8 pr-3 py-1 text-xs text-zinc-800 placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-teal-500">
            <svg class="pointer-events-none absolute left-2.5 top-1.5 h-3.5 w-3.5 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
          </div>
          <button id="btnExportClaimAnalysis" type="button" class="inline-flex items-center gap-1 rounded-lg bg-teal-50 px-2.5 py-1 text-xs font-semibold text-teal-700 ring-1 ring-teal-600/20 hover:bg-teal-100 transition">
            <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
            Excel 다운로드
          </button>
        </div>
      </div>

      <!-- 상단 메트릭 카드 3개 -->
      <section id="claimAnalysisKpiRow" class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <!-- 동적 렌더링: 1) 평균 통화 횟수 2) 평균 총 통화 시간 3) 평균 클레임 해결 리드타임 -->
      </section>

      <!-- 하단 시각화 차트 2종 (통화 횟수별 분포 vs 리드타임 구간별 히스토그램) -->
      <section class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <!-- 1) 통화 횟수별 분포 막대차트 -->
        <div class="rounded-xl bg-white p-4 ring-1 ring-black/5 shadow-2xs">
          <div class="flex items-center justify-between pb-2 border-b border-black/5">
            <div>
              <h3 class="text-sm font-semibold text-zinc-800">통화 횟수별 분포 (1회 vs 재통화 vs 다회)</h3>
              <p class="text-xs text-zinc-400 mt-0.5">클레임 건당 통화 횟수 비중 (1회 종결 vs 재통화)</p>
            </div>
            <span id="claimCallCountBadge" class="rounded-full bg-teal-50 px-2.5 py-0.5 text-[11px] font-semibold text-teal-800 ring-1 ring-teal-600/20"></span>
          </div>
          <div class="relative h-64 mt-3">
            <canvas id="claimCallCountChart"></canvas>
          </div>
        </div>

        <!-- 2) 해결 기간(리드타임) 구간별 건수 히스토그램 -->
        <div class="rounded-xl bg-white p-4 ring-1 ring-black/5 shadow-2xs">
          <div class="flex items-center justify-between pb-2 border-b border-black/5">
            <div>
              <h3 class="text-sm font-semibold text-zinc-800">해결 기간(리드타임) 구간별 분포</h3>
              <p class="text-xs text-zinc-400 mt-0.5">최초 접수부터 최종 재통화 완료까지 소요시간 구간</p>
            </div>
            <span id="claimLeadtimeBadge" class="rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-800 ring-1 ring-emerald-600/20"></span>
          </div>
          <div class="relative h-64 mt-3">
            <canvas id="claimLeadtimeChart"></canvas>
          </div>
        </div>
      </section>

      <!-- 하단 상세 원장 테이블 -->
      <section class="mt-4 rounded-xl bg-white p-4 ring-1 ring-black/5 shadow-2xs">
        <div class="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-black/5">
          <div class="flex items-center gap-2">
            <h3 class="text-sm font-semibold text-zinc-800">클레임 그룹별 통화 이력 및 처리 상세 원장</h3>
            <span id="claimTableCountBadge" class="rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-semibold text-zinc-700">0건</span>
          </div>
          <div class="text-xs text-zinc-500">
            * 14일 이내 재통화 건이 동일 Claim ID로 묶여 총 통화수와 리드타임이 산출됩니다.
          </div>
        </div>
        <div class="mt-3 overflow-x-auto max-h-[520px]">
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
    </div> <!-- End claimLeadtimeSection -->
  </div> <!-- End channelView -->"""

# Replace with normalized newlines
content_norm = content.replace('\r\n', '\n')
btn_target_norm = btn_target.replace('\r\n', '\n')
btn_replacement_norm = btn_replacement.replace('\r\n', '\n')
sec_target_norm = sec_target.replace('\r\n', '\n')
claim_section_html_norm = claim_section_html.replace('\r\n', '\n')

if btn_target_norm in content_norm and sec_target_norm in content_norm:
    content_norm = content_norm.replace(btn_target_norm, btn_replacement_norm)
    content_norm = content_norm.replace(sec_target_norm, claim_section_html_norm)
    with open('dashboard/index.html', 'w', encoding='utf-8') as f:
        f.write(content_norm.replace('\n', '\r\n'))
    print("Successfully patched dashboard/index.html!")
else:
    print("Targets not matched in dashboard/index.html")
    if btn_target_norm not in content_norm: print("btn_target not found")
    if sec_target_norm not in content_norm: print("sec_target not found")
