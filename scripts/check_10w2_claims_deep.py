# -*- coding: utf-8 -*-
import pyxlsb, glob

files = glob.glob(r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\**\*10*2주*.xls*', recursive=True)

with pyxlsb.open_workbook(files[0]) as wb:
    with wb.get_sheet('UserChat data') as s:
        rows = list(s.rows())
        headers = [c.v for c in rows[0]]
        
        claims = []
        for r in rows[1:]:
            vals = [c.v for c in r]
            if len(vals) > 108:
                year_val = vals[108]
                m_val = str(vals[100] or '')
                w_val = str(vals[101] or '')
                claim_val = str(vals[104] or '')
                if ('2026' in str(year_val) or year_val == 2026.0) and '10' in m_val and '2' in w_val and claim_val == '클레임':
                    claims.append(vals)

        with open('10w2_claims_deep.txt', 'w', encoding='utf-8') as out:
            out.write(f"Total 10W2 Claims: {len(claims)}\n\n")
            # Print headers for cols >= 95
            out.write("=== Headers for cols 95-108 ===\n")
            for idx in range(95, len(headers)):
                out.write(f"  Col {idx}: {headers[idx]}\n")
                
            out.write("\n=== 50 Claims List ===\n")
            for c in claims:
                cid = c[0]
                tags = c[5]
                name = c[2]
                extra_cols = [f"{headers[i]}={c[i]}" for i in range(95, min(len(headers), len(c))) if c[i] is not None]
                out.write(f"ID={cid} | Name={name} | Tags={tags}\n")
                out.write(f"  Extras: {' | '.join(extra_cols)}\n")

print("Done! Written to 10w2_claims_deep.txt")
