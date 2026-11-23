# -*- coding: utf-8 -*-
import sys
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

x_base = Path(r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\raw")
for p in x_base.rglob("*.xlsx"):
    print(p.parent.name, "-->", repr(p.name))
