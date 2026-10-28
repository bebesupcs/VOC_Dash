# -*- coding: utf-8 -*-
import re

with open(r'D:\dev\VOC리포트\dashboard\render.js', 'r', encoding='utf-8') as f:
    text = f.read()

matches = re.findall(r'charts\[["\']([^"\']+)["\']\]\s*=\s*new Chart\(', text)
print(f'Total charts created: {len(matches)}')
for m in matches:
    print(f'- {m}')
