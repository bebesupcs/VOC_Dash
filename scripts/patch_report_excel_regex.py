# -*- coding: utf-8 -*-
import re

with open('scripts/generate_report_excel.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Replace get_chats_for_p
pat_get_chats = r'    def get_chats_for_p\(p\):[\s\S]*?return \[\]'
new_get_chats = """    def get_chats_for_p(p):
        if not p: return []
        pk = str(p.get("key", ""))
        if is_week:
            return voc_data.get("CHATS_BY_WEEK", {}).get(pk, [])
        def get_c_date(c):
            return str(c.get("date") or c.get("time") or "")[:10]
        if "-" in pk and len(pk) == 7 and "W" not in pk and "-Q" not in pk:
            return [c for c in all_chats_flat if get_c_date(c).startswith(pk)]
        if "-Q" in pk:
            y, q = pk.split("-Q")
            qm = [f"{y}-{str((int(q)-1)*3 + i).zfill(2)}" for i in [1, 2, 3]]
            return [c for c in all_chats_flat if any(get_c_date(c).startswith(m) for m in qm)]
        if len(pk) == 4 and pk.isdigit():
            return [c for c in all_chats_flat if get_c_date(c).startswith(pk)]
        return []"""

m1 = re.search(pat_get_chats, text)
if m1:
    text = text[:m1.start()] + new_get_chats + text[m1.end():]
    print("Found and replaced get_chats_for_p")
else:
    print("Failed to find get_chats_for_p")

# 2. Replace is_item_in_p
pat_is_item = r'    def is_item_in_p\(item, p\):[\s\S]*?return False'
new_is_item = """    def is_item_in_p(item, p):
        if not item or not p: return False
        pk = str(p.get("key", ""))
        if is_week:
            return item.get("weekKey") == pk or item.get("week") == pk
        it_date = str(item.get("date") or item.get("claimDate") or item.get("time") or item.get("managedAt") or "")[:10]
        if "-" in pk and len(pk) == 7 and "W" not in pk and "-Q" not in pk:
            return it_date.startswith(pk)
        if "-Q" in pk:
            y, q = pk.split("-Q")
            qm = [f"{y}-{str((int(q)-1)*3 + i).zfill(2)}" for i in [1, 2, 3]]
            return any(it_date.startswith(m) for m in qm)
        if len(pk) == 4 and pk.isdigit():
            return it_date.startswith(pk)
        return False"""

m2 = re.search(pat_is_item, text)
if m2:
    text = text[:m2.start()] + new_is_item + text[m2.end():]
    print("Found and replaced is_item_in_p")
else:
    print("Failed to find is_item_in_p")

with open('scripts/generate_report_excel.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Saved generate_report_excel.py")
