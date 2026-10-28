import sys
import pyxlsb

sys.stdout.reconfigure(encoding='utf-8')
path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\voc 파일\CX팀_26년_10월2주차_VOC현황.xlsb"

with pyxlsb.open_workbook(path) as wb:
    with wb.get_sheet('UserChat data') as s:
        claims = []
        for r_idx, row in enumerate(s.rows()):
            if r_idx == 0:
                continue
            vals = [c.v for c in row]
            if len(vals) > 108 and vals[108] == 2026.0:
                m = str(vals[100]).strip()
                w = str(vals[101]).strip()
                claim_yn = str(vals[104]).strip()
                if '10' in m and '2' in w and claim_yn == '클레임':
                    claims.append(vals)

        print(f"Total claims in 10W2: {len(claims)}")
        for idx, c in enumerate(claims):
            cid = c[0]
            tags = c[5]
            channel = c[105]
            gubun = c[107]
            print(f"[{idx+1}] ID={cid} | channel={channel} | gubun={gubun} | tags={tags}")
