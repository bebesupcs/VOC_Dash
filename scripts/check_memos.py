# -*- coding: utf-8 -*-
with open(r'D:\dev\VOC리포트\dashboard\render.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re

for term in ["loadMemos", "renderMemo", "renderCategoryInsights", "renderReport"]:
    idx = text.find(f"function {term}")
    if idx != -1:
        print(f"=== {term} ===")
        print(text[idx:idx+800])
        print('='*50)
