# -*- coding: utf-8 -*-
import os

nas_voc = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\VOC자료"
if os.path.exists(nas_voc):
    for root, dirs, files in os.walk(nas_voc):
        for f in files:
            if "2026" in f or "10월" in f:
                print(os.path.join(root, f))
