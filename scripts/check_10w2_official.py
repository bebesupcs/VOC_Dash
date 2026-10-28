# -*- coding: utf-8 -*-
import pyxlsb, glob

files = glob.glob(r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\**\*10*2주*.xls*', recursive=True)
print('Target file:', files[0])

with pyxlsb.open_workbook(files[0]) as wb:
    with wb.get_sheet('UserChat data') as s:
        rows = list(s.rows())
        headers = [c.v for c in rows[0]]
        
        w2_rows = []
        for r in rows[1:]:
            vals = [c.v for c in r]
            if len(vals) > 108:
                year_val = vals[108]
                m_val = str(vals[100] or '')
                w_val = str(vals[101] or '')
                if ('2026' in str(year_val) or year_val == 2026.0) and '10' in m_val and '2' in w_val:
                    w2_rows.append(vals)
                    
        print(f"Total 10W2 rows: {len(w2_rows)}")
        
        with open('10w2_official_breakdown.txt', 'w', encoding='utf-8') as out:
            out.write(f"Total 10W2 rows: {len(w2_rows)}\n\n")
            
            # Count by Col 104 (클레임여부), Col 105 (채널), Col 107 (대구분)
            from collections import Counter
            c104 = Counter(r[104] for r in w2_rows)
            c107 = Counter(r[107] for r in w2_rows)
            out.write("=== Col 104 (클레임 여부) ===\n")
            for k, v in c104.items():
                out.write(f"  {k}: {v}\n")
                
            out.write("\n=== Col 107 (대구분/서비스/품질 등) ===\n")
            for k, v in c107.items():
                out.write(f"  {k}: {v}\n")
                
            out.write("\n=== '서비스' 관련 모든 행 목록 ===\n")
            for r in w2_rows:
                r_str = ' '.join(str(v) for v in r if v is not None)
                if '서비스' in str(r[107]) or '서비스' in str(r[104]) or '서비스' in str(r[5]):
                    cid = r[0]
                    tags = r[5]
                    m104 = r[104]
                    m107 = r[107]
                    name = r[2] if len(r) > 2 else ''
                    desc = r[4] if len(r) > 4 else ''
                    out.write(f"ID={cid} | Name={name} | Tags={tags} | Col104={m104} | Col107={m107}\n")
                    out.write(f"  Desc: {str(desc)[:100]}\n")

print("Done! Written to 10w2_official_breakdown.txt")
