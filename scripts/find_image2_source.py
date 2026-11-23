# -*- coding: utf-8 -*-
import os
import glob

dirs = [
    r"X:\11. VOC, CCM 자료 등",
    r"C:\Users\hshwa\Downloads",
    r"C:\Users\hshwa\Desktop",
    r"C:\Users\hshwa\Documents"
]

print("Searching for pptx, pdf, xlsx...")
found = []
for d in dirs:
    if not os.path.exists(d): continue
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith(('.pptx', '.pdf', '.xlsx', '.csv')) and not f.startswith('~$'):
                fp = os.path.join(root, f)
                # check modification time
                try:
                    mt = os.path.getmtime(fp)
                    # within last 14 days
                    import time
                    if time.time() - mt < 14 * 86400:
                        found.append((mt, fp))
                except Exception:
                    pass

found.sort(key=lambda x: x[0], reverse=True)
for mt, fp in found[:30]:
    import time
    print(f"{time.ctime(mt)} | {fp}")
