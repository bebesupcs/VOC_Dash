# -*- coding: utf-8 -*-
import openpyxl
import os
import glob

# Search in NAS directory for 10월 3주 Excel file
nas_dir = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황"
print("NAS dir exists:", os.path.exists(nas_dir))
if os.path.exists(nas_dir):
    files = [f for f in os.listdir(nas_dir) if "10월" in f or "2026" in f or "VOC" in f]
    print("Files in NAS:", files[:10])
