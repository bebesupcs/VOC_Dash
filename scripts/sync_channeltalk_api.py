# -*- coding: utf-8 -*-
"""
sync_channeltalk_api.py
채널톡(Channel.io) Open API v5 -> SQLite DB 실시간 자동 동기화 모듈

주요 기능:
1. 채널톡 Open API (v5) 연결 및 유효성 검증 (Access Key / Access Secret)
2. 매니저(상담원) 마스터 정보 자동 동기화 (`manager` 테이블)
3. 최근 상담 데이터(`user-chats`) 수집 및 증분 업데이트 (Incremental Upsert)
4. 상담 본문(`description`) 파싱 -> `userchat_description` 자동 적재
5. 베베숲 전사 운영 기준일/운영주차(목~수)/AI응대 판별 공식 100% 동일 적용
6. 동기화 완료 후 VOC 대시보드 데이터(`data.js`, `data.json`) 원터치 자동 갱신
"""

import argparse
from collections import Counter
from datetime import datetime, time, timedelta
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time as time_module
from zoneinfo import ZoneInfo

import pandas as pd
import requests

# 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ==============================================================================
# 기본 상수 및 설정
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "channeltalk_config.json"
DASHBOARD_DIR = BASE_DIR / "dashboard"
DEFAULT_DB_PATH = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
FALLBACK_DB_PATH = BASE_DIR / "channeltalk_voc.db"

API_BASE_URL = "https://api.channel.io/open/v5"
KST = ZoneInfo("Asia/Seoul")
OPERATION_END_TIME = time(17, 0, 0)


# ==============================================================================
# 설정 로드 & 유틸리티
# ==============================================================================
def load_config():
    config = {
        "access_key": os.environ.get("CHANNEL_ACCESS_KEY", ""),
        "access_secret": os.environ.get("CHANNEL_ACCESS_SECRET", ""),
        "db_path": DEFAULT_DB_PATH,
        "fallback_db_path": str(FALLBACK_DB_PATH),
        "sync_days_back": 14,
        "batch_size": 200,
        "auto_export_dashboard": True,
    }

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                config.update(loaded)
        except Exception as e:
            print(f"[경고] 설정 파일({CONFIG_PATH}) 로드 중 오류: {e}")

    return config


def save_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def resolve_db_path(configured_path, fallback_path):
    if configured_path and os.path.exists(configured_path):
        return Path(configured_path)
    if os.path.exists(DEFAULT_DB_PATH):
        return Path(DEFAULT_DB_PATH)
    if fallback_path and os.path.exists(fallback_path):
        print(f"[알림] 원본 네트워크 DB 대신 로컬 DB를 사용합니다: {fallback_path}")
        return Path(fallback_path)
    
    # 로컬 경로라도 파일 생성 가능하도록 반환
    target = Path(fallback_path or FALLBACK_DB_PATH)
    print(f"[알림] 새 DB 파일로 초기화합니다: {target}")
    return target


def clean_text(value):
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def clean_id(value):
    text = clean_text(value)
    if not text:
        return ""
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return text


def clean_long_id(value):
    text = clean_text(value)
    if not text:
        return ""
    text = re.sub(r"\s+", "", text)
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return text


def clean_number(value):
    text = clean_text(value)
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def extract_digits(value):
    text = clean_text(value)
    if not text:
        return ""
    digits = re.findall(r"\d+", text)
    return "".join(digits) if digits else ""


# ==============================================================================
# 채널톡 description 파싱 & 태그 분류기
# ==============================================================================
def extract_block(text, start_label, labels):
    text = clean_text(text)
    if not text:
        return ""
    pattern = (
        re.escape(start_label)
        + r"\s*(.*?)(?="
        + "|".join(re.escape(label) for label in labels)
        + r"|$)"
    )
    match = re.search(pattern, text, flags=re.S)
    return match.group(1).strip() if match else ""


