# -*- coding: utf-8 -*-
import pyxlsb
import os

xlsb_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\voc 파일\CX팀_26년_10월3주차_VOC현황.xlsb"
with pyxlsb.open_workbook(xlsb_path) as wb:
    print("Sheets in 10월3주차:", wb.sheets)
    
    # Check sheet that has claims or raw
    for sheet_name in wb.sheets:
        if any(k in sheet_name for k in ["품질", "원단", "물티슈", "raw", "클레임", "접수"]):
            print(f"\n--- Sheet: {sheet_name} ---")
            with wb.get_sheet(sheet_name) as s:
                for i, row in enumerate(s.rows()):
                    if i < 5:
                        vals = [c.v for c in row if c.v is not None]
                        print(f"Row {i}: {vals[:10]}")
                    if i >= 5:
                        break
