# -*- coding: utf-8 -*-
with open('scripts/generate_report_excel.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace get_chats_for_p
old_get_chats = """    def get_chats_for_p(p):
        if not p: return []
        pk = str(p.get("key", ""))
        if is_week:
            return voc_data.get("CHATS_BY_WEEK", {}).get(pk, [])
        if "-" in pk and len(pk) == 7 and "W" not in pk and "-Q" not in pk:
            return [c for c in all_chats_flat if (c.get("time") and str(c.get("time")).startswith(pk)) or (c.get("date") and str(c.get("date")).startswith(pk))]
        if "-Q" in pk:
            y, q = pk.split("-Q")
            qm = [f"{y}-{str((int(q)-1)*3 + i).zfill(2)}" for i in [1, 2, 3]]
            return [c for c in all_chats_flat if any((c.get("time") and str(c.get("time")).startswith(m)) or (c.get("date") and str(c.get("date")).startswith(m)) for m in qm)]
        if len(pk) == 4 and pk.isdigit():
            return [c for c in all_chats_flat if (c.get("time") and str(c.get("time")).startswith(pk)) or (c.get("date") and str(c.get("date")).startswith(pk))]
        return []"""

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

# Replace is_item_in_p
old_is_item = """    def is_item_in_p(item, p):
        if not item or not p: return False
        pk = str(p.get("key", ""))
        if is_week:
            return item.get("weekKey") == pk or item.get("week") == pk
        if "-" in pk and len(pk) == 7 and "W" not in pk and "-Q" not in pk:
            return (item.get("time") and str(item.get("time")).startswith(pk)) or (item.get("date") and str(item.get("date")).startswith(pk)) or (item.get("claimDate") and str(item.get("claimDate")).startswith(pk))
        if "-Q" in pk:
            y, q = pk.split("-Q")
            qm = [f"{y}-{str((int(q)-1)*3 + i).zfill(2)}" for i in [1, 2, 3]]
            return any((item.get("time") and str(item.get("time")).startswith(m)) or (item.get("date") and str(item.get("date")).startswith(m)) or (item.get("claimDate") and str(item.get("claimDate")).startswith(m)) for m in qm)
        if len(pk) == 4 and pk.isdigit():
            return (item.get("time") and str(item.get("time")).startswith(pk)) or (item.get("date") and str(item.get("date")).startswith(pk)) or (item.get("claimDate") and str(item.get("claimDate")).startswith(pk))
        return False"""

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

if old_get_chats in text and old_is_item in text:
    text = text.replace(old_get_chats, new_get_chats).replace(old_is_item, new_is_item)
    with open('scripts/generate_report_excel.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Successfully patched generate_report_excel.py!")
else:
    print("Could not match exact string in generate_report_excel.py")