def parse_description(description):
    labels = [
        "□ 제품명 :",
        "□ 제조일자 :",
        "□ 구매처/주문번호/출고처 :",
        "□ 구매처/주문번호 :",
        "□ 송장번호 :",
        "□ 문의내용 :",
        "◇ 안내 :",
        "□ 고객주소 :",
        "□ 특이사항 :",
    ]

    order_info = extract_block(description, "□ 구매처/주문번호/출고처 :", labels)
    if not order_info:
        order_info = extract_block(description, "□ 구매처/주문번호 :", labels)

    parts = [p.strip() for p in order_info.split("/")] if order_info else []
    special_note = extract_block(description, "□ 특이사항 :", labels)

    quality_send_yn = ""
    if special_note:
        first_char = special_note.strip().upper()[:1]
        if first_char == "O":
            quality_send_yn = "O"
        elif first_char == "X":
            quality_send_yn = "X"

    invoice_raw = extract_block(description, "□ 송장번호 :", labels)

    return {
        "product_name": extract_block(description, "□ 제품명 :", labels),
        "manufacture_date": extract_block(description, "□ 제조일자 :", labels),
        "mall_name": clean_text(parts[0]) if len(parts) >= 1 else "",
        "order_no": clean_long_id(parts[1]) if len(parts) >= 2 else "",
        "shipment_type": clean_text(parts[2]) if len(parts) >= 3 else "",
        "invoice_no": clean_long_id(extract_digits(invoice_raw)),
        "customer_issue": extract_block(description, "□ 문의내용 :", labels),
        "cs_action": extract_block(description, "◇ 안내 :", labels),
        "special_note": special_note,
        "quality_send_yn": quality_send_yn,
    }


def split_tag(full_tag):
    parts = [p.strip() for p in clean_text(full_tag).split("/") if p.strip()]
    return {
        "tag_a": parts[0] if len(parts) >= 1 else "",
        "tag_b": parts[1] if len(parts) >= 2 else "",
        "tag_c": parts[2] if len(parts) >= 3 else "",
    }


def infer_journey_from_tags(tag_a, tag_b, tag_c):
    if tag_a in ("단순", "콜", "운영외"):
        return "운영외"
    if tag_a in ("주문/결제", "배송/출고"):
        return "주문/배송"
    if tag_a in ("취소/반품/교환", "취소/반품"):
        return "취소/반품"
    if tag_a in ("제품/품질", "품질"):
        return "제품사용"
    if tag_a in ("이벤트/혜택", "회원/기타", "구매전"):
        return "구매전/탐색"
    return "기타"


# ==============================================================================
# 날짜 및 비즈니스 운영 로직 (목~수 운영주차, 17시 마감, 주말 이월)
# ==============================================================================
def parse_api_timestamp(val):
    if not val:
        return None
    try:
        # 밀리초 정수/부동소수점 타임스탬프 (Channel.io 기본)
        if isinstance(val, (int, float)):
            return datetime.fromtimestamp(val / 1000.0, tz=KST)
        s_val = str(val).strip()
        if s_val.isdigit():
            return datetime.fromtimestamp(int(s_val) / 1000.0, tz=KST)
        
        # ISO 문자열
        dt = pd.to_datetime(s_val)
        if pd.isna(dt):
            return None
        pydt = dt.to_pydatetime()
        if pydt.tzinfo is None:
            pydt = pydt.replace(tzinfo=KST)
        else:
            pydt = pydt.astimezone(KST)
        return pydt
    except Exception:
        return None


def calculate_business_fields(dt_kst):
    if dt_kst is None:
        return {
            "business_date": None,
            "report_date": None,
            "is_after_hours": None,
            "is_weekend": None,
            "operation_status": None,
        }

    is_weekend = 1 if dt_kst.weekday() >= 5 else 0
    is_after_hours = 1 if dt_kst.time().replace(tzinfo=None) >= OPERATION_END_TIME else 0

    business_date = dt_kst.date()
    if is_weekend:
        business_date += timedelta(days=7 - dt_kst.weekday())
        operation_status = "주말"
    elif is_after_hours:
        business_date += timedelta(days=1)
        while business_date.weekday() >= 5:
            business_date += timedelta(days=1)
        operation_status = "운영종료"
    else:
        operation_status = "운영시간"

    b_text = business_date.strftime("%Y-%m-%d")
    return {
        "business_date": b_text,
        "report_date": b_text,
        "is_after_hours": is_after_hours,
        "is_weekend": is_weekend,
        "operation_status": operation_status,
    }


