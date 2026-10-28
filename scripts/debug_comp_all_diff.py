# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))

from scripts.generate_report_excel import load_voc_data, load_clean_quality_raw

data = load_voc_data()
raw = load_clean_quality_raw({}, data)

# Items selected in 2026-09
comp_9m = []
for r in raw:
    if not r.get('isComp', True):
        continue
    t_str = str(r.get('time') or '')[:7]
    d_str = str(r.get('date') or '')[:7]
    if t_str == '2026-09' or d_str == '2026-09':
        comp_9m.append(r)

print(f"Total comp items in 2026-09: {len(comp_9m)}")

by_month = {}
by_report_m = {}

for r in comp_9m:
    m = r.get('month')
    rm = r.get('reportMonth')
    by_month[m] = by_month.get(m, 0) + 1
    by_report_m[rm] = by_report_m.get(rm, 0) + 1

print("\nBreakdown by r['month'] (주차월):", by_month)
print("Breakdown by r['reportMonth'] (월보고용 월):", by_report_m)

# Find items where r['month'] != '9월'
print("\nItems in 9월 whose r['month'] != '9월':")
for r in comp_9m:
    if r.get('month') != '9월':
        print(f"  ID: {r.get('id')} | Cust: {r.get('cust')} | Date: {r.get('date')} | Time: {r.get('time')} | Month: {r.get('month')} | ReportM: {r.get('reportMonth')} | WeekKey: {r.get('weekKey')}")
