# -*- coding: utf-8 -*-
"""
export_dashboard_data.py
SQLite DB (fact_voc, board_daily_counts, shipment_claims, tag_master) -> Web Dashboard (data.js, data.json)

베베숲 CX팀 주간 VOC 리포트 및 대시보드 실데이터 고속 추출기
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CANDIDATE_DBS = [
    "/data/db/channeltalk_voc.db",
    "/volume1/data/11. VOC, CCM 자료 등/1. VOC 불만접수현황/db/channeltalk_voc.db",
    "/volume1/DATA/11. VOC, CCM 자료 등/1. VOC 불만접수현황/db/channeltalk_voc.db",
    r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
]
DEFAULT_DB_PATH = next((p for p in CANDIDATE_DBS if os.path.exists(p)), CANDIDATE_DBS[-1])
FALLBACK_DB_PATH = r"C:\Users\hshwa\OneDrive\문서\VOC점검\channeltalk_voc_claim_test.db"
DEFAULT_OUT_DIR = Path(__file__).resolve().parent.parent / "dashboard"

RISK_HIGH = ["벌레", "이물질", "원단(공정)이물", "변색", "피부이상", "발진", "강성클레임", "성분불만", "파손"]
RISK_MED = ["보푸라기", "화학-약품냄새", "이취", "캡떨어짐", "용액"]
BRANDS = ["물티슈", "패밀리", "스킨케어", "헬로", "홈"]
# 1. 태그 분류 기준 재정의: 재통화를 무효 목록에서 제외 (실응대/공수 모수에 포함)
INVALID_SUBS = ["테스트", "오발신", "부재", "인입후끊김"]
REPEAT_SUBS = ["재통화"]

def mask_phone(phone_str):
    if not phone_str:
        return ""
    p = str(phone_str).strip()
    if p.startswith("+82"):
        p = "0" + p[3:]
    p_clean = re.sub(r"[^0-9]", "", p)
    if len(p_clean) == 11:
        return f"{p_clean[:3]}-****-{p_clean[7:]}"
    elif len(p_clean) == 10:
        return f"{p_clean[:3]}-***-{p_clean[6:]}"
    elif len(p_clean) >= 8:
        return f"{p_clean[:3]}-****-{p_clean[-4:]}"
    return p

def get_risk(full_tag, tag_c="", tag_b=""):
    text = f"{full_tag} {tag_c} {tag_b}"
    for h in RISK_HIGH:
        if h in text:
            return "HIGH"
    for m in RISK_MED:
        if m in text:
            return "MEDIUM"
    return "LOW"

def resolve_db_path(db_arg):
    local_cached = Path(r"C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db")
    if db_arg and os.path.exists(db_arg):
        target = Path(db_arg)
    elif os.path.exists(DEFAULT_DB_PATH):
        target = Path(DEFAULT_DB_PATH)
    elif local_cached.exists():
        print(f"[알림] 로컬 고속 캐시 DB를 사용합니다: {local_cached}")
        target = local_cached
    elif os.path.exists(FALLBACK_DB_PATH):
        print(f"[알림] 네트워크 DB를 찾을 수 없어 로컬 테스트 DB를 사용합니다: {FALLBACK_DB_PATH}")
        target = Path(FALLBACK_DB_PATH)
    else:
        raise SystemExit(f"[ERROR] DB 파일을 찾을 수 없습니다. (시도 경로: {DEFAULT_DB_PATH})")

    # 네트워크 드라이브(X:, Z: 등)인 경우 SQLite 랜덤 I/O 지연을 방지하기 위해 로컬 임시 파일로 고속 캐싱
    if str(target).upper().startswith(('X:', 'Z:', '\\\\')):
        local_cache = Path(tempfile.gettempdir()) / "channeltalk_voc_local.db"
        try:
            target_mtime = target.stat().st_mtime
            if not local_cache.exists() or local_cache.stat().st_mtime < target_mtime:
                print(f"[고속 캐싱] 네트워크 DB를 로컬 SSD 임시 경로로 동기화 중... ({target.stat().st_size / 1024 / 1024:.1f} MB)")
                shutil.copyfile(target, local_cache)
                print(f"✓ 로컬 임시 DB 동기화 완료: {local_cache}")
            return local_cache
        except Exception as e:
            print(f"[경고] 로컬 캐싱 실패 ({e}), 원본 경로를 사용합니다.")
    return target

def extract_dashboard_data(db_path, out_dir):
    print(f"==================================================")
    print(f"VOC 대시보드 실데이터 추출 시작")
    print(f"DB: {db_path}")
    print(f"출력 경로: {out_dir}")
    print(f"==================================================")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. 태그 마스터 추출
    cur.execute("SELECT channelId, full_tag, journey, tag_a, tag_b, tag_c FROM tag_master")
    tag_rows = cur.fetchall()

    tag_master = []
    parsed_tags = []
    risk_map = {}

    for r in tag_rows:
        t_id = str(r["channelId"])
        full = r["full_tag"] or ""
        journey = r["journey"] or ""
        tag_a = r["tag_a"] or ""
        tag_b = r["tag_b"] or ""
        tag_c = r["tag_c"] or ""

        if tag_a == "단순":
            nature = "문의"
        elif tag_a == "콜":
            nature = "운영"
        else:
            nature = "클레임"

        brand = tag_a if tag_a in BRANDS else ("공통" if tag_a == "클레임(공통)" else None)
        risk = get_risk(full, tag_c, tag_b) if nature == "클레임" else None
        if risk:
            risk_map[full] = risk

        valid = tag_c not in INVALID_SUBS

        tag_master.append([t_id, full, journey, tag_a, tag_b, tag_c, 1])
        parsed_tags.append({
            "id": t_id, "full": full, "journey": journey, "big": tag_a,
            "mid": tag_b, "sub": tag_c, "nature": nature, "brand": brand,
            "risk": risk, "valid": valid, "weight": 1
        })

    print(f"✓ 태그 마스터 {len(parsed_tags)}건 로드 완료")

    # 2. 주차 (WEEKS) 목록 추출 (2025 ~ 2026)
    cur.execute("""
        SELECT DISTINCT
            year, month, week, week_num, week_of_month,
            week_start_date, week_end_date
        FROM fact_voc
        WHERE year IN (2025, 2026) AND week_start_date IS NOT NULL AND week_start_date != ''
        ORDER BY week_start_date ASC
    """)
    week_rows = cur.fetchall()

    weeks = []
    for r in week_rows:
        s_date = r["week_start_date"]
        e_date = r["week_end_date"]
        w_key = f"{r['year']}-{r['week']}"
        w_month_str = r["week_of_month"] or ""

        try:
            s_dt = datetime.strptime(s_date, "%Y-%m-%d")
            e_dt = datetime.strptime(e_date, "%Y-%m-%d")
            label = f"{r['year']}년 {s_dt.month}/{s_dt.day}(목)~{e_dt.month}/{e_dt.day}(수)"
        except Exception:
            label = f"{r['year']}년 {s_date}~{e_date}"

        weeks.append({
            "key": w_key,
            "week_num": r["week_num"],
            "week_of_month": w_month_str,
            "label": label,
            "week_start_date": s_date,
            "week_end_date": e_date,
            "year": r["year"],
            "month": r["month"],
            "quarter": f"{(s_dt.month - 1) // 3 + 1}분기"
        })

    print(f"✓ 운영주차 {len(weeks)}개 주차 정의 완료 (2025 ~ 2026 전체)")

    # 월간 메타 구성 (MONTHS)
    months_map = {}
    for w in weeks:
        m_key = w["month"]
        if m_key not in months_map:
            y, m = m_key.split("-")
            months_map[m_key] = {
                "key": m_key,
                "label": f"{y}년 {int(m)}월",
                "weekKeys": []
            }
        months_map[m_key]["weekKeys"].append(w["key"])

    months = list(months_map.values())
    print(f"✓ 월간 메타 {len(months)}개 월 구성 완료")

    # 분기별 메타 구성 (QUARTERS)
    quarters_map = {}
    for w in weeks:
        y, m = w["month"].split("-")
        q_num = (int(m) - 1) // 3 + 1
        q_key = f"{y}-Q{q_num}"
        if q_key not in quarters_map:
            quarters_map[q_key] = {
                "key": q_key,
                "label": f"{y}년 {q_num}분기",
                "weekKeys": []
            }
        quarters_map[q_key]["weekKeys"].append(w["key"])

    quarters = list(quarters_map.values())
    print(f"✓ 분기별 메타 {len(quarters)}개 분기 구성 완료")

    # 연도별 메타 구성 (YEARS)
    years_map = {}
    for w in weeks:
        y_key = str(w["year"])
        if y_key not in years_map:
            years_map[y_key] = {
                "key": y_key,
                "label": f"{y_key}년 전체",
                "weekKeys": []
            }
        years_map[y_key]["weekKeys"].append(w["key"])

    years = list(years_map.values())
    print(f"✓ 연도별 메타 {len(years)}개 연도 구성 완료")

    # 3. 게시판(Board) 건수 주차별 집계 및 판매처(몰)별 건수 수집 ('전체합계' 중복합산 방지)
    cur.execute("""
        SELECT week_start_date, SUM(board_count) as total_board
        FROM board_daily_counts
        WHERE year IN (2025, 2026, '2025', '2026')
          AND mall_name NOT IN ('전체합계', '합계')
          AND mall_name NOT LIKE '%합계%'
        GROUP BY week_start_date
    """)
    board_by_week = {}
    for r in cur.fetchall():
        s_date = r["week_start_date"]
        matching_w = next((w for w in weeks if w["week_start_date"] == s_date), None)
        if matching_w:
            board_by_week[matching_w["key"]] = int(r["total_board"] or 0)

    cur.execute("""
        SELECT week_start_date, mall_name, SUM(board_count) as mall_total
        FROM board_daily_counts
        WHERE year IN (2025, 2026, '2025', '2026')
          AND mall_name IS NOT NULL AND mall_name != ''
          AND mall_name NOT IN ('전체합계', '합계')
          AND mall_name NOT LIKE '%합계%'
        GROUP BY week_start_date, mall_name
        HAVING mall_total > 0
        ORDER BY mall_total DESC
    """)
    board_malls_by_week = {w["key"]: {} for w in weeks}
    for r in cur.fetchall():
        s_date = r["week_start_date"]
        matching_w = next((w for w in weeks if w["week_start_date"] == s_date), None)
        if matching_w:
            m_name = (r["mall_name"] or "").strip()
            if m_name:
                board_malls_by_week[matching_w["key"]][m_name] = int(r["mall_total"] or 0)

    print(f"✓ 게시판 수기접수 주차별/판매처별 집계 완료 ({len(board_by_week)}개 주차)")

    # 3-2. 게시판(Board) 달력 기준 월간 / 분기 / 연간 집계 (1일~말일 달력 기준 100% 일치)
    cur.execute("""
        SELECT substr(date, 1, 7) as m_key, SUM(board_count) as total
        FROM board_daily_counts
        WHERE mall_name NOT IN ('전체합계', '합계') AND mall_name NOT LIKE '%합계%' AND date >= '2025-01-01'
        GROUP BY substr(date, 1, 7)
    """)
    board_by_month = {r["m_key"]: int(r["total"]) for r in cur.fetchall()}

    board_by_quarter = {}
    for m_key, total in board_by_month.items():
        if "-" in m_key:
            y, m = m_key.split("-")
            q_key = f"{y}-Q{(int(m) - 1) // 3 + 1}"
            board_by_quarter[q_key] = board_by_quarter.get(q_key, 0) + total

    board_by_year = {}
    for m_key, total in board_by_month.items():
        if "-" in m_key:
            y, _ = m_key.split("-")
            board_by_year[y] = board_by_year.get(y, 0) + total

    cur.execute("""
        SELECT substr(date, 1, 7) as m_key, mall_name, SUM(board_count) as total
        FROM board_daily_counts
        WHERE mall_name NOT IN ('전체합계', '합계') AND mall_name NOT LIKE '%합계%'
          AND mall_name IS NOT NULL AND mall_name != '' AND date >= '2025-01-01'
        GROUP BY substr(date, 1, 7), mall_name
        HAVING total > 0
        ORDER BY total DESC
    """)
    board_malls_by_month = {}
    for r in cur.fetchall():
        m_key = r["m_key"]
        m_name = (r["mall_name"] or "").strip()
        if m_key not in board_malls_by_month:
            board_malls_by_month[m_key] = {}
        board_malls_by_month[m_key][m_name] = int(r["total"])

    board_malls_by_quarter = {}
    for m_key, malls in board_malls_by_month.items():
        if "-" in m_key:
            y, m = m_key.split("-")
            q_key = f"{y}-Q{(int(m) - 1) // 3 + 1}"
            if q_key not in board_malls_by_quarter:
                board_malls_by_quarter[q_key] = {}
            for m_name, cnt in malls.items():
                board_malls_by_quarter[q_key][m_name] = board_malls_by_quarter[q_key].get(m_name, 0) + cnt

    board_malls_by_year = {}
    for m_key, malls in board_malls_by_month.items():
        if "-" in m_key:
            y, _ = m_key.split("-")
            if y not in board_malls_by_year:
                board_malls_by_year[y] = {}
            for m_name, cnt in malls.items():
                board_malls_by_year[y][m_name] = board_malls_by_year[y].get(m_name, 0) + cnt

    print(f"✓ 게시판 달력 기준 월간/분기/연간 집계 완료 (10월: {board_by_month.get('2026-10', 0):,}건)")

    # 4. 배송 클레임(Shipment Claims - 초저온/풀필먼트) 주차별 수집
    cur.execute("""
        SELECT
            claim_key, week_start_date, vendor_type, claim_type, customer_name,
            product_name, claim_text, action_text, order_no, original_invoice_no, damaged_qty,
            claim_date, order_date, inbound_date
        FROM shipment_claims
        WHERE claim_year IN (2025, 2026, '2025', '2026') AND claim_type IS NOT NULL AND claim_type != '확인요청'
    """)
    shipment_rows = cur.fetchall()

    shipment_by_week = {w["key"]: [] for w in weeks}
    shipments_by_week = {w["key"]: [] for w in weeks}

    for r in shipment_rows:
        s_date = r["week_start_date"]
        matching_w = next((w for w in weeks if w["week_start_date"] == s_date), None)
        if not matching_w:
            continue
        w_key = matching_w["key"]
        v_type = "초저온" if r["vendor_type"] == "coldchain" else "풀필먼트"
        c_type = r["claim_type"] or "기타"
        c_clean = c_type.replace(" ", "")
        if c_clean in ["저단가반송", "저단가", "운임비불만", "운임비", "운임불만"]:
            c_type = "운임비 불만"
        risk = "HIGH" if any(h in c_type for h in ["벌레", "이물질", "파손"]) else "LOW"

        raw_prod = (r["product_name"] or "").strip()
        clean_prod = re.sub(r"[\(\*\)]", " ", raw_prod).strip()
        if len(clean_prod) > 28:
            clean_prod = clean_prod[:28] + "..."

        ship_cust = (r["customer_name"] or "").strip()[:10] or "고객"
        c_date = (r["claim_date"] or "").strip()
        o_date = (r["order_date"] or "").strip()
        inb_date = (r["inbound_date"] or "").strip()
        # 인입/접수날짜: 접수일자(claim_date) 우선, 없으면 주문일자(order_date), 없으면 주차 시작일
        ship_date = c_date if (c_date and c_date != "입고") else (o_date or (inb_date if inb_date != "입고" else "") or s_date or "")

        shipment_chat = {
            "id": f"ship-{r['claim_key']}",
            "tag": f"클레임(공통)/배송/{c_type}",
            "journey": "배송/수령",
            "nature": "클레임",
            "brand": f"배송({v_type})",
            "mid": "배송",
            "sub": c_type,
            "risk": risk,
            "valid": True,
            "channel": "배송접수",
            "direction": None,
            "dow": 2,
            "hour": 14,
            "waiting": 0,
            "resolution": 0,
            "alfInflow": False,
            "alfResolved": False,
            "alfTransferred": False,
            "csat": None,
            "prod": clean_prod if clean_prod else "배송 전반",
            "mfg": "",
            "mall": v_type,
            "issue": (r["claim_text"] or "").strip()[:120],
            "act": (r["action_text"] or "").strip()[:80] or "교환/보상 처리",
            "cust": ship_cust,
            "custName": ship_cust,
            "name": ship_cust,
            "date": ship_date,
            "time": f"{ship_date} 14:00:00" if ship_date else "",
            "claimDate": c_date,
            "orderDate": o_date
        }
        shipment_by_week[w_key].append(shipment_chat)

        ship_item = {
            "id": str(r["claim_key"]),
            "week": w_key,
            "vendor": v_type,
            "type": c_type,
            "risk": risk,
            "date": ship_date,
            "claimDate": c_date,
            "orderDate": o_date,
            "cust": (r["customer_name"] or "").strip()[:10],
            "prod": raw_prod if raw_prod else (clean_prod if clean_prod else "배송 전반"),
            "raw_prod": raw_prod if raw_prod else (clean_prod if clean_prod else "배송 전반"),
            "clean_prod": clean_prod if clean_prod else "배송 전반",
            "orderNo": (r["order_no"] or "").strip(),
            "invoice": (r["original_invoice_no"] or "").strip(),
            "text": (r["claim_text"] or "").strip()[:150],
            "action": (r["action_text"] or "").strip()[:100] or "교환/보상 처리",
            "qty": r["damaged_qty"]
        }
        shipments_by_week[w_key].append(ship_item)

    print(f"✓ 배송 클레임 {sum(len(v) for v in shipment_by_week.values())}건 수집 완료")

    # 5. 채널톡 상담(fact_voc) 주차별 추출 및 정제 (tag_master 공식 매핑 결합)
    cur.execute("""
        SELECT
            f.id, f.date, f.week_start_date, f.full_tag,
            COALESCE(tm.journey, f.journey) as journey,
            COALESCE(tm.tag_a, f.tag_a) as tag_a,
            COALESCE(tm.tag_b, f.tag_b) as tag_b,
            COALESCE(tm.tag_c, f.tag_c) as tag_c,
            f.channel_type, f.medium_type, f.direction,
            f.is_ai_handled, f.alf_triggered, f.is_ai_inflow, f.is_ai_completed, f.is_ai_transferred,
            f.product_name, f.customer_issue, f.cs_action, f.profile_csat,
            f.mall_name, f.manufacture_date,
            f.special_note, f.quality_send_yn, f.handle_type, f.ai_status,
            f.managedAt, f.manager_name,
            f.customer_name, f.name,
            f.order_no, f.shipment_type, f.invoice_no
        FROM fact_voc f
        LEFT JOIN tag_master tm ON f.full_tag = tm.full_tag
        WHERE f.year IN (2025, 2026)
          AND (f.customer_name NOT LIKE '%홍길동%' AND (f.description IS NULL OR f.description NOT LIKE '%테스트건%'))
        ORDER BY f.managedAt ASC
    """)
    chat_rows = cur.fetchall()

    chats_by_week = {w["key"]: [] for w in weeks}
    issues_by_week = {w["key"]: [] for w in weeks}

    # 48시간 이내 재인입(FCR 품질) 추적용 이력 맵
    cust_contact_history = {}
    EXCLUDE_GENERIC_CUST = {"소비자", "고객", "미입력", "알수없음", "UNKNOWN", "NS홈쇼핑", "CJ온스타일", "GSSHOP", "11번가", "카카오", "네이버", "쿠팡"}

    for r in chat_rows:
        s_date = r["week_start_date"]
        matching_w = next((w for w in weeks if w["week_start_date"] == s_date), None)
        if not matching_w:
            continue
        w_key = matching_w["key"]

        full_tag = r["full_tag"] or ""
        if str(full_tag).strip().lower() in ["nan", "none", "null", ""]:
            full_tag = "단순문의/기타/단순종결"
        tag_a = r["tag_a"] or ""
        tag_b = r["tag_b"] or ""
        tag_c = r["tag_c"] or ""
        journey = r["journey"] or ""
        if str(journey).strip().lower() in ["nan", "none", "null", ""]:
            journey = "기타"

        # 채널 분류: 전화, 챗봇(ALF), 상담사챗
        ch_type = r["channel_type"] or ""
        med_type = r["medium_type"] or ""

        cust_issue = (r["customer_issue"] or "").strip()
        if cust_issue.lower() in ["nan", "none", "null"]:
            cust_issue = ""
        raw_prod = (r["product_name"] or "").strip()
        if raw_prod.lower() in ["nan", "none", "null"]:
            raw_prod = ""
        cs_act = (r["cs_action"] or "").strip()
        if cs_act.lower() in ["nan", "none", "null"]:
            cs_act = ""

        # 전화 여부 엄격 판별 (유선전화는 AI 상담 모수에서 100% 원천 배제)
        is_phone = (
            ch_type in ["콜", "전화"]
            or med_type in ["phone", "phoneNumber"]
            or full_tag.startswith("콜/")
        )
        raw_dir = (r["direction"] or "").strip().upper()

        if is_phone:
            channel = "전화"
            direction = raw_dir if raw_dir in ["INBOUND", "OUTBOUND"] else "INBOUND"
            alf_inflow = False
            alf_resolved = False
            alf_transferred = False
        else:
            # 순수 온라인 채팅 채널
            # 1) ALF 인입: 명시적 AI 인입 플래그 또는 트리거 기록이 있는 경우
            alf_inflow = bool(r["is_ai_inflow"] or str(r["alf_triggered"]).lower() == "true")

            # 2) ALF 완결: 공식 플래그 또는 cs_action / issue에 ALF가 기록된 경우
            has_alf_action = "ALF" in cs_act.upper() or "ALF" in cust_issue.upper()
            alf_resolved = bool(r["is_ai_completed"] or r["is_ai_handled"] or has_alf_action)
            alf_transferred = bool(r["is_ai_transferred"] and not alf_resolved)

            # 채팅 채널은 단일 '채팅'으로 일원화 (챗봇 ALF는 채팅 내 속성으로 관리)
            channel = "채팅"
            direction = raw_dir if raw_dir in ["INBOUND", "OUTBOUND"] else "INBOUND"

        # 클레임 / 단순 공식 분류 기준 (고객 여정 journey 기준 - 사용자 명시 지침)
        # 1) 서비스 클레임: 고객 여정(journey)이 '사후관리/클레임'인 건
        is_service_claim = (journey == "사후관리/클레임")

        # 2) 순수 품질 클레임: 고객 여정(journey)이 '제품사용'인 건
        is_quality_claim = (journey == "제품사용")

        # 3) 배송 클레임: 고객 여정(journey)이 '배송/수령'이거나 tag_b == '배송'
        is_delivery_claim = (journey == "배송/수령" or tag_b == "배송")

        if is_service_claim:
            nature = "클레임"
            brand = "서비스"
        elif is_quality_claim:
            nature = "클레임"
            brand = tag_a if tag_a in BRANDS else "공통"
        elif tag_a in ("단순", "단순문의"):
            nature = "문의"
            brand = None
        elif is_delivery_claim:
            nature = "클레임"
            brand = tag_a if tag_a in BRANDS else ("공통" if "공통" in tag_a else None)
        elif tag_a == "콜":
            nature = "운영"
            brand = None
        else:
            nature = "문의"
            brand = None

        risk = get_risk(full_tag, tag_c, tag_b) if nature == "클레임" else None

        # 48시간 이내 재인입(재통화) 판별
        managed_at = r["managedAt"] or ""
        raw_cust_id = (r["customer_name"] or r["name"] or "").strip()
        is_repeat_48h = False
        if managed_at and raw_cust_id and not any(ex in raw_cust_id for ex in EXCLUDE_GENERIC_CUST):
            try:
                m_dt = datetime.strptime(managed_at[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
                if raw_cust_id in cust_contact_history:
                    prev_dt = cust_contact_history[raw_cust_id][-1]
                    diff_h = (m_dt - prev_dt).total_seconds() / 3600.0
                    # 이전 상담 종료/인입 후 5분 이상 48시간 이내 동일 고객의 재인입
                    if 0.08 <= diff_h <= 48.0 and raw_dir != "OUTBOUND":
                        is_repeat_48h = True
                cust_contact_history.setdefault(raw_cust_id, []).append(m_dt)
            except Exception:
                pass

        # 문의 유효성 분류 (Contact Validity)
        # 태그가 '재통화'이거나 48시간 이내 동일 고객 재인입 건을 재통화/재인입 모수로 산출
        is_invalid = tag_c in INVALID_SUBS
        is_repeat = (tag_c in REPEAT_SUBS) or is_repeat_48h
        valid = not (channel == "전화" and is_invalid)  # 채팅은 220건 전수 유효 모수로 유지!
        unique_issue = (not is_repeat) and valid  # 단일 이슈 VOC 분석용 중복 제거 플래그

        managed_at = r["managedAt"] or ""
        hour = 14
        dow = 1
        is_in_hours = False

        if managed_at:
            try:
                m_dt = datetime.strptime(managed_at[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
                hour = m_dt.hour
                dow = (m_dt.weekday() - 3) % 7
                # 운영시간 분기 (1. 인바운드: 평일 10:00 ~ 17:00, 2. 아웃바운드: 10시 전 / 17시 이후 모두 정상 실적 인정)
                if raw_dir == "OUTBOUND":
                    is_in_hours = True
                else:
                    if m_dt.weekday() < 5 and 10 <= m_dt.hour < 17:
                        is_in_hours = True
                    else:
                        is_in_hours = False
            except Exception:
                is_in_hours = True
        else:
            is_in_hours = True

        # 고객명 마스킹 / 정제
        raw_cust = (r["customer_name"] or r["name"] or "").strip()
        cust_name = raw_cust if raw_cust else "고객"
        date_str = (r["date"] or (managed_at[:10] if managed_at else "") or "").strip()

        csat = None
        if r["profile_csat"]:
            try:
                csat = float(r["profile_csat"])
            except Exception:
                pass

        raw_prod = (r["product_name"] or "").strip()
        clean_prod = re.sub(r"[\(\*\)]", " ", raw_prod).strip()
        if len(clean_prod) > 28:
            clean_prod = clean_prod[:28] + "..."

        mgr_name = (r["manager_name"] or "").strip()
        if not mgr_name or mgr_name == "nan":
            if (
                r["is_ai_handled"] == 1
                or str(r["alf_triggered"]).lower() == "true"
                or r["is_ai_completed"] == 1
                or r["handle_type"] == "AI"
                or r["ai_status"] == "completed"
                or alf_resolved
                or alf_inflow
                or "ALF" in cs_act.upper()
                or "ALF" in cust_issue.upper()
            ):
                mgr_name = "ALF (AI 상담)"
            else:
                mgr_name = "미배정"

        chat_obj = {
            "id": str(r["id"]),
            "tag": full_tag,
            "journey": journey,
            "nature": nature,
            "brand": brand,
            "mid": tag_b,
            "sub": tag_c,
            "risk": risk,
            "valid": valid,
            "is_in_hours": is_in_hours,
            "is_invalid": is_invalid,
            "is_repeat": is_repeat,
            "is_repeat_48h": is_repeat_48h,
            "unique_issue": unique_issue,
            "channel": channel,
            "direction": direction,
            "dow": dow,
            "hour": hour,
            "waiting": 45,
            "resolution": 480,
            "alfInflow": alf_inflow,
            "alfResolved": alf_resolved,
            "alfTransferred": alf_transferred,
            "csat": csat,
            "prod": raw_prod if raw_prod else (brand or "기타"),
            "mfg": (r["manufacture_date"] or "").strip()[:30],
            "mall": (r["mall_name"] or "").strip() or "자사몰/기타",
            "issue": (r["customer_issue"] or "").strip()[:150],
            "act": (r["cs_action"] or "").strip()[:100],
            "agent": mgr_name,
            "note": (r["special_note"] or "").strip(),
            "qSend": (r["quality_send_yn"] or "").strip(),
            "cust": cust_name,
            "custName": cust_name,
            "name": cust_name,
            "date": date_str,
            "time": managed_at,
            "orderNo": (r["order_no"] or "").strip(),
            "shipmentType": (r["shipment_type"] or "").strip(),
            "invoice": (r["invoice_no"] or "").strip()
        }
        chats_by_week[w_key].append(chat_obj)

        # 주요 이슈 & 인사이트 수집 (실제 고객불만 텍스트)
        cust_issue = (r["customer_issue"] or "").strip()
        cs_act = (r["cs_action"] or "").strip()
        prod_name = (r["product_name"] or "").strip()

        if nature == "클레임" and cust_issue and len(cust_issue) >= 5:
            clean_prod = re.sub(r"[\(\*\)]", " ", prod_name).strip()[:24] or (brand or "제품 전반")
            issues_by_week[w_key].append({
                "id": f"{w_key}-issue-{r['id']}",
                "tag": full_tag,
                "brand": brand or "공통",
                "mid": tag_b,
                "risk": risk or "LOW",
                "product": clean_prod,
                "count": 1,
                "detail": cust_issue[:120] + ("..." if len(cust_issue) > 120 else ""),
                "action": cs_act[:80] + ("..." if len(cs_act) > 80 else "") if cs_act else "고객 안내 및 조치 종결"
            })

    # 배송 클레임도 주차별 chats 및 issues에 병합
    for w_key, s_chats in shipment_by_week.items():
        chats_by_week[w_key].extend(s_chats)
        for sc in s_chats:
            if sc.get("issue"):
                issues_by_week[w_key].append({
                    "id": sc["id"],
                    "tag": sc["tag"],
                    "brand": sc["brand"],
                    "mid": "배송",
                    "risk": sc["risk"],
                    "product": sc["prod"] or "배송 전반",
                    "count": 1,
                    "detail": sc["issue"][:120] + ("..." if len(sc["issue"]) > 120 else ""),
                    "action": sc["act"][:80]
                })

    # 주차별 이슈 정리: HIGH 리스크 우선 정렬 후 상위 8건 추출
    for w_key, issue_list in issues_by_week.items():
        issue_list.sort(key=lambda x: (x["risk"] == "HIGH", len(x["detail"])), reverse=True)
        issues_by_week[w_key] = issue_list[:10]

    total_chats = sum(len(v) for v in chats_by_week.values())
    print(f"✓ 채널톡/배송 상담 건수 총 {total_chats:,}건 추출 완료 (37개 주차 전체)")

    # 5-2. CTI 통화 상세 원장(standard_meet) 주차별 추출 및 정제
    print("▶ CTI 통화 상세 원장(standard_meet) 수집 시작...")
    cur.execute("""
        SELECT 
            s.meet_key, s.week_start_date, s.started_at, s.ended_at, s.engaged_at,
            s.direction, s.is_answered, s.is_missed, s.missed_reason, s.missed_category,
            s.from_number, s.to_number,
            COALESCE(m.name, '미배정') as agent_name,
            u.name as customer_name,
            u.journey, u.tag_a, u.tag_b, u.tag_c,
            u.description,
            d.customer_issue, d.cs_action
        FROM standard_meet s
        LEFT JOIN userchat u ON s.user_chat_id = u.id
        LEFT JOIN manager m ON COALESCE(NULLIF(s.assignee_id, ''), NULLIF(u.assigneeId, '')) = CAST(m.id AS TEXT)
        LEFT JOIN userchat_description d ON s.user_chat_id = d.id
        WHERE s.year IN (2025, 2026)
        ORDER BY s.started_at DESC
    """)
    cti_rows = cur.fetchall()
    cti_by_week = {w["key"]: [] for w in weeks}

    for r in cti_rows:
        s_date = r["week_start_date"]
        matching_w = next((w for w in weeks if w["week_start_date"] == s_date), None)
        if not matching_w:
            continue
        w_key = matching_w["key"]

        st = r["started_at"] or ""
        et = r["ended_at"] or ""
        eg = r["engaged_at"] or ""
        # 실제 통화 연결 여부 (engaged_at이 기록된 경우만 상담사 실통화 성공!)
        has_engaged = bool(eg and str(eg).strip() != "")
        ans = 1 if has_engaged else 0

        talk_sec = 0
        wait_sec = 0
        if ans == 1:
            if et and eg:
                try:
                    et_dt = datetime.strptime(et[:19], "%Y-%m-%d %H:%M:%S")
                    eg_dt = datetime.strptime(eg[:19], "%Y-%m-%d %H:%M:%S")
                    talk_sec = max(0, int((et_dt - eg_dt).total_seconds()))
                except Exception:
                    pass
            if eg and st:
                try:
                    st_dt = datetime.strptime(st[:19], "%Y-%m-%d %H:%M:%S")
                    eg_dt = datetime.strptime(eg[:19], "%Y-%m-%d %H:%M:%S")
                    wait_sec = max(0, int((eg_dt - st_dt).total_seconds()))
                except Exception:
                    pass
            elif et and st and not eg:
                try:
                    st_dt = datetime.strptime(st[:19], "%Y-%m-%d %H:%M:%S")
                    et_dt = datetime.strptime(et[:19], "%Y-%m-%d %H:%M:%S")
                    talk_sec = max(0, int((et_dt - st_dt).total_seconds()))
                except Exception:
                    pass
        else:
            if et and st:
                try:
                    st_dt = datetime.strptime(st[:19], "%Y-%m-%d %H:%M:%S")
                    et_dt = datetime.strptime(et[:19], "%Y-%m-%d %H:%M:%S")
                    wait_sec = max(0, int((et_dt - st_dt).total_seconds()))
                except Exception:
                    pass

        direction = r["direction"] or "inbound"
        phone = mask_phone(r["from_number"] if direction == "inbound" else r["to_number"])
        missed_reason = (r["missed_category"] or r["missed_reason"] or "").strip()
        tag_parts = [p for p in [r["tag_a"], r["tag_b"], r["tag_c"]] if p]
        tag_str = "/".join(tag_parts)

        is_cti_in_hours = False
        if st:
            try:
                st_dt = datetime.strptime(st[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
                # 인바운드 10:00 ~ 17:00, 아웃바운드는 10시 전 / 17시 이후 모두 정상 실적으로 인정
                if direction == "outbound":
                    is_cti_in_hours = True
                else:
                    if st_dt.weekday() < 5 and 10 <= st_dt.hour < 17:
                        is_cti_in_hours = True
                    else:
                        is_cti_in_hours = False
            except Exception:
                is_cti_in_hours = True
        else:
            is_cti_in_hours = True

        raw_issue = (r["customer_issue"] or "").strip()
        raw_act = (r["cs_action"] or "").strip()
        desc = r["description"] or ""

        if (not raw_issue or not raw_act) and desc:
            m_iss = re.search(r'[■□◇\*\-]?\s*(?:문의내용|문의|상담내용|인입내용|불만내용|고객문의)\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:안내|안내내용|조치|조치사항|고객주소|특이사항|품질발송)|$)', desc, re.DOTALL)
            m_act = re.search(r'[■□◇\*\-]?\s*(?:안내내용|안내|조치내용|조치사항|조치|처리내용|처리결과)\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:고객주소|특이사항|품질발송)|$)', desc, re.DOTALL)
            if not raw_issue and m_iss:
                raw_issue = re.sub(r'[\r\n]+', ' ', m_iss.group(1)).strip()
            if not raw_act and m_act:
                raw_act = re.sub(r'[\r\n]+', ' ', m_act.group(1)).strip()

            if not raw_issue and ('상품명' in desc or '입금자' in desc or '주문' in desc):
                m_prod = re.search(r'[■□◇\*\-]?\s*(?:상품명|제품명)\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:금액|입금자|주소)|$)', desc, re.DOTALL)
                prod = m_prod.group(1).strip() if m_prod else ''
                raw_issue = f'전화 주문 접수: {prod}' if prod else '전화 주문 접수 문의'
                if not raw_act:
                    raw_act = '주문 확인 및 가상계좌 입금 안내'

            if not raw_issue:
                lines = [l.strip() for l in desc.splitlines() if l.strip() and not l.startswith('■')]
                if lines:
                    raw_issue = lines[0]
                    if len(lines) > 1 and not raw_act:
                        raw_act = lines[1]

        cti_item = {
            "id": r["meet_key"],
            "time": st,
            "dir": direction,
            "ans": ans,
            "agent": r["agent_name"],
            "cust": (r["customer_name"] or "").strip() or "고객",
            "talk": talk_sec,
            "wait": wait_sec,
            "phone": phone,
            "reason": missed_reason,
            "tag": tag_str,
            "journey": r["journey"] or "",
            "issue": raw_issue[:100],
            "act": raw_act[:80],
            "is_in_hours": is_cti_in_hours
        }
        cti_by_week[w_key].append(cti_item)

    total_cti = sum(len(v) for v in cti_by_week.values())
    print(f"✓ CTI 통화 상세 원장 총 {total_cti:,}건 추출 완료 (36개 주차 전체)")

    # 5-3. 품질raw 원장(quality_raw) 추출 및 정제 (리포트 엑셀 추출 및 품질 분석용)
    print("▶ 품질raw 원장 데이터 추출 시작...")
    cur.execute("""
        SELECT 
            u.id,
            COALESCE(u.__schema_year, SUBSTR(u.report_date, 1, 4), '2026') as year,
            u.quarter,
            u.month,
            u.week,
            u.week_of_month,
            u.week_start_date,
            u.name as customer_name,
            u.report_date,
            u.managedAt,
            COALESCE(m.name, 'AI') as manager_name,
            u.tag_a,
            u.tag_b,
            u.tag_c,
            u.tags,
            u.journey,
            d.product_name,
            d.manufacture_date,
            d.customer_issue,
            d.cs_action,
            d.special_note,
            d.quality_send_yn,
            d.mall_name,
            d.order_no,
            d.shipment_type,
            d.invoice_no,
            u.__source_file
        FROM userchat u
        LEFT JOIN tag_master tm ON u.tags = tm.full_tag
        LEFT JOIN userchat_description d ON u.id = d.id
        LEFT JOIN manager m ON REPLACE(CAST(u.assigneeId AS TEXT), '.0', '') = CAST(m.id AS TEXT)
        WHERE (u.__schema_year = '2026' OR u.report_date >= '2026-01-01' OR u.__source_file LIKE '%26년%')
          AND COALESCE(tm.journey, u.journey) = '제품사용'
          AND COALESCE(u.tag_c, '') != '재통화'
          AND (u.name NOT LIKE '%홍길동%' AND (u.description IS NULL OR u.description NOT LIKE '%테스트건%'))
        ORDER BY u.report_date ASC, u.managedAt ASC, u.id ASC
    """)
    q_rows = cur.fetchall()

    quality_raw_rows = []
    for r in q_rows:
        rd = str(r['report_date'] or r['managedAt'] or r['week_start_date'] or '')[:10]
        # 날짜도 없고 제품명도 없는 비정상 더미 레코드는 제외
        if not rd and not r['product_name'] and not r['tag_a']:
            continue

        # [사용자 확정 4대 불변 공식 기준]
        dt_target = None
        raw_dt_str = str(r['report_date'] or r['managedAt'] or '')
        if raw_dt_str:
            try:
                dt_target = datetime.fromisoformat(raw_dt_str[:19].replace('T', ' '))
            except Exception:
                try:
                    dt_target = datetime.strptime(raw_dt_str[:10], "%Y-%m-%d")
                except Exception:
                    pass
        if not dt_target and rd:
            try:
                dt_target = datetime.strptime(rd[:10], "%Y-%m-%d")
            except Exception:
                pass

        # 1. 연도: 인입 연도
        # 2. 월간: 1일 ~ 말일 (캘린더 월)
        # 3. 분기: 1분기(1~3월), 2분기(4~6월), 3분기(7~9월), 4분기(10~12월)
        src_file = str(r['__source_file'] or '')
        file_year = '2026'
        if '25년' in src_file or '2025' in src_file:
            file_year = '2025'
        elif '26년' in src_file or '2026' in src_file:
            file_year = '2026'
        else:
            file_year = str(r['year'] or (rd[:4] if rd else '2026')).replace('년', '').strip()

        if dt_target:
            y = str(dt_target.year)
            m_val = dt_target.month
            m_str = f"{m_val}월"
            q_num = (m_val - 1) // 3 + 1
            q = f"{q_num}분기"
        else:
            y = file_year
            m_str = "10월"
            q = "4분기"

        # 4. 주간: 목 10:00 ~ 수 17:00 (수요일 17:00 마감 후 접수건은 익주 목요일 사이클로 이월)
        matching_w = None
        if dt_target:
            shifted_dt = dt_target + timedelta(hours=7)
            days_since_thu = (shifted_dt.weekday() - 3) % 7
            cycle_start_thu = (shifted_dt - timedelta(days=days_since_thu)).date()
            cycle_start_str = str(cycle_start_thu)
            matching_w = next((w for w in weeks if w.get("week_start_date") == cycle_start_str), None)

        if not matching_w and r['week_start_date']:
            matching_w = next((w for w in weeks if w["week_start_date"] == r["week_start_date"]), None)

        if not matching_w and rd:
            matching_w = next((w for w in weeks if (w.get("year") == file_year or file_year in w.get("key", "")) and w["week_start_date"] <= rd <= w["week_end_date"]), None)
            if not matching_w:
                matching_w = next((w for w in weeks if w["week_start_date"] <= rd <= w["week_end_date"]), None)

        if not matching_w or not rd:
            sf_match = re.search(r'(\d+)월\s*(\d+)주', src_file)
            if sf_match:
                target_label_sub = f"{sf_match.group(1)}월 {sf_match.group(2)}주"
                found_w = next((w for w in weeks if (w.get("year") == file_year or file_year in w.get("key", "")) and w.get("week_of_month") == target_label_sub), None)
                if not found_w:
                    found_w = next((w for w in weeks if w.get("week_of_month") == target_label_sub), None)
                if found_w:
                    matching_w = found_w
                    if not rd and found_w.get("week_start_date"):
                        rd = found_w["week_start_date"]

        if matching_w:
            w_key = matching_w["key"]
            wom = matching_w.get("week_of_month") or matching_w.get("label") or ""
            w_match = re.search(r'(\d+주)', wom)
            w_str = w_match.group(1) if w_match else f"{matching_w.get('week_num', 1)}주"
            mw = wom if wom else f"{m_str} {w_str}"
        else:
            w_key = str(r['week'] or '')
            wom_raw = str(r['week_of_month'] or '')
            w_match = re.search(r'(\d+)주', wom_raw)
            w_str = f"{w_match.group(1)}주" if w_match else "1주"
            mw = f"{m_str} {w_str}"

        # DATE (YYYY년 M월 D일)
        if rd and '-' in rd:
            parts = rd.split('-')
            date_str = f"{parts[0]}년 {int(parts[1])}월 {int(parts[2])}일" if len(parts) >= 3 else rd
        else:
            date_str = rd
            
        mgr = str(r['manager_name'] or 'AI').replace('CX_', '').replace('CX', '').strip() or 'AI'
        
        q_send = (r['quality_send_yn'] or '').strip().upper()
        if not q_send:
            sp = (r['special_note'] or '').strip().upper()
            if sp in ('O', 'X'): q_send = sp
            else: q_send = 'O' if r['tag_a'] == '물티슈' and r['tag_b'] not in ('시스템', '배송') else 'X'
            
        sp_note = (r['special_note'] or '').strip()
        comp_m = sp_note if sp_note and sp_note not in ('O', 'X') else ''
        comp_all = comp_m

        cur_tag_a = str(r["tag_a"] or "")
        cur_tag_b = str(r["tag_b"] or "")
        cur_tag_c = str(r["tag_c"] or "")
        cust_issue_text = str(r["customer_issue"] or "")
        raw_prod_text = str(r["product_name"] or "")

        # 유입 채널(전화/단순문의 등)에 의해 태그가 단순문의로 찍힌 품질 건 태그 복원
        if cur_tag_a in ("단순", "단순문의", "", "None") or cur_tag_b in ("Call-Chat", "", "전화"):
            if any(k in raw_prod_text for k in ["물티슈", "시그니처", "센시", "포레스트", "위드", "프라임", "에코"]) or "물티슈" in cust_issue_text:
                cur_tag_a = "물티슈"
            elif any(k in raw_prod_text for k in ["로션", "수딩", "크림", "바스", "샴푸", "스킨"]):
                cur_tag_a = "스킨케어"
            else:
                cur_tag_a = "물티슈"
            
            if any(k in cust_issue_text for k in ["수분", "물기", "건조"]):
                cur_tag_b, cur_tag_c = "용액", "수분부족"
            elif any(k in cust_issue_text for k in ["원사찌꺼기", "원사"]):
                cur_tag_b, cur_tag_c = "원단(공정)이물", "원사찌꺼기"
            elif any(k in cust_issue_text for k in ["원사뭉침", "뭉침"]):
                cur_tag_b, cur_tag_c = "원단면", "원사뭉침"
            elif any(k in cust_issue_text for k in ["보풀", "보푸라기"]):
                cur_tag_b, cur_tag_c = "원단면", "보푸라기(원단면)"
            elif any(k in cust_issue_text for k in ["이물", "벌레", "플라스틱"]):
                cur_tag_b, cur_tag_c = "원단(공정)이물", "기타이물"
            elif any(k in cust_issue_text for k in ["캡탈락", "캡떨어", "캡안붙", "캡 누락"]):
                cur_tag_b, cur_tag_c = "포장공정", "캡탈락"
            elif any(k in cust_issue_text for k in ["캡파손", "캡불량", "캡"]):
                cur_tag_b, cur_tag_c = "포장공정", "캡불량"
            elif any(k in cust_issue_text for k in ["누액", "터짐", "새어나", "물이새"]):
                cur_tag_b, cur_tag_c = "포장공정", "누액(터짐)"
            elif any(k in cust_issue_text for k in ["찢김", "찢어"]):
                cur_tag_b, cur_tag_c = "포장공정", "찢김"
            elif any(k in cust_issue_text for k in ["부정형", "절단"]):
                cur_tag_b, cur_tag_c = "원단면", "부정형절단"
            elif any(k in cust_issue_text for k in ["냄새", "악취", "약품"]):
                cur_tag_b, cur_tag_c = "이취", "화학-약품냄새"

        quality_raw_rows.append({
            "year": y,
            "quarter": q,
            "month": m_str,
            "week": w_str,
            "mw": mw,
            "id": str(r["id"]),
            "cust": str(r["customer_name"] or "고객"),
            "date": date_str,
            "mgr": mgr,
            "tagA": cur_tag_a,
            "tagB": cur_tag_b,
            "tagC": cur_tag_c,
            "prod": str(r["product_name"] or "").strip() or cur_tag_a,
            "mfg": str(r["manufacture_date"] or "").strip(),
            "issue": str(r["customer_issue"] or "").strip(),
            "act": str(r["cs_action"] or "").strip(),
            "note": str(r["special_note"] or "").strip(),
            "qualitySend": q_send,
            "compMonth": comp_m,
            "compAll": comp_all,
            "mall": str(r["mall_name"] or ""),
            "orderNo": str(r["order_no"] or ""),
            "shipmentType": str(r["shipment_type"] or ""),
            "invoice": str(r["invoice_no"] or ""),
            "weekKey": w_key,
            "rawDate": rd
        })

    print(f"✓ 품질raw 원장 총 {len(quality_raw_rows):,}건 추출 완료")

    conn.close()

    # 5-3. 3개 계층 데이터 세트 생성 (raw_summary, operational_kpis, issue_breakdown)
    print("▶ 3개 계층(원본요약 / CX운영KPI / 원인별VOC) 데이터 생성 시작...")
    raw_summary = {}
    operational_kpis = {}
    issue_breakdown = {}

    # 공식 엑셀 리포트(UserChat/전화/채팅/게시판 시트) 주간 채널 통계 데이터 로드
    official_counts_file = Path(__file__).resolve().parent / "official_weekly_channel_counts.json"
    official_counts = {}
    if official_counts_file.exists():
        try:
            with open(official_counts_file, "r", encoding="utf-8") as f:
                official_counts = json.load(f)
            print(f"✓ 공식 주간 채널 통계 데이터 {len(official_counts)}개 주차 로드 완료")
        except Exception as e:
            print(f"⚠️ 공식 주간 채널 통계 로드 실패: {e}")

    for w in weeks:
        w_key = w["key"]
        b_cnt = board_by_week.get(w_key, 0)
        w_chats = chats_by_week.get(w_key, [])
        w_cti = cti_by_week.get(w_key, [])

        # CTI 교환기 원장 기반 콜 수치
        # ※ 운영시간 외 ARS 자동안내(IVR 중도이탈, 운영시간 아님 등)는 상담원 응대 모수가 아니므로
        # 실질 인바운드 및 총 CTI 통화량에서 제외하여 8월 이전과 9월 이후의 통계 기준을 통일합니다.
        cti_target_reasons = {
            "응대 가능 상담원 없음", "상담원 수신 거절", "대기열 최대 대기시간 초과",
            "링 울리는 시간 초과", "최대 대기열 수 초과", "링 울리는 중 고객 종료",
            "음성 사서함", "고객이 먼저 끊었을 때"
        }
        if w_cti:
            # 제안 2번: 실제로 통화를 나눈 실통화 건수만 메인 카운트 (수신 실통화 + 발신 실통화)
            calls_in = sum(1 for c in w_cti if c.get("dir") in ("inbound", "missed") and c.get("ans") == 1)
            calls_out = sum(1 for c in w_cti if c.get("dir") == "outbound" and c.get("ans") == 1 and "부재" not in (c.get("tag") or "") and "부재" not in (c.get("reason") or ""))
            calls_total = calls_in + calls_out
            op_missed = sum(1 for c in w_cti if c.get("dir") in ("inbound", "missed") and c.get("ans") != 1 and c.get("is_in_hours"))
            off_missed = sum(1 for c in w_cti if c.get("dir") in ("inbound", "missed") and c.get("ans") != 1 and not c.get("is_in_hours"))
        else:
            calls_in = sum(1 for c in w_chats if c.get("channel") == "전화" and c.get("direction") == "INBOUND" and c.get("valid"))
            # 아웃바운드: 부재 제외하고 실통화건만 체크
            calls_out = sum(1 for c in w_chats if c.get("channel") == "전화" and c.get("direction") == "OUTBOUND" and c.get("valid") and "부재" not in (c.get("sub") or "") and "부재" not in (c.get("tag") or ""))
            calls_total = calls_in + calls_out
            op_missed = 0
            off_missed = 0

        # 채널톡 온라인 채팅 (순수 채팅 전체 모수 220건, 배송접수 제외)
        chat_in = sum(1 for c in w_chats if c.get("channel") in ["채팅", "상담사챗", "챗봇(ALF)"] and c.get("channel") != "배송접수" and c.get("direction") != "OUTBOUND")
        chat_out = sum(1 for c in w_chats if c.get("channel") in ["채팅", "상담사챗", "챗봇(ALF)"] and c.get("channel") != "배송접수" and c.get("direction") == "OUTBOUND")
        chats_all = chat_in + chat_out

        # 시스템 전수 인입량 = 게시판 + CTI 전화 + 온라인 채팅
        raw_total = b_cnt + calls_total + chats_all

        # 1. 시스템 원장 요약 (raw_summary)
        raw_summary[w_key] = {
            "total_offered_raw": raw_total,
            "raw_board": b_cnt,
            "raw_call": calls_total,
            "raw_call_inbound": calls_in,
            "raw_call_outbound": calls_out,
            "raw_call_op_missed": op_missed,
            "raw_call_off_missed": off_missed,
            "raw_chat": chats_all,
            "raw_chat_inbound": chat_in,
            "raw_chat_outbound": chat_out
        }

        # 2. CX팀 공식 성과 지표 (operational_kpis)
        # 운영시간 내 인입 모수: 평일 10~17시 인바운드 실질 응대대상 콜 + 운영시간 내 유효 채팅(인&아웃)
        if w_cti:
            cti_target_reasons = {
                "응대 가능 상담원 없음", "상담원 수신 거절", "대기열 최대 대기시간 초과",
                "링 울리는 시간 초과", "최대 대기열 수 초과", "링 울리는 중 고객 종료",
                "부재 중(ARS/IVR 이후)", "상담원 부재"
            }
            def is_cti_target(c):
                if c.get("dir") not in ("inbound", "missed"):
                    return False
                if c.get("ans") == 1:
                    return True
                r = (c.get("reason") or "").strip()
                if r in cti_target_reasons:
                    return True
                if r == "대기열에서 고객 종료" and c.get("is_in_hours"):
                    return True
                return False

            in_hours_calls = sum(1 for c in w_cti if is_cti_target(c))
            in_hours_calls_ans = sum(1 for c in w_cti if c.get("dir") in ("inbound", "missed") and c.get("ans") == 1)
        else:
            in_hours_calls = sum(1 for c in w_chats if c.get("channel") == "전화" and c.get("direction") == "INBOUND" and c.get("is_in_hours") and c.get("valid"))
            in_hours_calls_ans = in_hours_calls

        in_hours_chats = sum(1 for c in w_chats if c.get("channel") in ["채팅", "상담사챗", "챗봇(ALF)"] and c.get("direction") in ["INBOUND", "OUTBOUND"] and c.get("is_in_hours") and c.get("channel") != "배송접수")
        in_hours_chats_handled = in_hours_chats

        in_hours_offered = in_hours_calls + in_hours_chats
        handled_offered = in_hours_calls_ans + in_hours_chats_handled

        # 실응대 건수: 운영시간 내 처리 완료 건수 (일반 상담 + 재통화 포함, 배송접수 제외)
        handled_contacts = sum(1 for c in w_chats if c.get("is_in_hours") and c.get("valid") and c.get("channel") != "배송접수")
        if handled_offered > handled_contacts:
            handled_contacts = handled_offered

        repeat_contacts = sum(1 for c in w_chats if c.get("is_in_hours") and c.get("is_repeat") and c.get("channel") != "배송접수")
        after_hours_traffic = sum(1 for c in w_chats if not c.get("is_in_hours") and c.get("channel") != "배송접수")

        ans_rate = min(100.0, round((handled_offered / in_hours_offered * 100), 1)) if in_hours_offered > 0 else 0.0
        call_ans_rate = min(100.0, round((in_hours_calls_ans / in_hours_calls * 100), 1)) if in_hours_calls > 0 else 0.0
        chat_ans_rate = min(100.0, round((in_hours_chats_handled / in_hours_chats * 100), 1)) if in_hours_chats > 0 else 0.0
        rep_rate = round((repeat_contacts / handled_contacts * 100), 1) if handled_contacts > 0 else 0.0

        operational_kpis[w_key] = {
            "in_hours_offered": in_hours_offered,
            "handled_contacts": handled_contacts,
            "handled_offered": handled_offered,
            "operational_answer_rate": ans_rate,
            "call_answer_rate": call_ans_rate,
            "call_in_hours_offered": in_hours_calls,
            "call_in_hours_handled": in_hours_calls_ans,
            "chat_answer_rate": chat_ans_rate,
            "chat_in_hours_offered": in_hours_chats,
            "chat_in_hours_handled": in_hours_chats_handled,
            "repeat_contact_rate": rep_rate,
            "repeat_contacts": repeat_contacts,
            "after_hours_traffic": after_hours_traffic,
            "in_hours_board": b_cnt
        }

        # 3. 원인별 VOC 분석 (issue_breakdown)
        claims_all = [c for c in w_chats if c.get("nature") == "클레임" and c.get("valid")]
        claims_unique = [c for c in claims_all if c.get("unique_issue")]

        issue_breakdown[w_key] = {
            "total_claims_with_repeat": len(claims_all),
            "unique_claims": len(claims_unique),
            "repeat_claims": len(claims_all) - len(claims_unique)
        }

    print("✓ 3개 계층(원본요약 / CX운영KPI / 원인별VOC) 생성 완료")

    # 6. JavaScript 및 JSON 파일 생성
    channels = ["상담사챗", "챗봇(ALF)", "전화", "배송접수"]

    data_payload = {
        "TAG_MASTER": tag_master,
        "RISK_MAP": risk_map,
        "PARSED_TAGS": parsed_tags,
        "CHANNELS": channels,
        "WEEKS": weeks,
        "MONTHS": months,
        "QUARTERS": quarters,
        "YEARS": years,
        "BOARD_COUNT_BY_WEEK": board_by_week,
        "BOARD_MALLS_BY_WEEK": board_malls_by_week,
        "BOARD_COUNT_BY_MONTH": board_by_month,
        "BOARD_COUNT_BY_QUARTER": board_by_quarter,
        "BOARD_COUNT_BY_YEAR": board_by_year,
        "BOARD_MALLS_BY_MONTH": board_malls_by_month,
        "BOARD_MALLS_BY_QUARTER": board_malls_by_quarter,
        "BOARD_MALLS_BY_YEAR": board_malls_by_year,
        "CHATS_BY_WEEK": chats_by_week,
        "ISSUES_BY_WEEK": issues_by_week,
        "SHIPMENTS_BY_WEEK": shipments_by_week,
        "CTI_BY_WEEK": cti_by_week,
        "RAW_SUMMARY": raw_summary,
        "OPERATIONAL_KPIS": operational_kpis,
        "ISSUE_BREAKDOWN": issue_breakdown,
        "QUALITY_RAW": quality_raw_rows
    }

    # data.js 출력
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_js = out_dir / "data.js"
    out_json = out_dir / "data.json"

    js_content = f"""(function () {{
"use strict";

// ============================================================
// data.js — 베베숲 실제 VOC 데이터 (자동 생성 파일)
// 추출 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
// 데이터 소스: channeltalk_voc.db (fact_voc, board, shipment)
// ============================================================

const VOC_DATA_PAYLOAD = {json.dumps(data_payload, ensure_ascii=False, indent=2)};

window.VOC_DATA = VOC_DATA_PAYLOAD;
}})();
"""

    with open(out_js, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"✓ data.js 작성 완료: {out_js} ({os.path.getsize(out_js):,} bytes)")

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data_payload, f, ensure_ascii=False, indent=2)
    print(f"✓ data.json 작성 완료: {out_json} ({os.path.getsize(out_json):,} bytes)")

    print(f"==================================================")
    print(f"★ VOC 대시보드 실데이터 추출이 성공적으로 완료되었습니다!")
    print(f"==================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract real VOC data from SQLite DB for Web Dashboard")
    parser.add_argument("--db", default=None, help="Path to channeltalk_voc.db")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="Output directory for data.js and data.json")
    args = parser.parse_args()

    db_path = resolve_db_path(args.db)
    extract_dashboard_data(db_path, args.out)
