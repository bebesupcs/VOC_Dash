# -*- coding: utf-8 -*-
import io, os, sys, msoffcrypto, openpyxl
from collections import Counter
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

ws_raw = wb['클레임Raw']
# Read all 2026 9월 rows from 클레임Raw
raw_9m = []
categories = Counter()
channels = Counter()

for idx, row in enumerate(ws_raw.iter_rows(values_only=True)):
    if idx < 3: continue
    if len(row) >= 14:
        y_val = row[1]
        m_val = str(row[2] or '')
        date_val = str(row[13] or '')
        if str(y_val) == '2026' and ('9월' in m_val or date_val.startswith('2026-09')):
            raw_9m.append(row)
            # Column 6: 대분류, 8: 중분류, 9: 소분류, 10: 고객명
            cat_large = row[6] or row[8]
            cat_mid = row[9] if len(row) > 9 else ''
            cat_sub = row[10] if len(row) > 10 else ''
            categories[f"{cat_large}>{cat_mid}>{cat_sub}"] += 1

print(f"Total 2026 9월 rows in 클레임Raw: {len(raw_9m)}")
print("\nTop Categories in 클레임Raw 9월:")
for cat, cnt in categories.most_common(20):
    print(f"  {cat}: {cnt}건")

wb.close()
