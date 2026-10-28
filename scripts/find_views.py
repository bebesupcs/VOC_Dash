# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8')
with open('dashboard/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

for m in re.finditer(r'id=["\']view-[^"\']+["\']', text):
    start = max(0, m.start() - 20)
    end = min(len(text), m.end() + 60)
    print(text[start:end].replace('\n', ' '))
