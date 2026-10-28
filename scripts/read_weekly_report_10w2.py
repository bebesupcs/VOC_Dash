# -*- coding: utf-8 -*-
import pyxlsb, glob

files = glob.glob(r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\**\*10*2주*.xls*', recursive=True)

with pyxlsb.open_workbook(files[0]) as wb:
    target_sheet = '주간 보고서' if '주간 보고서' in wb.sheets else wb.sheets[1]
    with wb.get_sheet(target_sheet) as s:
        rows = list(s.rows())
        with open('weekly_report_10w2.txt', 'w', encoding='utf-8') as out:
            for r_idx, r in enumerate(rows[:100]):
                vals = [c.v for c in r]
                # print non-empty
                row_str = " | ".join(f"{v}" for v in vals if v is not None)
                if row_str.strip():
                    out.write(f"R{r_idx+1}: {row_str}\n")

print("Written to weekly_report_10w2.txt")
