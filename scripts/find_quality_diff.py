import json

with open(r'D:\dev\VOC리포트\dashboard\data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

# The user pasted 16 rows under "# 리포트 추출 raw"
# Let's inspect what is in d['CHATS_BY_WEEK'] or d['RAW_SUMMARY_BY_WEEK'] or wherever the 16 rows came from!
print("Keys in data.json:", list(d.keys()))

# Check quality_raw in data.json
qraw = d.get('QUALITY_RAW', [])
print(f"Total QUALITY_RAW rows in data.json: {len(qraw)}")

# Filter for 10월 3주 or 2026-10-15 ~ 2026-10-21
w42_q = [r for r in qraw if r.get('week') == '2026-W42' or r.get('mw') == '10월 3주' or ('2026-10-15' <= str(r.get('rawDate',''))[:10] <= '2026-10-21')]
print(f"QUALITY_RAW for 10월 3주: {len(w42_q)} rows")
for r in w42_q:
    print(r.get('id'), r.get('customerName'), r.get('date'), r.get('tagA'), r.get('tagB'), r.get('tagC'), r.get('productName'))
