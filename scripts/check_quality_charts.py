# -*- coding: utf-8 -*-
with open(r'D:\dev\VOC리포트\dashboard\render.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re

for ch in ["qualityProductChart", "qualityMfgChart", "qualityMallChart"]:
    idx = text.find(ch)
    if idx != -1:
        print(f"=== {ch} ===")
        print(text[max(0, idx-300):min(len(text), idx+500)])
        print('='*50)
