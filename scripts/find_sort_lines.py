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

for target in ["renderDelivery", "renderService", "renderReportThreePillars"]:
    m = re.search(rf'function {target}\(', text)
    if m:
        start = m.start()
        # Find next function or 5000 chars
        next_fn = text.find('\nfunction ', start + 10)
        end = next_fn if next_fn != -1 else start + 5000
        print(f"=== {target} (length: {end-start}) ===")
        fn_text = text[start:end]
        for line in fn_text.split('\n'):
            if 'sort' in line or 'orderBy' in line or 'order' in line or 'top' in line:
                print(f"  {line.strip()[:120]}")
