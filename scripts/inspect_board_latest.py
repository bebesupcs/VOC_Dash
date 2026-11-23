# -*- coding: utf-8 -*-
import openpyxl

fp = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\raw\게시판 수기접수\게시판_취합운영.xlsx"
wb = openpyxl.load_workbook(fp, data_only=True)
print("Sheets:", wb.sheetnames)
ws = wb.active
for r in range(1, 20):
    row = [str(ws.cell(row=r, column=c).value or "") for c in range(1, 15)]
    if any(row):
        print(f"R{r}: " + " | ".join(row[:10]))
