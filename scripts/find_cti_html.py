# -*- coding: utf-8 -*-
with open('dashboard/index.html', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'ctiKpiRow' in line or 'ctiDirFilter' in line or 'tab-cti' in line:
            print(f"{i+1}: {line.strip()[:100]}")
