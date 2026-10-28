import os, pyxlsb

base_26 = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년"
voc_dir = None
for d in os.listdir(base_26):
    if "voc" in d.lower():
        voc_dir = os.path.join(base_26, d)
        break

print("voc_dir:", voc_dir)
if voc_dir:
    for f in os.listdir(voc_dir):
        if "10" in f and "3" in f and f.endswith(".xlsb"):
            fpath = os.path.join(voc_dir, f)
            print("Found exact file:", fpath)
            with pyxlsb.open_workbook(fpath) as wb:
                print("Sheets in 10월 3주:", wb.sheets)
                for sname in wb.sheets:
                    with wb.get_sheet(sname) as s:
                        rows = list(s.rows())
                        header = [c.v for c in rows[0]] if rows else []
                        print(f"  [{sname}]: {len(rows)} rows, header: {header[:6]}")
