# -*- coding: utf-8 -*-
import os
import openpyxl

target_dir = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\voc 파일"
print("Directory exists:", os.path.exists(target_dir))
if os.path.exists(target_dir):
    for f in os.listdir(target_dir):
        if "하반기" in f or "10월" in f:
            print("File:", f)
            fp = os.path.join(target_dir, f)
            try:
                wb = openpyxl.load_workbook(fp, data_only=True)
                print("  Sheets:", wb.sheetnames)
                for sname in wb.sheetnames:
                    if any(k in sname for k in ["차트", "대시보드", "추이", "주간"]):
                        print(f"  --> Interesting sheet: {sname}")
                        ws = wb[sname]
                        for r in range(1, 20):
                            row = [str(ws.cell(row=r, column=c).value or "") for c in range(1, 15)]
                            if any(row):
                                print(f"    R{r}: " + " | ".join(row[:10]))
            except Exception as e:
                print("  Error reading:", e)
