import sys
import pyxlsb

sys.stdout.reconfigure(encoding='utf-8')
path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\voc 파일\CX팀_26년_10월2주차_VOC현황.xlsb"

with pyxlsb.open_workbook(path) as wb:
    with wb.get_sheet('UserChat data') as s:
        for r_idx, row in enumerate(s.rows()):
            vals = [c.v for c in row]
            for idx, col in enumerate(vals):
                print(f"{idx}: {col}")
            break
