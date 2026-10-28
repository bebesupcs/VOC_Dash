import sys
import pyxlsb

sys.stdout.reconfigure(encoding='utf-8')
path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\voc 파일\CX팀_26년_10월2주차_VOC현황.xlsb"

target_ids = ['6ac75cbeafb194dab888', '6acc68e255ef7bf8f95f', '6acc9a8cb909417793ae', '6acd8aea3853f0c54878']

with pyxlsb.open_workbook(path) as wb:
    with wb.get_sheet('UserChat data') as s:
        header = None
        for r_idx, row in enumerate(s.rows()):
            vals = [c.v for c in row]
            if r_idx == 0:
                header = vals
            else:
                if len(vals) > 0 and vals[0] in target_ids:
                    print(f"\nFound ID: {vals[0]}")
                    for i in [1, 2, 4, 5, 7, 16, 17, 32, 52, 97, 98, 99, 100, 101, 104, 105, 107, 108]:
                        col_name = header[i] if i < len(header) else f"col_{i}"
                        val = vals[i] if i < len(vals) else None
                        print(f"  {col_name} ({i}): {val}")
