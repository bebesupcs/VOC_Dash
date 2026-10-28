# -*- coding: utf-8 -*-
import pyxlsb, glob

files = glob.glob(r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\**\*10*2주*.xls*', recursive=True)

with pyxlsb.open_workbook(files[0]) as wb:
    sheet_name = '대시보드' if '대시보드' in wb.sheets else wb.sheets[0]
    with wb.get_sheet(sheet_name) as s:
        rows = list(s.rows())
        with open('dashboard_sheet_10w2.txt', 'w', encoding='utf-8') as out:
            for r_idx, r in enumerate(rows[:80]):
                vals = [c.v for c in r]
                row_str = " | ".join(f"{v}" for v in vals if v is not None)
                if row_str.strip():
                    out.write(f"R{r_idx+1}: {row_str}\n")

print("Written to dashboard_sheet_10w2.txt")
