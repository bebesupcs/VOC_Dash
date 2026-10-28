# -*- coding: utf-8 -*-
import sys
import os
import shutil
import pyxlsb

sys.stdout.reconfigure(encoding='utf-8')

base = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년"
for entry in os.scandir(base):
    if entry.is_dir() and "voc" in entry.name.lower():
        print("Found dir:", repr(entry.name))
        for f in os.scandir(entry.path):
            if "10" in f.name and "2" in f.name:
                print("Found file:", repr(f.name))
                dst = r"C:\Users\hshwa\AppData\Local\Temp\voc_10w2.xlsb"
                if not os.path.exists(dst):
                    shutil.copyfile(f.path, dst)
                    print("Copied!")
                
                with pyxlsb.open_workbook(dst) as wb:
                    print("Sheets:", wb.sheets)
                    with wb.get_sheet("대시보드") as sheet:
                        for idx, row in enumerate(sheet.rows()):
                            if idx < 40:
                                vals = [c.v for c in row if c.v is not None]
                                if vals:
                                    print(f"Row {idx:2d}: {vals[:10]}")
