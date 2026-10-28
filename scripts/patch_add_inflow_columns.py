# -*- coding: utf-8 -*-
import sys, re

# ==========================================
# 1. Update dashboard/engine.js
# ==========================================
with open('dashboard/engine.js', 'r', encoding='utf-8') as f:
    engine_text = f.read()

old_engine_rawchats_pat = r'function rawChats\(period\) \{[\s\S]*?return chatsForWeekKey\(period\.key\);\s*\}'
new_engine_rawchats = """function rawChats(period) {
  period = period || (typeof getPeriod === "function" ? getPeriod() : null);
  if (!period) return [];
  // 1. 월간 모드: 달력 1일 00:00:00 ~ 말일 23:59:59 (인입일시 또는 접수일자 기준 전체 포함)
  if (period.key && /^\\d{4}-\\d{2}$/.test(period.key)) {
    const mPrefix = period.key;
    return getAllChats().filter((c) => {
      const t = c.time ? c.time.slice(0, 7) : "";
      const d = c.date ? c.date.slice(0, 7) : "";
      return t === mPrefix || d === mPrefix;
    });
  }
  // 2. 분기 모드: 해당 분기 3개 월 달력 일자 기준
  if (period.key && /^\\d{4}-Q[1-4]$/.test(period.key)) {
    const y = period.key.slice(0, 4);
    const q = parseInt(period.key.slice(6), 10);
    const startM = (q - 1) * 3 + 1;
    const months = [startM, startM + 1, startM + 2].map((m) => `${y}-${String(m).padStart(2, "0")}`);
    return getAllChats().filter((c) => {
      const t = c.time ? c.time.slice(0, 7) : "";
      const d = c.date ? c.date.slice(0, 7) : "";
      return months.some((m) => t === m || d === m);
    });
  }
  // 3. 연간 모드: 해당 연도 전체 달력 일자 기준
  if (period.key && /^\\d{4}$/.test(period.key)) {
    const yPrefix = period.key;
    return getAllChats().filter((c) => {
      const t = c.time ? c.time.slice(0, 4) : "";
      const d = c.date ? c.date.slice(0, 4) : "";
      return t === yPrefix || d === yPrefix;
    });
  }
  // 4. 주간 모드: 운영 주차 기준
  if (period.weekKeys && period.weekKeys.length) {
    return period.weekKeys.flatMap(chatsForWeekKey);
  }
  return chatsForWeekKey(period.key);
}"""

m = re.search(old_engine_rawchats_pat, engine_text)
if m:
    engine_text = engine_text[:m.start()] + new_engine_rawchats + engine_text[m.end():]
    with open('dashboard/engine.js', 'w', encoding='utf-8') as f:
        f.write(engine_text)
    print("1. Successfully updated engine.js rawChats to include inflow time!")
else:
    print("1. Warning: Could not match rawChats pattern in engine.js")


# ==========================================
# 2. Update scripts/generate_report_excel.py
# ==========================================
with open('scripts/generate_report_excel.py', 'r', encoding='utf-8') as f:
    rep_text = f.read()

# A. Update get_chats_for_p and is_item_in_p
pat_get_chats = r'    def get_chats_for_p\(p\):[\s\S]*?return \[\]'
new_get_chats = """    def get_chats_for_p(p):
        if not p: return []
        pk = str(p.get("key", ""))
        if is_week:
            return voc_data.get("CHATS_BY_WEEK", {}).get(pk, [])
        if "-" in pk and len(pk) == 7 and "W" not in pk and "-Q" not in pk:
            return [c for c in all_chats_flat if (c.get("time") and str(c.get("time"))[:7] == pk) or (c.get("date") and str(c.get("date"))[:7] == pk)]
        if "-Q" in pk:
            y, q = pk.split("-Q")
            qm = [f"{y}-{str((int(q)-1)*3 + i).zfill(2)}" for i in [1, 2, 3]]
            return [c for c in all_chats_flat if any((c.get("time") and str(c.get("time"))[:7] == m) or (c.get("date") and str(c.get("date"))[:7] == m) for m in qm)]
        if len(pk) == 4 and pk.isdigit():
            return [c for c in all_chats_flat if (c.get("time") and str(c.get("time"))[:4] == pk) or (c.get("date") and str(c.get("date"))[:4] == pk)]
        return []"""

m1 = re.search(pat_get_chats, rep_text)
if m1:
    rep_text = rep_text[:m1.start()] + new_get_chats + rep_text[m1.end():]
    print("2-A. Successfully updated get_chats_for_p")

pat_is_item = r'    def is_item_in_p\(item, p\):[\s\S]*?return False'
new_is_item = """    def is_item_in_p(item, p):
        if not item or not p: return False
        pk = str(p.get("key", ""))
        if is_week:
            return item.get("weekKey") == pk or item.get("week") == pk
        t_str = str(item.get("time") or item.get("managedAt") or "")[:7]
        d_str = str(item.get("date") or item.get("claimDate") or "")[:7]
        if "-" in pk and len(pk) == 7 and "W" not in pk and "-Q" not in pk:
            return (t_str == pk) or (d_str == pk)
        if "-Q" in pk:
            y, q = pk.split("-Q")
            qm = [f"{y}-{str((int(q)-1)*3 + i).zfill(2)}" for i in [1, 2, 3]]
            return any((t_str == m) or (d_str == m) for m in qm)
        if len(pk) == 4 and pk.isdigit():
            y_t = t_str[:4]
            y_d = d_str[:4]
            return (y_t == pk) or (y_d == pk)
        return False"""

