# -*- coding: utf-8 -*-
import openpyxl, os, glob, sys
sys.stdout.reconfigure(encoding='utf-8')

pattern = r"X:\11. VOC, CCM 자료 등\26년\voc 취합\*.xlsx"
found = glob.glob(pattern)
print(f"Found {len(found)} files in voc 취합:")
for f in found:
    print(" -", os.path.basename(f))

target = r"X:\11. VOC, CCM 자료 등\26년\voc 취합\CX팀_26년_10월_VOC현황_취합.xlsx"
if not os.path.exists(target):
    target = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\voc 취합\CX팀_26년_10월_VOC현황_취합.xlsx"

if os.path.exists(target):
    wb = openpyxl.load_workbook(target, read_only=True)
    print("Sheets in 10월 취합:", wb.sheetnames)
    # Check if there is a CTI or 콜 sheet
    for s in wb.sheetnames:
        if '콜' in s or 'cti' in s.lower() or '전화' in s:
            print("Found call sheet:", s)
