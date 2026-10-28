import os, pyxlsb

fpath = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\voc 파일\CX팀_26년_10월3주_VOC현황.xlsb"
print(f"Inspecting: {fpath}")

with pyxlsb.open_workbook(fpath) as wb:
    print("Sheets:", wb.sheets)
    
    # Check if there is a '품질raw' or 'raw' or 'UserChat data' or '종합리포트'
    for sname in wb.sheets:
        with wb.get_sheet(sname) as s:
            first_row = next(s.rows(), None)
            vals = [c.v for c in first_row] if first_row else []
            count = sum(1 for _ in s.rows()) + (1 if first_row else 0)
            print(f"Sheet '{sname}': {count} rows, cols: {vals[:8]}")