def operational_week_range(dt):
    if dt is None:
        return None, None
    days_since_thursday = (dt.weekday() - 3) % 7
    week_start = dt - timedelta(days=days_since_thursday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def report_month_by_weekdays(week_start, week_end):
    if week_start is None or week_end is None:
        return None, None
    counts = Counter()
    d = week_start
    while d.date() <= week_end.date():
        if d.weekday() < 5:
            counts[(d.year, d.month)] += 1
        d += timedelta(days=1)
    if not counts:
        return week_end.year, week_end.month
    max_count = max(counts.values())
    candidates = [ym for ym, cnt in counts.items() if cnt == max_count]
    if len(candidates) == 1:
        return candidates[0]
    end_ym = (week_end.year, week_end.month)
    return end_ym if end_ym in candidates else sorted(candidates)[-1]


def week_of_month_by_weekday_majority(week_start, week_end):
    report_year, report_month = report_month_by_weekdays(week_start, week_end)
    if report_year is None or report_month is None:
        return None, None, None

    first_day = datetime(report_year, report_month, 1)
    first_week_start, _ = operational_week_range(first_day)

    week_no = 0
    cursor = first_week_start
    for _ in range(8):
        cursor_end = cursor + timedelta(days=6)
        ry, rm = report_month_by_weekdays(cursor, cursor_end)
        if ry == report_year and rm == report_month:
            week_no += 1
            if cursor.date() == week_start.date():
                return report_year, report_month, week_no
        cursor += timedelta(days=7)

    fallback_week_no = ((week_start.day - 1) // 7) + 1
    return report_year, report_month, fallback_week_no


def date_parts(dt_kst):
    if dt_kst is None:
        return {
            "year": None,
            "week_num": None,
            "month": "",
            "week": "",
            "week_of_month": "",
            "week_start_date": "",
            "week_end_date": "",
            "quarter": "",
        }

    week_start, week_end = operational_week_range(dt_kst)
    report_year, report_month, week_no = week_of_month_by_weekday_majority(week_start, week_end)
    quarter = ((report_month - 1) // 3) + 1 if report_month else 1
    week_num = int(week_start.isocalendar().week)
    return {
        "year": report_year,
        "week_num": week_num,
        "month": f"{report_year}-{report_month:02d}" if report_year and report_month else "",
        "week": f"W{week_num:02d}",
        "week_of_month": f"{report_month}월 {week_no}주" if report_month else "",
        "week_start_date": week_start.strftime("%Y-%m-%d"),
        "week_end_date": week_end.strftime("%Y-%m-%d"),
        "quarter": f"Q{quarter}",
    }


# ==============================================================================
# 채널톡 API 통신 클라이언트
# ==============================================================================
class ChannelTalkClient:
    def __init__(self, access_key, access_secret):
        self.access_key = access_key.strip()
        self.access_secret = access_secret.strip()
        self.session = requests.Session()
        self.session.headers.update({
            "x-access-key": self.access_key,
            "x-access-secret": self.access_secret,
            "accept": "application/json",
            "Content-Type": "application/json",
        })

    def request(self, method, endpoint, params=None, json_data=None, max_retries=3):
        url = f"{API_BASE_URL}{endpoint}" if not endpoint.startswith("http") else endpoint
        for attempt in range(max_retries):
            try:
                res = self.session.request(method, url, params=params, json=json_data, timeout=30)
                if res.status_code == 429:
                    # Rate limiting 처리
                    wait_sec = 2 ** (attempt + 1)
                    print(f"  [API 제한] 호출 빈도 초과(429). {wait_sec}초 후 재시도...")
                    time_module.sleep(wait_sec)
                    continue
                res.raise_for_status()
                return res.json()
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"채널톡 API 호출 실패 ({url}): {e}")
                time_module.sleep(1)

    def test_connection(self):
        """API Key 유효성 검증"""
        try:
            # 1건만 조회하여 정상 인증 확인
            data = self.request("GET", "/user-chats", params={"limit": 1})
            return True, "인증 성공! 채널톡 API와 정상 연결되었습니다."
        except Exception as e:
            return False, f"인증 실패: {e}"

    def get_managers(self):
        """상담원(매니저) 목록 조회"""
        try:
            data = self.request("GET", "/managers", params={"limit": 500})
            return data.get("managers", [])
        except Exception as e:
            print(f"  [경고] 매니저 목록 조회 실패: {e}")
            return []

    def get_user_chats_page(self, state=None, since=None, limit=200, sort_order="desc"):
        """유저 챗 페이지 단위 조회"""
        params = {
            "limit": limit,
            "sortOrder": sort_order,
        }
        if state:
            params["state"] = state
        if since:
            params["since"] = since

        return self.request("GET", "/user-chats", params=params)


# ==============================================================================
# DB 스키마 초기화 및 동기화 엔진
# ==============================================================================
def ensure_db_schema(conn):
    """DB 테이블 및 뷰가 없으면 안전하게 생성"""
    cur = conn.cursor()
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS manager (
        id TEXT PRIMARY KEY,
        name TEXT,
        __source_file TEXT,
        __source_path TEXT,
        __source_sheet TEXT,
        __file_modified_time TEXT,
        __imported_at TEXT,
        __row_hash TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tag_master (
        channelId TEXT PRIMARY KEY,
        full_tag TEXT,
        journey TEXT,
        tag_a TEXT,
        tag_b TEXT,
        tag_c TEXT,
        __source_file TEXT,
        __source_path TEXT,
        __source_sheet TEXT,
        __file_modified_time TEXT,
        __imported_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS userchat (
        id TEXT PRIMARY KEY,
        managedAt TEXT,
        name TEXT,
        description TEXT,
        tags TEXT,
        journey TEXT,
        tag_a TEXT,
        tag_b TEXT,
        tag_c TEXT,
        direction TEXT,
        assigneeId TEXT,
        mediumName TEXT,
        mediumType TEXT,
        mediumSenderName TEXT,
        alfTriggered TEXT,
        ai_status TEXT,
        is_ai_inflow INTEGER,
        is_ai_completed INTEGER,
        is_ai_transferred INTEGER,
        is_non_phone_inbound INTEGER,
        is_ai_handled INTEGER,
        is_agent_handled INTEGER,
        handle_type TEXT,
        closedAt TEXT,
        profile_csat REAL,
        week_num INTEGER,
        month TEXT,
        week TEXT,
        week_of_month TEXT,
        week_start_date TEXT,
        week_end_date TEXT,
        quarter TEXT,
        __schema_year TEXT,
        __source_file TEXT,
        __source_path TEXT,
        __source_sheet TEXT,
        __file_modified_time TEXT,
        __imported_at TEXT,
        __row_hash TEXT,
        business_date TEXT,
        report_date TEXT,
        is_after_hours INTEGER,
        is_weekend INTEGER,
        operation_status TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS userchat_description (
        id TEXT PRIMARY KEY,
        product_name TEXT,
        manufacture_date TEXT,
        mall_name TEXT,
        order_no TEXT,
        shipment_type TEXT,
        invoice_no TEXT,
        customer_issue TEXT,
        cs_action TEXT,
        special_note TEXT,
        quality_send_yn TEXT,
        __source_file TEXT,
        __source_path TEXT,
        __source_sheet TEXT,
        __file_modified_time TEXT,
        __imported_at TEXT,
        __row_hash TEXT
    )
    """)

    # fact_voc 뷰 생성/확인
    cur.execute("""
    CREATE VIEW IF NOT EXISTS fact_voc AS
    WITH base AS (
        SELECT
            uc.*,
            COALESCE(uc.report_date, DATE(uc.managedAt)) AS __basis_date
        FROM userchat uc
    ),
    period_week AS (
        SELECT
            base.*,
            DATE(
                __basis_date,
                '-' || ((CAST(STRFTIME('%w', __basis_date) AS INTEGER) + 3) % 7) || ' days'
            ) AS __week_start_date
        FROM base
    ),
    periods AS (
        SELECT
            period_week.*,
            DATE(__week_start_date, '+6 days') AS __week_end_date,
            DATE(__week_start_date, '+4 days') AS __week_anchor_date
        FROM period_week
    )
    SELECT
        p.id,
        p.__basis_date AS date,
        p.__basis_date AS report_date,
        p.business_date,
        p.is_after_hours,
        p.is_weekend,
        p.operation_status,
        p.managedAt,
        p.name,
        p.description,
        p.tags,
        p.direction,
        p.assigneeId,
        p.mediumName,
        p.mediumType,
        p.mediumSenderName,
        p.alfTriggered,
        p.ai_status,
        p.closedAt,
        p.managedAt AS managed_at,
        p.name AS customer_name,
        p.tags AS full_tag,
        p.assigneeId AS assignee_id,
        mgr.name AS manager_name,
        p.mediumName AS medium_name,
        p.mediumType AS medium_type,
        p.mediumSenderName AS medium_sender_name,
        p.alfTriggered AS alf_triggered,
        p.closedAt AS closed_at,
        CASE
            WHEN TRIM(COALESCE(p.journey, '')) IN ('제품사용', '취소/반품', '주문/배송')
                THEN '클레임'
            ELSE '단순'
        END AS voc_type,
        CASE
            WHEN LOWER(TRIM(COALESCE(p.mediumName, ''))) = 'phonenumber'
                THEN '유선'
            ELSE '채팅'
        END AS channel_type,
        p.journey,
        p.tag_a,
        p.tag_b,
        p.tag_c,
        p.profile_csat,
        p.is_ai_inflow,
        p.is_ai_completed,
        p.is_ai_transferred,
        p.is_non_phone_inbound,
        p.is_ai_handled,
        p.is_agent_handled,
        p.handle_type,
        CAST(STRFTIME('%Y', p.__week_anchor_date) AS INTEGER) AS year,
        STRFTIME('%Y-%m', p.__week_anchor_date) AS month,
        CAST(STRFTIME('%V', p.__week_start_date) AS INTEGER) AS week_num,
        'W' || STRFTIME('%V', p.__week_start_date) AS week,
        PRINTF(
            '%d월 %d주',
            CAST(STRFTIME('%m', p.__week_anchor_date) AS INTEGER),
            CAST((CAST(STRFTIME('%d', p.__week_anchor_date) AS INTEGER) - 1) / 7 AS INTEGER) + 1
        ) AS week_of_month,
        p.__week_start_date AS week_start_date,
        p.__week_end_date AS week_end_date,
        'Q' || (
            CAST((CAST(STRFTIME('%m', p.__week_anchor_date) AS INTEGER) - 1) / 3 AS INTEGER) + 1
        ) AS quarter,
        p.__schema_year,
        ud.product_name,
        ud.manufacture_date,
        ud.mall_name,
        ud.order_no,
        ud.shipment_type,
        ud.invoice_no,
        ud.customer_issue,
        ud.cs_action,
        ud.special_note,
        ud.quality_send_yn
    FROM periods p
    LEFT JOIN userchat_description ud
        ON p.id = ud.id
    LEFT JOIN manager mgr
        ON CAST(p.assigneeId AS TEXT) = CAST(mgr.id AS TEXT)
    """)
    conn.commit()


def load_tag_master(conn):
    cur = conn.cursor()
    cur.execute("SELECT full_tag, journey, tag_a, tag_b, tag_c FROM tag_master")
    tag_map = {}
    for r in cur.fetchall():
        if r[0]:
            tag_map[r[0]] = {
                "journey": r[1] or "",
                "tag_a": r[2] or "",
                "tag_b": r[3] or "",
                "tag_c": r[4] or "",
            }
    return tag_map


def sync_managers(client, conn):
    """매니저 목록 동기화"""
    print("▶ 상담원(매니저) 목록 동기화 중...")
    managers = client.get_managers()
    if not managers:
        print("  - 동기화할 매니저 정보 없음.")
        return 0

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()
    upserted = 0
    for m in managers:
        m_id = str(m.get("id", ""))
        name = m.get("name", "")
        if m_id and name:
            cur.execute("""
                INSERT OR REPLACE INTO manager (id, name, __imported_at, __source_file)
                VALUES (?, ?, ?, 'API:Channel.io v5')
            """, (m_id, name, now_str))
            upserted += 1

    conn.commit()
    print(f"  ✓ 매니저 {upserted}명 동기화 완료.")
    return upserted


def sync_user_chats(client, conn, sync_days_back=45, batch_size=200, full_sync=False):
    """
    유저 챗 증분 동기화
    closed(완료 상담)와 opened(진행 중 상담) 모두 수집
    최신(sortOrder=desc)부터 탐색하며 sync_days_back 기준 이전 데이터 도달 시 중단
    """
    tag_map = load_tag_master(conn)
    cur = conn.cursor()

    cutoff_dt = None
    if not full_sync and sync_days_back > 0:
        cutoff_dt = datetime.now(tz=KST) - timedelta(days=sync_days_back)
        print(f"▶ 최근 {sync_days_back}일 상담 데이터 증분 수집 시작 (기준일시: {cutoff_dt.strftime('%Y-%m-%d %H:%M:%S')})...")
    else:
        print("▶ 전체 상담 데이터 동기화 시작 (시간이 다소 소요될 수 있습니다)...")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_fetched = 0
    total_upserted = 0

    # closed(완료 상담)와 opened(진행 중 상담) 순차 수집
    for target_state in ["closed", "opened"]:
        print(f"\n▶ [{target_state.upper()}] 상태 상담 데이터 수집 시작...")
        page_cursor = None
        page_num = 1

        while True:
            print(f"  [{target_state} 페이지 {page_num}] 데이터 수신 요청 중 (커서: {page_cursor or '최신'})...")
            try:
                res = client.get_user_chats_page(state=target_state, limit=batch_size, since=page_cursor, sort_order="desc")
            except Exception as e:
                print(f"  [에러] 페이지 {page_num} 수신 실패: {e}")
                break

            chats = res.get("userChats", [])
            if not chats:
                print(f"  - [{target_state}] 더 이상 수신할 채팅 내역이 없습니다.")
                break

            total_fetched += len(chats)
            stop_pagination = False

            userchat_rows = []
            desc_rows = []

            for chat in chats:
                chat_id = clean_id(chat.get("id"))
                if not chat_id:
                    continue

                # 접수일시 (managedAt -> createdAt -> openedAt 순)
                managed_at_raw = chat.get("managedAt") or chat.get("createdAt") or chat.get("openedAt")
                dt_kst = parse_api_timestamp(managed_at_raw)

                managed_at = dt_kst.strftime("%Y-%m-%d %H:%M:%S") if dt_kst else ""
                closed_at_raw = chat.get("closedAt")
                dt_closed = parse_api_timestamp(closed_at_raw)
                closed_at = dt_closed.strftime("%Y-%m-%d %H:%M:%S") if dt_closed else ""

                # 비즈니스 일자 및 주차
                business_fields = calculate_business_fields(dt_kst)
                parts = date_parts(dt_kst)

                # 태그 처리
                raw_tags = chat.get("tags") or []
                if isinstance(raw_tags, list):
                    full_tag = raw_tags[0] if raw_tags else ""
                else:
                    full_tag = clean_text(raw_tags)

                tag_info = tag_map.get(full_tag)
                if not tag_info:
                    st = split_tag(full_tag)
                    journey = infer_journey_from_tags(st["tag_a"], st["tag_b"], st["tag_c"])
                    tag_info = {
                        "journey": journey,
                        "tag_a": st["tag_a"],
                        "tag_b": st["tag_b"],
                        "tag_c": st["tag_c"],
                    }

                # 고객명
                cust_name = clean_text(chat.get("name"))

                # 채널 및 방향
                source = chat.get("source") or {}
                medium_obj = source.get("medium") or {}
                contact_medium = clean_text(
                    chat.get("contactMediumType")
                    or medium_obj.get("mediumType")
                    or chat.get("mediumType")
                    or ""
                )
                medium_name = clean_text(chat.get("mediumName") or contact_medium).lower()
                direction = clean_text(chat.get("direction") or "INBOUND").lower()

                assignee_id = clean_id(chat.get("assigneeId"))

                # AI / 워크플로우(ALF) 응대 여부 판별
                # 채널톡 v5에서는 supportBot 외에 workflow가 신규 챗봇 엔진임
                source = chat.get("source") or {}
                workflow = source.get("workflow")
                support_bot = source.get("supportBot")
                is_workflow_triggered = bool(workflow or support_bot or chat.get("alfTriggered"))

                is_non_phone_inbound = (
                    direction == "inbound"
                    and medium_name not in ("phonenumber", "phone_number", "phone")
                    and contact_medium.lower() not in ("phonenumber", "phone_number", "phone")
                )

                # 상담원 실제 답변 발송 여부 (최초 답변 시각 또는 답변 횟수)
                agent_replied = bool(chat.get("firstRepliedAt")) or bool(chat.get("replyCount") and chat.get("replyCount") > 0)

                # AI(ALF) 완결 판별:
                # 1) 워크플로우/서포트봇이 실행되었고 상담원 개입(답변)이 없었던 경우
                # 2) 또는 매니저 미배정 건
                # 3) 상담 설명문에 'ALF 답변' 등이 기재된 경우
                is_ai_handled = is_non_phone_inbound and (
                    (is_workflow_triggered and not agent_replied)
                    or assignee_id == ""
                    or "ALF" in (chat.get("description") or "").upper()
                )
                is_agent_handled = is_non_phone_inbound and not is_ai_handled

                alf_triggered = "true" if is_workflow_triggered else "false"

                handling_type = (chat.get("handling") or {}).get("type") or ""
                if is_ai_handled:
                    ai_status = "completed"
                    handle_type = "AI"
                elif is_agent_handled:
                    ai_status = "transferred"
                    handle_type = "AGENT"
                else:
                    ai_status = handling_type
                    handle_type = "EXCLUDED"

                # 설명문
                description = chat.get("description") or ""

                # userchat 레코드 생성
                userchat_rows.append((
                    chat_id,
                    managed_at,
                    cust_name,
                    description,
                    full_tag,
                    tag_info["journey"],
                    tag_info["tag_a"],
                    tag_info["tag_b"],
                    tag_info["tag_c"],
                    direction.upper(),
                    assignee_id,
                    medium_name,
                    contact_medium,
                    clean_text(chat.get("mediumSenderName")),
                    alf_triggered,
                    ai_status,
                    1 if is_non_phone_inbound else 0,  # is_ai_inflow
                    1 if is_ai_handled else 0,        # is_ai_completed
                    1 if is_agent_handled else 0,      # is_ai_transferred
                    1 if is_non_phone_inbound else 0,  # is_non_phone_inbound
                    1 if is_ai_handled else 0,        # is_ai_handled
                    1 if is_agent_handled else 0,      # is_agent_handled
                    handle_type,
                    closed_at,
                    clean_number((chat.get("profile") or {}).get("csat")),
                    parts["week_num"],
                    parts["month"],
                    parts["week"],
                    parts["week_of_month"],
                    parts["week_start_date"],
                    parts["week_end_date"],
                    parts["quarter"],
                    str(parts["year"] or datetime.now().year),
                    "API:Channel.io v5",
                    "API",
                    "user-chats",
                    now_str,
                    now_str,
                    f"api_{chat_id}",
                    business_fields["business_date"],
                    business_fields["report_date"],
                    business_fields["is_after_hours"],
                    business_fields["is_weekend"],
                    business_fields["operation_status"],
                ))

                # description 파싱 레코드 생성
                parsed_desc = parse_description(description)
                desc_rows.append((
                    chat_id,
                    parsed_desc["product_name"],
                    parsed_desc["manufacture_date"],
                    parsed_desc["mall_name"],
                    parsed_desc["order_no"],
                    parsed_desc["shipment_type"],
                    parsed_desc["invoice_no"],
                    parsed_desc["customer_issue"],
                    parsed_desc["cs_action"],
                    parsed_desc["special_note"],
                    parsed_desc["quality_send_yn"],
                    "API:Channel.io v5",
                    "API",
                    "user-chats",
                    now_str,
                    now_str,
                    f"api_desc_{chat_id}",
                ))

            # DB 트랜잭션 적재
            if userchat_rows:
                cur.executemany("""
                    INSERT OR REPLACE INTO userchat (
                        id, managedAt, name, description, tags, journey, tag_a, tag_b, tag_c,
                        direction, assigneeId, mediumName, mediumType, mediumSenderName,
                        alfTriggered, ai_status, is_ai_inflow, is_ai_completed, is_ai_transferred,
                        is_non_phone_inbound, is_ai_handled, is_agent_handled, handle_type,
                        closedAt, profile_csat, week_num, month, week, week_of_month,
                        week_start_date, week_end_date, quarter, __schema_year, __source_file,
                        __source_path, __source_sheet, __file_modified_time, __imported_at,
                        __row_hash, business_date, report_date, is_after_hours, is_weekend,
                        operation_status
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?
                    )
                """, userchat_rows)

                cur.executemany("""
                    INSERT OR REPLACE INTO userchat_description (
                        id, product_name, manufacture_date, mall_name, order_no,
                        shipment_type, invoice_no, customer_issue, cs_action,
                        special_note, quality_send_yn, __source_file, __source_path,
                        __source_sheet, __file_modified_time, __imported_at, __row_hash
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?
                    )
                """, desc_rows)

                conn.commit()
                total_upserted += len(userchat_rows)
                print(f"  ✓ [{target_state}] {len(userchat_rows)}건 DB 반영 완료 (누적: {total_upserted}건)")

            # 페이지 단위 기준일자 도달 여부 판정
            if cutoff_dt:
                if target_state == "closed":
                    oldest_ts = min(((c.get("closedAt") or c.get("updatedAt") or 0) for c in chats), default=0)
                else:
                    oldest_ts = min(((c.get("createdAt") or 0) for c in chats), default=0)
                if oldest_ts and (oldest_ts / 1000.0) < cutoff_dt.timestamp():
                    stop_pagination = True

            if stop_pagination or (target_state == "opened" and page_num >= 3):
                print(f"  - [{target_state}] 기준 범위 데이터 수집을 종료합니다.", flush=True)
                break

            # 다음 페이지 커서
            page_cursor = res.get("next")
            if not page_cursor:
                print(f"  - [{target_state}] 마지막 페이지에 도달했습니다.", flush=True)
                break

            page_num += 1
            time_module.sleep(0.15)  # API Rate limit 방지

    print(f"▶ 총 {total_fetched}건 조회 중 {total_upserted}건 최신화 완료!")
    return total_upserted


# ==============================================================================
# 메인 실행 파이프라인
# ==============================================================================
def run_sync(access_key=None, access_secret=None, days=None, full=False, export_dashboard=True):
    print("=" * 60)
    print("🚀 베베숲 채널톡 Open API 실시간 VOC 자동 동기화")
    print("=" * 60)

    config = load_config()

    ak = (access_key or config.get("access_key") or "").strip()
    sk = (access_secret or config.get("access_secret") or "").strip()

    # 키가 없을 경우 콘솔 입력 유도
    if not ak or not sk:
        print("\n[!] 채널톡 API 키가 설정되지 않았습니다.")
        print(f"    설정 파일 위치: {CONFIG_PATH}\n")
        try:
            ak = input("채널톡 Access Key를 입력하세요: ").strip()
            sk = input("채널톡 Access Secret을 입력하세요: ").strip()
            if ak and sk:
                config["access_key"] = ak
                config["access_secret"] = sk
                save_config(config)
                print(f"✓ 입력하신 API 키가 {CONFIG_PATH}에 안전하게 저장되었습니다.\n")
            else:
                print("❌ API 키가 입력되지 않아 작업을 중단합니다.")
                return False
        except (EOFError, KeyboardInterrupt):
            print("❌ 입력이 취소되었습니다.")
            return False

    client = ChannelTalkClient(ak, sk)

    # 1. 연결 테스트
    print("▶ 채널톡 API 연결 검증 중...")
    success, msg = client.test_connection()
    if not success:
        print(f"❌ 연결 실패: {msg}")
        print("   Access Key와 Access Secret을 다시 한 번 확인해주세요.")
        return False
    print(f"✓ {msg}\n")

    # 2. DB 연결 및 스키마 확인
    db_path = resolve_db_path(config.get("db_path"), config.get("fallback_db_path"))
    print(f"▶ 타겟 DB 연결: {db_path}", flush=True)
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    ensure_db_schema(conn)

    # 3. 매니저 동기화
    sync_managers(client, conn)

    # 4. 상담 내역 증분 동기화
    sync_days = days if days is not None else config.get("sync_days_back", 14)
    upserted_count = sync_user_chats(
        client,
        conn,
        sync_days_back=sync_days,
        batch_size=config.get("batch_size", 200),
        full_sync=full,
    )
    conn.close()

    # 5. VOC 대시보드 자동 내보내기 (data.js)
    if export_dashboard and config.get("auto_export_dashboard", True):
        print("\n" + "=" * 60)
        print("📊 VOC 대시보드 데이터 자동 갱신 트리거")
        print("=" * 60)
        try:
            from export_dashboard_data import extract_dashboard_data, resolve_db_path
            resolved_db = resolve_db_path(str(db_path))
            extract_dashboard_data(str(resolved_db), DASHBOARD_DIR)
            print("✓ 대시보드 데이터(data.js, data.json) 갱신 완료!")
        except Exception as e:
            print(f"[경고] 대시보드 데이터 내보내기 중 오류: {e}")

    print("\n" + "=" * 60)
    print(f"✨ [완료] 채널톡 API 동기화 및 대시보드 갱신이 성공적으로 끝났습니다! ({upserted_count}건 반영)")
    print("=" * 60)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="채널톡 API 실시간 동기화")
    parser.add_argument("--key", help="Channel.io Access Key")
    parser.add_argument("--secret", help="Channel.io Access Secret")
    parser.add_argument("--days", type=int, default=None, help="과거 수집 일수 (기본 14일)")
    parser.add_argument("--full", action="store_true", help="전체 데이터 수집 (과거 전체)")
    args = parser.parse_args()

    run_sync(access_key=args.key, access_secret=args.secret, days=args.days, full=args.full)
