# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. Patch engine.js
with open('dashboard/engine.js', 'r', encoding='utf-8') as f:
    engine_code = f.read()

# Fix getAllCti
old_get_all_cti = """let _allCtiCache = null;
function getAllCti() {
  if (!_allCtiCache && window.VOC_DATA && window.VOC_DATA.CTI_BY_WEEK) {
    _allCtiCache = Object.values(window.VOC_DATA.CTI_BY_WEEK).flat();
  }
  return _allCtiCache || [];
}"""

new_get_all_cti = """let _allCtiCache = null;
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
}"""

engine_norm = engine_code.replace('\r\n', '\n')
old_get_all_cti_norm = old_get_all_cti.replace('\r\n', '\n')
new_get_all_cti_norm = new_get_all_cti.replace('\r\n', '\n')

if old_get_all_cti_norm in engine_norm:
    engine_norm = engine_norm.replace(old_get_all_cti_norm, new_get_all_cti_norm, 1)
    print("Fixed getAllCti in engine.js to attach week property!")
else:
    print("Warning: old_get_all_cti not matched")

# Update analyzeClaimLeadtime signature and diffDays
engine_norm = engine_norm.replace(
    'function analyzeClaimLeadtime(period, scope = "period") {',
    'function analyzeClaimLeadtime(period, scope = "period", windowDays = 30) {'
)

engine_norm = engine_norm.replace(
    'if (diffDays >= 0 && diffDays <= 14.0) {',
    'if (diffDays >= 0 && diffDays <= windowDays) {'
)

with open('dashboard/engine.js', 'w', encoding='utf-8') as f:
    f.write(engine_norm.replace('\n', '\r\n'))
print("Successfully updated engine.js with windowDays parameter!")


# 2. Patch index.html to add windowDays dropdown
with open('dashboard/index.html', 'r', encoding='utf-8') as f:
    html_code = f.read()

old_select_bar = """          <!-- 통화횟수 필터 -->
          <select id="claimCallCountFilter" class="rounded-lg border border-black/10 bg-white px-2.5 py-1 text-xs text-zinc-700 focus:outline-none focus:ring-1 focus:ring-teal-500">"""

new_select_bar = """          <!-- 추적 윈도우(한달/14일/60일) 필터 -->
          <select id="claimWindowFilter" class="rounded-lg border border-teal-500/30 bg-teal-50/50 px-2.5 py-1 text-xs font-semibold text-teal-800 focus:outline-none focus:ring-1 focus:ring-teal-500" title="클레임 발생 후 재통화를 동일 건으로 추적하는 기간">
            <option value="30" selected>추적: 30일 (한달·권장)</option>
            <option value="14">추적: 14일 (2주)</option>
            <option value="60">추적: 60일 (2개월)</option>
          </select>
          <!-- 통화횟수 필터 -->
          <select id="claimCallCountFilter" class="rounded-lg border border-black/10 bg-white px-2.5 py-1 text-xs text-zinc-700 focus:outline-none focus:ring-1 focus:ring-teal-500">"""

html_norm = html_code.replace('\r\n', '\n')
old_select_bar_norm = old_select_bar.replace('\r\n', '\n')
new_select_bar_norm = new_select_bar.replace('\r\n', '\n')

if old_select_bar_norm in html_norm:
    html_norm = html_norm.replace(old_select_bar_norm, new_select_bar_norm, 1)
    with open('dashboard/index.html', 'w', encoding='utf-8') as f:
        f.write(html_norm.replace('\n', '\r\n'))
    print("Successfully added claimWindowFilter to index.html!")
else:
    print("Warning: old_select_bar not matched in index.html")


# 3. Patch render.js to use claimWindowDays and wire up event listener
with open('dashboard/render.js', 'r', encoding='utf-8') as f:
    render_code = f.read()

render_norm = render_code.replace('\r\n', '\n')

# Add claimWindowDays variable
render_norm = render_norm.replace(
    'let claimLeadtimeScope = "period"; // "period" or "all"',
    'let claimLeadtimeScope = "period"; // "period" or "all"\nlet claimWindowDays = 30;'
)

# Update renderClaimLeadtimeDetail call
render_norm = render_norm.replace(
    'const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope);',
    'const res = E.analyzeClaimLeadtime(period, claimLeadtimeScope, claimWindowDays);'
)

# Wire up claimWindowFilter listener
window_listener = """  const claimWindowFilter = document.getElementById("claimWindowFilter");
  if (claimWindowFilter) {
    claimWindowFilter.addEventListener("change", (e) => {
      claimWindowDays = parseInt(e.target.value, 10) || 30;
      claimPage = 1;
      renderClaimLeadtimeDetail();
    });
  }"""

if 'claimWindowFilter.addEventListener' not in render_norm:
    render_norm = render_norm.replace('if (claimCategoryFilter) {', window_listener + '\n\n  if (claimCategoryFilter) {')

with open('dashboard/render.js', 'w', encoding='utf-8') as f:
    f.write(render_norm.replace('\n', '\r\n'))
print("Successfully updated render.js with claimWindowDays logic and listener!")
