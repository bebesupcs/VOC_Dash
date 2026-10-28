# -*- coding: utf-8 -*-
import pyxlsb, glob
import sys

sys.stdout.reconfigure(encoding='utf-8')
files = glob.glob(r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\**\*10*2주*.xls*', recursive=True)
print("File:", files[0])

with pyxlsb.open_workbook(files[0]) as wb:
    print("Sheets:", wb.sheets)
    for sheet_name in wb.sheets:
        if any(k in sheet_name for k in ['서비스', '클레임', '대시보드', '요약', '주간']):
            print(f"\n--- Sheet: {sheet_name} (first 20 rows) ---")
            with wb.get_sheet(sheet_name) as s:
                for idx, row in enumerate(s.rows()):
                    if idx >= 20:
                        break
                    vals = [c.v for c in row if c.v is not None]
                    if vals:
                        print(f"Row {idx}: {vals[:8]}")
