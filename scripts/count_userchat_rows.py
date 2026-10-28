import sys
import pyxlsb

sys.stdout.reconfigure(encoding='utf-8')
excel_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\voc 파일\CX팀_26년_10월2주차_VOC현황.xlsb"

with pyxlsb.open_workbook(excel_path) as wb:
    with wb.get_sheet('UserChat data') as s:
        count = 0
        for _ in s.rows():
            count += 1
        print(f"Total rows in UserChat data: {count}")
