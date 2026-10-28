import os, pyxlsb

base_26 = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년"
voc_dir = [os.path.join(base_26, d) for d in os.listdir(base_26) if "voc" in d.lower()][0]
target_f = [os.path.join(voc_dir, f) for f in os.listdir(voc_dir) if "10" in f and "3" in f and f.endswith(".xlsb")][0]
print("Target:", target_f)

with pyxlsb.open_workbook(target_f) as wb:
    print("Sheets in 10월 3주 file:", wb.sheets)
