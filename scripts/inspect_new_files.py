# -*- coding: utf-8 -*-
import os, sys
import pandas as pd
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

x_base = Path(r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\raw")

print("=== 1. 채널톡 엑셀 (20261112.xlsx) ===")
ct_path = x_base / "채널톡 데이터 원본" / "20261112.xlsx"
if ct_path.exists():
    xl = pd.ExcelFile(ct_path)
    print("Sheets:", xl.sheet_names)
    df = pd.read_excel(ct_path, sheet_name=xl.sheet_names[0], nrows=3)
    print("Columns in sheet 0:", list(df.columns)[:10])
else:
    print("Not found:", ct_path)

print("\n=== 2. 게시판 엑셀 (게시판_위탁운영.xlsx) ===")
bd_path = x_base / "게시판 데이터 원본" / "게시판_위탁운영.xlsx"
if bd_path.exists():
    xl_b = pd.ExcelFile(bd_path)
    print("Sheets:", xl_b.sheet_names)
    df_b = pd.read_excel(bd_path, sheet_name=xl_b.sheet_names[0], nrows=3)
    print("Columns in sheet 0:", list(df_b.columns)[:10])
else:
    print("Not found:", bd_path)

print("\n=== 3. 배송 엑셀 (CJ대한통운 CS접수_1111.xlsx & 풀필먼트20261104.xlsx) ===")
cj_path = x_base / "배송 데이터 원본" / "CJ대한통운 CS접수_1111.xlsx"
if cj_path.exists():
    xl_cj = pd.ExcelFile(cj_path)
    print("CJ Sheets:", xl_cj.sheet_names)
ff_path = x_base / "배송 데이터 원본" / "풀필먼트20261104.xlsx"
if ff_path.exists():
    xl_ff = pd.ExcelFile(ff_path)
    print("FF Sheets:", xl_ff.sheet_names)
