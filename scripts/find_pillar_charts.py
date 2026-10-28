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

# find all charts created in renderQuality, renderDelivery, renderService
for fn_name in ["renderQuality", "renderDelivery", "renderService"]:
    m = re.search(rf'function {fn_name}\(', text)
    if m:
        start = m.start()
        next_fn = text.find('\nfunction ', start + 10)
        end = next_fn if next_fn != -1 else start + 10000
        fn_code = text[start:end]
        chart_matches = re.findall(r'(?:charts\[["\']|barChart\(["\']|doughnutChart\(["\']|lineChart\(["\'])([^"\']+)', fn_code)
        print(f"=== {fn_name} charts ===")
        for ch in set(chart_matches):
            print(f"  - {ch}")
