# -*- coding: utf-8 -*-
with open(r'D:\dev\VOC리포트\dashboard\render.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find("function renderReportThreePillars")
if idx != -1:
    print(text[idx:idx+2500])
