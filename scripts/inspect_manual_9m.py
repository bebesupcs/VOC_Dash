# -*- coding: utf-8 -*-
import io, os, sys, msoffcrypto, openpyxl
sys.stdout.reconfigure(encoding='utf-8')

fp = r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\월voc\CX팀_9월 VOC 현황_20261002 (1).xlsx'
PASSWORD = 'qpqptnv1'

decrypted = io.BytesIO()
with open(fp, 'rb') as f:
    office_file = msoffcrypto.OfficeFile(f)
    office_file.load_key(password=PASSWORD)
    office_file.decrypt(decrypted)

decrypted.seek(0)
wb = openpyxl.load_workbook(decrypted, data_only=True)

for sname in ['보상내역서', '보상제외 리스트', '클레임Raw']:
    ws = wb[sname]
    print(f"\n{'='*30} {sname} (max_row={ws.max_row}) {'='*30}")
    for r in range(1, min(15, ws.max_row + 1)):
        row_vals = [ws.cell(row=r, column=c).value for c in range(1, 15)]
        if any(v is not None for v in row_vals):
            print(f"Row {r:2d}: {row_vals}")

wb.close()
