# -*- coding: utf-8 -*-
import io, msoffcrypto, openpyxl, json, glob, os, sys
sys.stdout.reconfigure(encoding='utf-8')

# Compare 3월 and 4월 chats
with open('dashboard/data.json', 'r', encoding='utf-8') as f:
    djson = json.load(f)

# Let's inspect 3월 manual file
fp3 = r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\월voc\CX팀_3월 VOC 현황_20260403.xlsx'
dec = io.BytesIO()
with open(fp3, 'rb') as f:
    o = msoffcrypto.OfficeFile(f)
    o.load_key('qpqptnv1')
    o.decrypt(dec)
dec.seek(0)
wb = openpyxl.load_workbook(dec, read_only=True, data_only=True)

# Get all chat IDs or customer names in 3월 manual
comp_names = []
ws_c = wb['보상내역서']
# ws_c only has product and count!
# Where are the detailed chats for 보상내역서?
# Let's see the sheet names in 3월
print("Sheets in 3월:", wb.sheetnames)
ws_ex = wb['제외리스트'] if '제외리스트' in wb.sheetnames else wb['보상제외 리스트']
ex_names = []
if ws_ex:
    for idx, r in enumerate(ws_ex.iter_rows(values_only=True)):
        if idx == 0: continue
        if any(r):
            ex_names.append((r[10] if len(r)>10 else '', r[11] if len(r)>11 else ''))
print("3월 제외리스트 고객/ID:", ex_names[:10])
wb.close()
