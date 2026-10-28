# -*- coding: utf-8 -*-
import io, msoffcrypto, openpyxl, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

fp = r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\월voc\CX팀_9월 VOC 현황_20261002 (1).xlsx'
dec = io.BytesIO()
with open(fp, 'rb') as f:
    o = msoffcrypto.OfficeFile(f)
    o.load_key('qpqptnv1')
    o.decrypt(dec)
dec.seek(0)
wb = openpyxl.load_workbook(dec, read_only=True, data_only=True)

ws = wb['클레임Raw']
cats = Counter()
m9_rows = 0
for i, r in enumerate(ws.iter_rows(values_only=True)):
    if i < 3: continue
    if len(r) > 10 and str(r[1]) == '2026' and '9월' in str(r[2] or ''):
        m9_rows += 1
        d_cat = f"{r[7]}>{r[8]}>{r[9]}"
        cats[d_cat] += 1
print(f"=== 9월 클레임Raw 총 {m9_rows}건 중 대/중/소분류별 건수 ===")
for cat, cnt in cats.most_common(30):
    print(f"  {cnt:2d}건: {cat}")

ws_ex = wb['보상제외 리스트']
ex_reasons = []
for i, r in enumerate(ws_ex.iter_rows(values_only=True)):
    if i == 0: continue
    if any(r):
        c_name = str(r[10]) if len(r) > 10 else ''
        c_cat = f"{r[7]}>{r[8]}>{r[9]}" if len(r) > 9 else ''
        c_desc = str(r[14]) if len(r) > 14 and r[14] is not None else ''
        c_act = str(r[15]) if len(r) > 15 and r[15] is not None else ''
        ex_reasons.append((c_name, c_cat, c_desc, c_act))

print(f"\n=== 9월 보상제외 리스트 총 {len(ex_reasons)}건 상세 내역 ===")
for name, cat, desc, act in ex_reasons:
    print(f"  [{name}] {cat} | 사유/조치: {act[:35]} / 문의: {desc[:25]}")
