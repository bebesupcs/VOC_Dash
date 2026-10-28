# -*- coding: utf-8 -*-
import json, sys, os
sys.path.insert(0, os.path.abspath('.'))

from scripts.generate_report_excel import load_voc_data, is_qc_chat

data = load_voc_data()
chats_by_week = data.get("CHATS_BY_WEEK", {})
all_chats_flat = []
seen_ids = set()
for wk, clist in chats_by_week.items():
    for c in clist:
        cid = c.get("id")
        if cid and cid not in seen_ids:
            seen_ids.add(cid)
            all_chats_flat.append(c)

quality_sep = [c for c in all_chats_flat if is_qc_chat(c) and ((c.get("time") and str(c.get("time")).startswith("2026-09")) or (c.get("date") and str(c.get("date")).startswith("2026-09")))]

with open('parsed_user_rows.json', 'r', encoding='utf-8') as f:
    user_d = json.load(f)

print(f"System September Quality Chats: {len(quality_sep)}")
v_count = len(user_d['v_rows'])
ex_count = len(user_d['ex_rows'])
print(f"User Table Total Rows: {v_count + ex_count} (V: {v_count}, 제외: {ex_count})")

user_all = user_d['v_rows'] + user_d['ex_rows']

matched = []
unmatched_user = []
used_chat_ids = set()

for ur in user_all:
    u_cust = ur[3].strip()
    u_date = ur[5].strip()
    u_mgr = ur[4].strip()
    u_mid = ur[1].strip()
    u_sub = ur[2].strip()
    u_status = ur[-1].strip()
    
    found = False
    for c in quality_sep:
        if c.get('id') in used_chat_ids:
            continue
        c_cust = (c.get('cust') or c.get('custName') or c.get('name') or '').strip()
        c_date = (c.get('time') or c.get('date') or '')[:10]
        c_mgr = (c.get('agent') or '').strip()
        
        # Check matching
        if (u_cust and u_cust == c_cust) or (u_date == c_date and u_mgr and u_mgr == c_mgr and u_cust and u_cust in c_cust):
            matched.append((ur, c))
            used_chat_ids.add(c.get('id'))
            found = True
            break
            
    if not found:
        # try looser matching
        for c in quality_sep:
            if c.get('id') in used_chat_ids:
                continue
            c_cust = (c.get('cust') or c.get('custName') or c.get('name') or '').strip()
            c_date = (c.get('time') or c.get('date') or '')[:10]
            if u_date == c_date and u_cust == c_cust:
                matched.append((ur, c))
                used_chat_ids.add(c.get('id'))
                found = True
                break

    if not found:
        unmatched_user.append(ur)

print(f"Matched User Rows: {len(matched)} / {len(user_all)}")
print(f"Unmatched User Rows: {len(unmatched_user)}")
print(f"DB Quality Chats not in User Table: {len(quality_sep) - len(used_chat_ids)}")

with open('user_vs_db_diff.txt', 'w', encoding='utf-8') as out:
    out.write(f"System DB Sep Quality Chats: {len(quality_sep)}\n")
    out.write(f"User Table Rows: {len(user_all)} (V: {v_count}, 제외: {ex_count})\n\n")
    out.write("--- DB chats NOT in User Table ---\n")
    for c in quality_sep:
        if c.get('id') not in used_chat_ids:
            out.write(f"[{c.get('time') or c.get('date')}] ID: {c.get('id')} | Cust: {c.get('cust') or c.get('name')} | Agent: {c.get('agent')} | Mid: {c.get('mid')} | Sub: {c.get('sub')} | Issue: {(c.get('issue') or '')[:60]}\n")
    
    out.write("\n--- Unmatched User Rows ---\n")
    for ur in unmatched_user:
        out.write(f"[{ur[5]}] Cust: {ur[3]} | Mgr: {ur[4]} | Cat: {ur[1]}>{ur[2]} | Text: {ur[8][:60]}\n")

print("Detailed diff saved to user_vs_db_diff.txt")
