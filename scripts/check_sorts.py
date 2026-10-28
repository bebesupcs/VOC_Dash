# -*- coding: utf-8 -*-
import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

with open(r'D:\dev\VOC리포트\dashboard\render.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re

def find_sort_logic(fn_name):
    m = re.search(rf'function {fn_name}', text)
    if m:
        start = m.start()
        end = min(len(text), start + 3000)
        print(f"=== {fn_name} ===")
        # find sort calls
        sort_matches = [s.start() for s in re.finditer(r'\.sort\(', text[start:end])]
        for s in sort_matches:
            s_abs = start + s
            print(text[max(start, s_abs-80):min(end, s_abs+200)])
            print('---')

find_sort_logic("renderQuality")
find_sort_logic("renderDelivery")
find_sort_logic("renderService")
find_sort_logic("renderReportThreePillars")
