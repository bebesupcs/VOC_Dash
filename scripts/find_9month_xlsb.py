import os
from pathlib import Path
import pyxlsb

root = Path(r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황")
print("Root exists:", root.exists())

target_file = None
for dirpath, dirnames, filenames in os.walk(str(root)):
    for f in filenames:
        if "9월" in f and "보상" not in f and f.endswith(".xlsb"):
            print("Found:", os.path.join(dirpath, f))
            target_file = os.path.join(dirpath, f)
            break
    if target_file:
        break

if target_file:
    with pyxlsb.open_workbook(target_file) as wb:
        print("Sheets in target:", wb.sheets)
        sname = [s for s in wb.sheets if "보상" in s]
        if sname:
            print("Opening sheet:", sname[0])
            with wb.get_sheet(sname[0]) as s:
                for idx, row in enumerate(s.rows()):
                    vals = [c.v for c in row if c.v is not None]
                    if vals:
                        print(f"Row {idx}: {vals}")
                    if idx >= 65:
                        break
