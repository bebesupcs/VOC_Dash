# -*- coding: utf-8 -*-
import sys, re

with open('dashboard/engine.js', 'r', encoding='utf-8') as f:
    text = f.read()

old_func_pat = r'function rawChats\(period\) \{[\s\S]*?return chatsForWeekKey\(period\.key\);\s*\}'

new_func = """function rawChats(period) {
  period = period || (typeof getPeriod === "function" ? getPeriod() : null);
  if (!period) return [];
  const getItemDate = (c) => c.date || (c.time ? c.time.slice(0, 10) : "");
  // 1. 월간 모드: 달력 1일 ~ 말일 (영업 접수일자 기준)
  if (period.key && /^\\d{4}-\\d{2}$/.test(period.key)) {
    const mPrefix = period.key;
    return getAllChats().filter((c) => getItemDate(c).startsWith(mPrefix));
  }
  // 2. 분기 모드: 해당 분기 3개 월 달력 일자 기준
  if (period.key && /^\\d{4}-Q[1-4]$/.test(period.key)) {
    const y = period.key.slice(0, 4);
    const q = parseInt(period.key.slice(6), 10);
    const startM = (q - 1) * 3 + 1;
    const months = [startM, startM + 1, startM + 2].map((m) => `${y}-${String(m).padStart(2, "0")}`);
    return getAllChats().filter((c) => months.some((m) => getItemDate(c).startsWith(m)));
  }
  // 3. 연간 모드: 해당 연도 전체 달력 일자 기준
  if (period.key && /^\\d{4}$/.test(period.key)) {
    const yPrefix = period.key;
    return getAllChats().filter((c) => getItemDate(c).startsWith(yPrefix));
  }
  // 4. 주간 모드: 운영 주차 기준
  if (period.weekKeys && period.weekKeys.length) {
    return period.weekKeys.flatMap(chatsForWeekKey);
  }
  return chatsForWeekKey(period.key);
}"""

m = re.search(old_func_pat, text)
if m:
    updated = text[:m.start()] + new_func + text[m.end():]
    with open('dashboard/engine.js', 'w', encoding='utf-8') as f:
        f.write(updated)
    print("Successfully replaced rawChats in engine.js")
else:
    print("Failed to find pattern in engine.js")
