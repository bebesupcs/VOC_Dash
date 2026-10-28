# -*- coding: utf-8 -*-
import json

with open(r'D:\dev\VOC리포트\dashboard\data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

weeks = d.get('WEEKS', [])
raw_sum = d.get('RAW_SUMMARY', {})

for w in weeks:
    k = w['key']
    r = raw_sum.get(k, {})
    if r.get('total_offered_raw') in (413, 395) or r.get('raw_board') == 169:
        print("Found:", k, w.get('label'), w.get('week_of_month'), r)
