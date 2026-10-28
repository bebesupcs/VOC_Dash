# -*- coding: utf-8 -*-
with open('scripts/generate_report_excel.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = 'm_str = str(r.get("month", ""))'
replacement = 'm_str = str(r.get("reportMonth") or r.get("month", ""))'

if target in text:
    text = text.replace(target, replacement, 1)
    with open('scripts/generate_report_excel.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Successfully updated ws_comp_all to use reportMonth!")
else:
    print("Target not found in generate_report_excel.py")
