# -*- coding: utf-8 -*-
import io, os, sys, glob, msoffcrypto, openpyxl, json
sys.stdout.reconfigure(encoding='utf-8')

DIR_PATH = r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\월voc'
PASSWORD = 'qpqptnv1'

files = sorted(glob.glob(os.path.join(DIR_PATH, '*.xlsx')))
print(f"Found {len(files)} monthly excel files.")

summary_data = []

for fp in files:
    fname = os.path.basename(fp)
    decrypted = io.BytesIO()
    with open(fp, 'rb') as f:
        office_file = msoffcrypto.OfficeFile(f)
        office_file.load_key(password=PASSWORD)
        office_file.decrypt(decrypted)
        
    decrypted.seek(0)
    wb = openpyxl.load_workbook(decrypted, read_only=True, data_only=True)
    
    file_info = {'file': fname, 'sheets': {}}
    for sname in wb.sheetnames:
        ws = wb[sname]
        cnt = 0
        for row in ws.iter_rows(values_only=True):
            if any(cell is not None and str(cell).strip() != '' for cell in row):
                cnt += 1
        file_info['sheets'][sname] = cnt
        
    summary_data.append(file_info)
    print(f"[{fname}] Sheets: {file_info['sheets']}")
    sys.stdout.flush()

print("\nDone scanning all files!")
with open('manual_excel_summary.json', 'w', encoding='utf-8') as out:
    json.dump(summary_data, out, ensure_ascii=False, indent=2)
