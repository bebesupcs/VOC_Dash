import os
from pathlib import Path
import pyxlsb

base_dir = Path(r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년")
voc_dir = None
for d in base_dir.iterdir():
    if d.is_dir() and "voc" in d.name.lower():
        voc_dir = d
        break

print("VOC Dir:", voc_dir)
if voc_dir:
    for f in voc_dir.iterdir():
        if "9월4주차" in f.name and "월간" in f.name:
            print("Found file:", f.name)
            with pyxlsb.open_workbook(str(f)) as wb:
                print("Sheets:", wb.sheets)
                for sname in wb.sheets:
                    if "보상" in sname:
                        print("=== Inspecting sheet:", sname, "===")
                        with wb.get_sheet(sname) as s:
                            for idx, r in enumerate(s.rows()):
                                vals = [c.v for c in r if c.v is not None]
                                if vals and any(vals):
                                    if idx < 30 or "합계" in str(vals) or "총" in str(vals):
                                        print(f"Row {idx}: {vals}")