m2 = re.search(pat_is_item, rep_text)
if m2:
    rep_text = rep_text[:m2.start()] + new_is_item + rep_text[m2.end():]
    print("2-B. Successfully updated is_item_in_p")


# B. In load_clean_quality_raw, compute report_m_str and add time/reportMonth
old_raw_append_pat = r'raw_records\.append\(\{\s*"year": str\(w_obj\.get\("year"\) or c\.get\("year"\) or "2026"\),[\s\S]*?"weekKey": wk_key\s*\}\)'

new_raw_append = """# Compute report month based on actual inflow time
            inflow_time = str(c.get("time") or c.get("managedAt") or "")
            if len(inflow_time) >= 7 and inflow_time[4] == "-":
                report_m_str = f"{int(inflow_time[5:7])}월"
            elif date_str and len(date_str) >= 7 and date_str[4] == "-":
                report_m_str = f"{int(date_str[5:7])}월"
            else:
                report_m_str = m_str

            raw_records.append({
                "year": str(w_obj.get("year") or c.get("year") or "2026"),
                "quarter": q_str,
                "reportMonth": report_m_str,
                "month": m_str,
                "week": w_str,
                "mw": mw,
                "id": cid,
                "cust": cust_val,
                "time": inflow_time,
                "date": date_str,
                "mgr": clean_mgr,
                "tagA": c.get("brand") or "",
                "tagB": c.get("mid") or "",
                "tagC": c.get("sub") or "",
                "prod": c.get("prod") or "기타",
                "mfg": c.get("mfgDate") or c.get("mfg") or "",
                "issue": c.get("issue") or "",
                "journey": c.get("journey") or "제품사용",
                "qualitySend": c.get("qSend") or "X",
                "isComp": is_comp,
                "exReason": ex_reason,
                "compMonth": "O" if is_comp else "",
                "compAll": "O" if is_comp else "",
                "mall": c.get("mall") or "",
                "orderNo": c.get("orderId") or "",
                "shipmentType": c.get("shipType") or "",
                "invoice": c.get("invoice") or "",
                "weekKey": wk_key
            })"""

m3 = re.search(old_raw_append_pat, rep_text)
if m3:
    rep_text = rep_text[:m3.start()] + new_raw_append + rep_text[m3.end():]
    print("2-C. Successfully updated load_clean_quality_raw record dict")


# C. In Sheet 3 (품질raw), update q_col_names, row_vals, widths, alignment, filter ref
old_q_cols_block = r'q_col_names = \[[\s\S]*?ws_qraw\.append\(q_col_names\)'
new_q_cols_block = """q_col_names = [
        "연도", "분기", "월보고용 월", "주차월(MONTH)", "WEEK", "M&W", "id", "고객명",
        "인입일시", "접수일자(DATE)", "담당자", "대분류", "중분류", "소분류",
        "제품명", "제조일자", "문의내용", "품질발송여부", "보상내역서(월)", "보상내역서_전체",
        "유통채널", "주문번호", "출고처", "송장번호"
    ]
    ws_qraw.append(q_col_names)"""

m4 = re.search(old_q_cols_block, rep_text)
if m4:
    rep_text = rep_text[:m4.start()] + new_q_cols_block + rep_text[m4.end():]
    print("2-D. Successfully updated q_col_names")

# Update row_vals in ws_qraw loop
old_row_vals_pat = r'row_vals = \[[\s\S]*?r\.get\("invoice", ""\)\s*\]'
new_row_vals = """row_vals = [
            r.get("year", ""), r.get("quarter", ""), r.get("reportMonth", ""), r.get("month", ""),
            r.get("week", ""), r.get("mw", ""), r.get("id", ""), r.get("cust", ""),
            r.get("time", ""), r.get("date", ""), r.get("mgr", ""), r.get("tagA", ""),
            r.get("tagB", ""), r.get("tagC", ""), r.get("prod", ""), r.get("mfg", ""),
            r.get("issue", ""), r.get("qualitySend", ""), r.get("compMonth", ""), r.get("compAll", ""),
            r.get("mall", ""), r.get("orderNo", ""), r.get("shipmentType", ""), r.get("invoice", "")
        ]"""

m5 = re.search(old_row_vals_pat, rep_text)
if m5:
    rep_text = rep_text[:m5.start()] + new_row_vals + rep_text[m5.end():]
    print("2-E. Successfully updated row_vals in ws_qraw")

# Update auto_filter ref and widths and is_left
old_filter_ref = r'ws_qraw\.auto_filter\.ref = f"A1:V\{len\(sorted_raw\) \+ 1\}"'
new_filter_ref = 'ws_qraw.auto_filter.ref = f"A1:X{len(sorted_raw) + 1}"'
rep_text = re.sub(old_filter_ref, new_filter_ref, rep_text)

old_is_left = r'is_left = ci in \(13, 15\)'
new_is_left = 'is_left = ci in (15, 17)'
rep_text = re.sub(old_is_left, new_is_left, rep_text)

old_widths = r'q_widths = \[8, 9, 9, 8, 12, 18, 12, 14, 11, 13, 13, 15, 34, 15, 48, 12, 14, 14, 14, 16, 12, 16\]'
new_widths = 'q_widths = [8, 9, 12, 12, 8, 12, 18, 12, 20, 14, 11, 13, 13, 15, 34, 15, 48, 12, 14, 14, 14, 16, 12, 16]'
rep_text = re.sub(old_widths, new_widths, rep_text)

with open('scripts/generate_report_excel.py', 'w', encoding='utf-8') as f:
    f.write(rep_text)
print("2-F. Successfully saved all changes to generate_report_excel.py!")
