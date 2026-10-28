# -*- coding: utf-8 -*-
import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

with open(r'D:\dev\VOC리포트\dashboard\render.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '총 인입 (전수)' in line or 'total_offered_raw' in line:
        print(f"Line {i+1}:")
        for j in range(max(0, i-5), min(len(lines), i+25)):
            print(f"{j+1}: {lines[j]}", end="")
        print("="*50)
