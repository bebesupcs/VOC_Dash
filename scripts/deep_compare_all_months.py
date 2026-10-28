# -*- coding: utf-8 -*-
import io, os, sys, glob, msoffcrypto, openpyxl, json, re
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding='utf-8')

DIR_PATH = r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\월voc'
PASSWORD = 'qpqptnv1'

# Load our system data
with open('dashboard/data.json', 'r', encoding='utf-8') as f:
    djson = json.load(f)

files = sorted(glob.glob(os.path.join(DIR_PATH, '*.xlsx')))

report_data = []

for fp in files:
    fname = os.path.basename(fp)
    # Extract month number from filename (e.g. CX팀_3월... -> 3)
    m_match = re.search(r'(\d+)월', fname)
    m_num = int(m_match.group(1)) if m_match else 0
    m_key = f"2026-{str(m_num).zfill(2)}"
    
    print(f"\n==========================================")
    print(f"Analyzing {fname} ({m_key})")
    print(f"==========================================")
    
    decrypted = io.BytesIO()
    with open(fp, 'rb') as f:
        office_file = msoffcrypto.OfficeFile(f)
        office_file.load_key(password=PASSWORD)
        office_file.decrypt(decrypted)
        
    decrypted.seek(0)
    wb = openpyxl.load_workbook(decrypted, read_only=True, data_only=True)
    
    # 1. Inspect 보상내역서
    ws_comp = wb['보상내역서'] if '보상내역서' in wb.sheetnames else None
    comp_items = []
    comp_total = 0
    if ws_comp:
        for row in ws_comp.iter_rows(values_only=True):
            if len(row) >= 4:
                val_p = row[2]
                val_c = row[3]
                if isinstance(val_c, (int, float)) and val_p and '제품명' not in str(val_p) and '합계' not in str(val_p):
                    comp_items.append((str(val_p).strip(), int(val_c)))
                    comp_total += int(val_c)
                
    # 2. Inspect 보상제외 리스트
    ws_ex = wb['보상제외 리스트'] if '보상제외 리스트' in wb.sheetnames else (wb['제외리스트'] if '제외리스트' in wb.sheetnames else None)
    ex_items = []
    if ws_ex:
        for idx, row in enumerate(ws_ex.iter_rows(values_only=True)):
            if idx == 0: continue # header
            if any(v is not None and str(v).strip() != '' for v in row):
                ex_items.append(list(row))
                
    # 3. Inspect 클레임Raw for this month
    ws_raw = wb['클레임Raw'] if '클레임Raw' in wb.sheetnames else (wb['클레임raw'] if '클레임raw' in wb.sheetnames else None)
    raw_month_items = []
    if ws_raw:
        for idx, row in enumerate(ws_raw.iter_rows(values_only=True)):
            if idx < 3: continue # header rows
            if len(row) >= 4:
                y_val = row[1]
                m_val = str(row[2] or '')
                date_val = str(row[13] or '') if len(row) > 13 else ''
                is_match = False
                if str(y_val) == '2026':
                    if f"{m_num}월" in m_val:
                        is_match = True
                    elif date_val.startswith(m_key):
                        is_match = True
                if is_match:
                    raw_month_items.append(row)

    # 4. Compare with our System DB
    # Filter chats in data.json for m_key
    sys_quality_chats = []
    for wk, clist in djson.get('CHATS_BY_WEEK', {}).items():
        for c in clist:
            if c.get('journey') in ('제품사용', '품질'):
                t_str = str(c.get('time') or '')[:7]
                d_str = str(c.get('date') or '')[:7]
                if t_str == m_key or d_str == m_key:
                    sys_quality_chats.append(c)

    print(f"Manual Excel File:")
    print(f"  - 보상내역서 클레임 수 합계: {comp_total}건 (제품 종류: {len(comp_items)}종)")
    print(f"  - 보상제외 리스트 행 수: {len(ex_items)}건")
    print(f"  - 클레임Raw 해당 월 건수: {len(raw_month_items)}건")
    print(f"System DB:")
    print(f"  - 시스템 품질 클레임 총건수: {len(sys_quality_chats)}건")
    
    report_data.append({
        'month': f"{m_num}월",
        'file': fname,
        'manual_comp_total': comp_total,
        'manual_ex_count': len(ex_items),
        'manual_raw_count': len(raw_month_items),
        'sys_quality_count': len(sys_quality_chats),
        'diff': len(sys_quality_chats) - (comp_total + len(ex_items)),
        'ex_sample': [str(x[9]) if len(x) > 9 else '' for x in ex_items[:5]]
    })
    wb.close()

with open('monthly_comparison_results.json', 'w', encoding='utf-8') as out:
    json.dump(report_data, out, ensure_ascii=False, indent=2)

print("\nSaved detailed comparison to monthly_comparison_results.json")
