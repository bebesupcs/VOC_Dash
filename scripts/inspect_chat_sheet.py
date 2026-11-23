import pyxlsb
import sys
sys.stdout.reconfigure(encoding='utf-8')

path = r'x:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\voc 파일\CX팀_26년_10월3주차_VOC현황.xlsb'
with pyxlsb.open_workbook(path) as wb:
    with wb.get_sheet('채팅') as s:
        for i, row in enumerate(s.rows()):
            if i < 30:
                vals = [c.v for c in row if c.v is not None]
                if vals:
                    print(f"Row {i}: {vals}")
            else:
                break
