import os, openpyxl

base = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년"
down_dir = None
for d in os.listdir(base):
    if "채널톡" in d or "다운" in d:
        down_dir = os.path.join(base, d)
        print("Found dir:", d)

if down_dir:
    files = [f for f in os.listdir(down_dir) if "10-22" in f and f.endswith(".xlsx")]
    print("Files on 10-22:", files)
    if files:
        fpath = os.path.join(down_dir, files[0])
        wb = openpyxl.load_workbook(fpath, read_only=True)
        sheet = wb.active
        headers = list(next(sheet.iter_rows(values_only=True)))
        print("Headers:", headers)
        
        matches = []
        for r in sheet.iter_rows(values_only=True):
            r_str = " ".join(str(x) for x in r if x is not None)
            if "이혜림" in r_str or "보푸라기" in r_str or "기타이물" in r_str:
                matches.append(r)
        print(f"Matched rows in 10-22 excel: {len(matches)}")
        for m in matches[:5]:
            print(m[:8])
