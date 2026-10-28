import sys
import pyxlsb
import json

sys.stdout.reconfigure(encoding='utf-8')
path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\voc 파일\CX팀_26년_10월2주차_VOC현황.xlsb"

board_by_mw = {}
call_by_mw = {}
chat_by_mw = {}
chat_agent_by_mw = {}
chat_ai_by_mw = {}

print("▶ 엑셀 3대 공식 시트(게시판, 전화, 채팅) 추출 시작...")
with pyxlsb.open_workbook(path) as wb:
    # 1. 게시판
    with wb.get_sheet('게시판') as s:
        for r_idx, row in enumerate(s.rows()):
            if r_idx >= 3:
                vals = [c.v for c in row]
                if len(vals) > 7 and vals[1] == 2026.0:
                    mw = str(vals[4]).strip()
                    if vals[7]:
                        board_by_mw[mw] = board_by_mw.get(mw, 0) + int(vals[7])

    # 2. 전화
    with wb.get_sheet('전화') as s:
        for r_idx, row in enumerate(s.rows()):
            if r_idx >= 3:
                vals = [c.v for c in row]
                if len(vals) > 13 and vals[1] == 2026.0:
                    mw = str(vals[4]).strip()
                    if vals[13]:
                        call_by_mw[mw] = call_by_mw.get(mw, 0) + int(vals[13])

    # 3. 채팅
    with wb.get_sheet('채팅') as s:
        for r_idx, row in enumerate(s.rows()):
            if r_idx >= 4:
                vals = [c.v for c in row]
                if len(vals) > 15 and vals[2] == 2026.0:
                    mw = str(vals[5]).strip()
                    if vals[13]:
                        chat_by_mw[mw] = chat_by_mw.get(mw, 0) + int(vals[13])
                    if vals[14]:
                        chat_agent_by_mw[mw] = chat_agent_by_mw.get(mw, 0) + int(vals[14])
                    if vals[15]:
                        chat_ai_by_mw[mw] = chat_ai_by_mw.get(mw, 0) + int(vals[15])

# Print table
all_mws = []
for mw in list(call_by_mw.keys()) + list(chat_by_mw.keys()) + list(board_by_mw.keys()):
    if mw not in all_mws and mw != 'WEEK':
        all_mws.append(mw)

result = {}
for mw in all_mws:
    b = board_by_mw.get(mw, 0)
    c = chat_by_mw.get(mw, 0)
    p = call_by_mw.get(mw, 0)
    tot = b + c + p
    result[mw] = {
        '게시판': b,
        '채팅': c,
        '콜': p,
        '전체': tot,
        '채팅_담당자': chat_agent_by_mw.get(mw, 0),
        '채팅_AI': chat_ai_by_mw.get(mw, 0)
    }

print(f"✓ 총 {len(result)}개 주차 공식 집계 완료:")
for mw in sorted(result.keys()):
    d = result[mw]
    print(f"  [{mw}] 전체: {d['전체']:>4} | 게시판: {d['게시판']:>3} | 채팅: {d['채팅']:>3} (담당자: {d['채팅_담당자']:>3}, AI: {d['채팅_AI']:>3}) | 콜: {d['콜']:>3}")

out_path = r"D:\dev\VOC리포트\scripts\official_weekly_channel_counts.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"✓ JSON 저장 완료: {out_path}")
