# -*- coding: utf-8 -*-
"""
ChannelTalk Excel → SQLite DB Import

2025/2026 컬럼 구조 차이 + missedReason 부재 기준 대응 + 속도 개선 버전

핵심 기능
1. raw 폴더 아래 모든 채널톡 엑셀 자동 탐색
2. UserChat / UserChat data → userchat 표준 테이블
3. UserChat meet data → userchat_meet
4. Manager data → manager
5. description → userchat_description 자동 파싱
6. master/tag_master.xlsx → tag_master 전체 덮어쓰기
7. import_log 기준 이미 처리한 파일은 FILE SKIP
8. ID 계열은 전부 TEXT 저장
9. FK 강제 OFF
10. managedAt 없으면 createdAt → openedAt 순서로 대체
11. SQLite 성능 PRAGMA 적용
12. read_sheet 엑셀 중복 오픈 최소화
"""

import argparse
from collections import Counter
import hashlib
import io
import re
import sqlite3
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import pandas as pd

try:
    import msoffcrypto
except ImportError:
    msoffcrypto = None


EXCEL_PASSWORDS = ["1111", "qpqptnv1"]
KST = ZoneInfo("Asia/Seoul")
OPERATION_END_TIME = time(17, 0, 0)

USERCHAT_SHEETS = ["UserChat", "UserChat data"]
MEET_SHEETS = ["UserChat meet data"]
OLD_MEET_SHEETS = ["Old_UserChat meet data"]
MANAGER_SHEETS = ["Manager data", "Manager"]
TAG_MASTER_SHEETS = ["tag_master", "TAG_MASTER", "TagMaster"]


# =========================
# 공통 유틸
# =========================

def normalize_col(col):
    col = str(col).strip()
    col = re.sub(r"\s+", "_", col)
    col = re.sub(r"[^\w가-힣.]", "_", col)
    col = re.sub(r"_+", "_", col).strip("_")
    return col or "empty_col"


def unique_cols(cols):
    seen = {}
    out = []
    for col in cols:
        base = normalize_col(col)
        if base not in seen:
            seen[base] = 0
            out.append(base)
        else:
            seen[base] += 1
            out.append(f"{base}_{seen[base]}")
    return out


def excel_engine(path):
    return "pyxlsb" if path.suffix.lower() == ".xlsb" else "openpyxl"


def find_excel_files(base):
    files = []

    skip_keywords = [
        "배송 데이터 원본",
        "배송",
        "shipment",
        "CJ(",
        "게시판",
        "board"
    ]

    for raw_dir in [p for p in base.rglob("raw") if p.is_dir()]:
        for ext in ("*.xlsx", "*.xlsm", "*.xlsb"):
            for f in raw_dir.rglob(ext):

                if f.name.startswith("~$") or f.stat().st_size <= 1024:
                    continue

                path_text = str(f).lower()

                if any(keyword.lower() in path_text for keyword in skip_keywords):
                    continue

                files.append(f)

    return sorted(set(files))


def find_tag_master_file(base):
    master_dir = base / "master"
    if not master_dir.exists():
        return None

    for filename in ["tag_master.xlsx", "tag_master.xlsm", "tag_master.xlsb"]:
        path = master_dir / filename
        if path.exists():
            return path

    files = []
    for ext in ("*.xlsx", "*.xlsm", "*.xlsb"):
        files.extend(master_dir.rglob(ext))

    files = [
        f for f in files
        if "tag_master" in f.name.lower() and not f.name.startswith("~$")
    ]

    return sorted(files)[0] if files else None


def load_excel_source(path):
    try:
        pd.ExcelFile(path, engine=excel_engine(path))
        return path
    except Exception as e:
        msg = str(e)
        maybe_encrypted = (
            "File is not a zip file" in msg
            or "encrypted" in msg.lower()
            or "password" in msg.lower()
        )

        if not maybe_encrypted:
            raise

    if msoffcrypto is None:
        raise RuntimeError("암호화 엑셀을 읽으려면 pip install msoffcrypto-tool 필요")

    last_error = None

    for pwd in EXCEL_PASSWORDS:
        try:
            decrypted = io.BytesIO()
            with open(path, "rb") as f:
                office_file = msoffcrypto.OfficeFile(f)
                office_file.load_key(password=pwd)
                office_file.decrypt(decrypted)
            decrypted.seek(0)
            return decrypted
        except Exception as e:
            last_error = e

    raise RuntimeError(f"엑셀 비밀번호 해제 실패: {path} / {last_error}")


def read_sheet(path, candidates, fallback_first_sheet=False):
    """
    엑셀 시트 읽기 최적화 버전.
    기존 버전은 sheet_names 확인 후 같은 파일을 다시 열어 read_excel을 수행했다.
    이 버전은 ExcelFile 객체를 재사용하여 파일 오픈 횟수를 줄인다.
    """
    try:
        src = load_excel_source(path)
        xls = pd.ExcelFile(src, engine=excel_engine(path))

        sheet = next((s for s in candidates if s in xls.sheet_names), None)

        if sheet is None and fallback_first_sheet and xls.sheet_names:
            sheet = xls.sheet_names[0]

        if sheet is None:
            return None, None

        df = pd.read_excel(xls, sheet_name=sheet, dtype=str)

        if df.empty:
            return None, sheet

        df.columns = unique_cols(df.columns)
        return df, sheet

    except Exception as e:
        print(f"[ERROR] 파일 읽기 실패: {path} / {e}")
        return None, None


def clean_text(value):
    if value is None or pd.isna(value):
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


def clean_number(value):
    text = clean_text(value)
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None



def clean_flag(value, default=None):
    text = clean_text(value).lower()
    if text in ("1", "true", "t", "y", "yes", "o", "완료", "completed"):
        return 1
    if text in ("0", "false", "f", "n", "no", "x", ""):
        return 0 if default is None else default
    try:
        return 1 if float(text) != 0 else 0
    except Exception:
        return 0 if default is None else default


def clean_long_id(value):
    """
    주문번호/송장번호처럼 긴 숫자 ID를 숫자가 아닌 TEXT로 보존한다.
    - 12345.0 형태는 12345로 정리
    - 공백/개행 제거
    - 지수표기처럼 보이는 값도 문자열 그대로 유지
    """
    text = clean_text(value)
    if not text:
        return ""
    text = re.sub(r"\s+", "", text)
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return text


def extract_digits(value):
    """송장번호 영역에서 숫자만 추출한다."""
    text = clean_text(value)
    if not text:
        return ""
    digits = re.findall(r"\d+", text)
    return "".join(digits) if digits else ""


def normalize_timestamp(value):
    text = clean_text(value)
    if not text:
        return ""
    try:
        dt = pd.to_datetime(value, errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return text

def calculate_business_fields(value):
    """접수시각을 KST로 해석해 운영기준일과 운영상태를 계산한다.

    timezone이 없는 값은 이미 대한민국 표준시인 것으로 간주한다.
    법정공휴일은 이번 긴급 패치 범위에서 적용하지 않는다.
    """
    text = clean_text(value)
    if not text:
        return {
            "business_date": None,
            "report_date": None,
            "is_after_hours": None,
            "is_weekend": None,
            "operation_status": None,
        }

    try:
        parsed = pd.to_datetime(value, errors="coerce")
    except Exception:
        parsed = pd.NaT

    if pd.isna(parsed):
        return {
            "business_date": None,
            "report_date": None,
            "is_after_hours": None,
            "is_weekend": None,
            "operation_status": None,
        }

    dt = parsed.to_pydatetime() if hasattr(parsed, "to_pydatetime") else parsed
    if dt.tzinfo is None or dt.utcoffset() is None:
        dt_kst = dt.replace(tzinfo=KST)
    else:
        dt_kst = dt.astimezone(KST)

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

    business_date_text = business_date.strftime("%Y-%m-%d")
    return {
        "business_date": business_date_text,
        "report_date": business_date_text,
        "is_after_hours": is_after_hours,
        "is_weekend": is_weekend,
        "operation_status": operation_status,
    }

def first_col(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def get_value(row, col):
    if not col or col not in row.index:
        return ""
    return row[col]


def get_first_value(row, df, candidates):
    col = first_col(df, candidates)
    return get_value(row, col)


def file_modified_time(path):
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


def now_text():
    return datetime.now().isoformat(timespec="seconds")


def row_hash_from_dict(data):
    text = "||".join(
        f"{k}={'' if data[k] is None else str(data[k])}"
        for k in sorted(data.keys())
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def infer_schema_year(path):
    path_text = str(path)
    if "2026" in path_text or "26년" in path_text:
        return "2026"
    if "2025" in path_text or "25년" in path_text:
        return "2025"
    if "2024" in path_text or "24년" in path_text:
        return "2024"
    return ""

# =========================
# 스키마 감지 / 표준 meet 변환
# =========================

def schema_column_list(columns):
    """
    시트 컬럼 구조를 비교하기 위한 표준 문자열.
    read_sheet()에서 이미 unique_cols/normalize_col 처리된 컬럼명을 사용한다.
    """
    return "|".join(str(c).strip() for c in columns)


def schema_hash_from_columns(columns):
    return hashlib.sha256(schema_column_list(columns).encode("utf-8")).hexdigest()


def detect_meet_schema_version(columns):
    """
    UserChat meet data 시트 버전 자동 판별.
    날짜나 폴더명이 아니라 실제 컬럼 존재 여부 기준으로 판단한다.
    """
    cols = set(columns)

    # 2026 이후 신규 구조
    if {"meetId", "callDuration"}.issubset(cols) or {"meetId", "firstEngagedAt"}.issubset(cols) or {"meetId", "callAssigneeId"}.issubset(cols):
        return "meet_v2"

    # 2025 3Q처럼 meetId는 있지만 v1 컬럼 구조를 쓰는 경우
    if {"meetId", "duration"}.issubset(cols) or {"meetId", "engagedAt"}.issubset(cols):
        return "meet_v1"

    # Old_UserChat meet data 구조 (engagedAt 등이 전부 결측/드롭되어도 id, duration/userChatId가 있으면 v1)
    if {"id", "duration"}.issubset(cols) or {"id", "engagedAt"}.issubset(cols) or ({"id", "userChatId"}.issubset(cols) and "meetId" not in cols):
        return "meet_v1"

    return "unknown"



def register_schema_if_needed(conn, sheet_name, schema_version, columns):
    """
    발견된 시트 구조를 schema_registry에 기록한다.
    이미 같은 schema_hash가 있으면 last_detected_at만 갱신한다.
    """
    col_list = schema_column_list(columns)
    s_hash = schema_hash_from_columns(columns)
    now = now_text()

    existing = conn.execute("""
        SELECT id
        FROM schema_registry
        WHERE sheet_name = ?
          AND schema_hash = ?
    """, (sheet_name, s_hash)).fetchone()

    if existing:
        conn.execute("""
            UPDATE schema_registry
            SET last_detected_at = ?
            WHERE id = ?
        """, (now, existing[0]))
    else:
        conn.execute("""
            INSERT INTO schema_registry (
                sheet_name,
                schema_version,
                schema_hash,
                column_list,
                first_detected_at,
                last_detected_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sheet_name, schema_version, s_hash, col_list, now, now))

    return s_hash, col_list


def log_schema_event(conn, path, sheet, schema_hash, schema_version, status, message=""):
    conn.execute("""
        INSERT INTO import_schema_log (
            file_name,
            sheet_name,
            schema_hash,
            schema_version,
            status,
            imported_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        path.name,
        sheet,
        schema_hash,
        schema_version,
        status if not message else f"{status}: {message}",
        now_text()
    ))


def standard_date_parts(started_at):
    dt = to_datetime_safe(started_at)
    if dt is None:
        return None, None, None
    return int(dt.year), int(dt.month), int(dt.isocalendar().week)


def is_non_empty(value):
    text = clean_text(value)
    return bool(text)


def response_target_flag(direction):
    return 1 if clean_text(direction).lower() == "inbound" else 0




def normalize_missed_reason(reason):
    """missedReason 비교용 정규화.
    Excel/SQLite/Power BI 경유 중 생기는 공백, 개행, 대소문자 차이를 흡수한다.
    """
    text = clean_text(reason)
    if not text:
        return ""
    text = re.sub(r"\s+", "", text)
    aliases = {
        "notinoperation": "notInOperation",
        "nooperator": "noOperator",
        "rejectedbyoperator": "rejectedByOperator",
        "abandonedinqueue": "abandonedInQueue",
        "ringtimeover": "ringTimeOver",
        "exceededqueue": "exceededQueue",
        "userleftingreeting": "userLeftInGreeting",
        "userleftinivrwithoutinput": "userLeftInIvrWithoutInput",
        "userleftinivr": "userLeftInIvr",
        "userleftinqueued": "userLeftInQueued",
        "userleftinwaitingmanager": "userLeftInWaitingManager",
        "wfinputtimeout": "wfInputTimeout",
        "wfvoicemail": "wfVoiceMail",
        "wfendcall": "wfEndCall",
        "managerleft": "managerLeft",
        "userleft": "userleft",
        "workflow": "workflow",
    }
    return aliases.get(text.lower(), text)

def classify_missed_reason(reason, schema_version=""):
    """missedReason 값을 보고 Power BI용 부재 사유 카테고리를 표준화한다."""
    reason = normalize_missed_reason(reason)
    if not reason:
        return ""

    labels = {
        # meet_v2
        "notInOperation": "운영 시간 아님",
        "noOperator": "응대 가능 상담원 없음",
        "rejectedByOperator": "상담원 수신 거절",
        "abandonedInQueue": "대기열 최대 대기시간 초과",
        "ringTimeOver": "링 울리는 시간 초과",
        "exceededQueue": "최대 대기열 수 초과",
        "userLeftInGreeting": "인사말 재생 중 고객 종료",
        "userLeftInIvrWithoutInput": "IVR 입력 전 고객 종료",
        "userLeftInIvr": "IVR 진행 중 고객 종료",
        "userLeftInQueued": "대기열에서 고객 종료",
        "userLeftInWaitingManager": "링 울리는 중 고객 종료",
        "wfInputTimeout": "워크플로우 입력 시간 초과",
        "wfVoiceMail": "음성 사서함",
        "wfEndCall": "워크플로우로 통화 종료",
        "managerLeft": "발신 미연결",

        # meet_v1
        "userleft": "고객이 먼저 끊었을 때",
        "userLeft": "고객이 먼저 끊었을 때",
        "workflow": "액션을 통해 종료되었을 때",
    }
    return labels.get(reason, reason)


def is_missed_by_reason(schema_version, reason):
    """
    사용자가 확정한 부재여부 기준.
    1 = 부재 건수 포함(Y)
    0 = 부재 제외(N)
    """
    reason = normalize_missed_reason(reason)
    if not reason:
        return 0

    v1_missed = {
        "userleft": 1,
        "userLeft": 1,
        "workflow": 0,
    }

    v2_missed = {
        "notInOperation": 0,
        "noOperator": 1,
        "rejectedByOperator": 1,
        "abandonedInQueue": 1,
        "ringTimeOver": 1,
        "exceededQueue": 1,
        "userLeftInGreeting": 0,
        "userLeftInIvrWithoutInput": 0,
        "userLeftInIvr": 0,
        "userLeftInQueued": 1,
        "userLeftInWaitingManager": 1,
        "wfInputTimeout": 0,
        "wfVoiceMail": 1,
        "wfEndCall": 0,
        "managerLeft": 0,
    }

    schema_version = clean_text(schema_version).lower()
    if schema_version == "meet_v1":
        return int(v1_missed.get(reason, 0))
    if schema_version == "meet_v2":
        return int(v2_missed.get(reason, 0))
    return int(v2_missed.get(reason, v1_missed.get(reason, 0)))


def is_response_target_by_reason(schema_version, reason):
    """
    missedReason 기준 응대율 분모 포함 여부.
    1 = 응대율 분모 포함(Y)
    0 = 응대율 분모 제외(N)
    """
    reason = normalize_missed_reason(reason)
    if not reason:
        return 0

    v1_target = {
        "userleft": 1,
        "userLeft": 1,
        "workflow": 0,
    }

    v2_target = {
        "notInOperation": 0,
        "noOperator": 1,
        "rejectedByOperator": 1,
        "abandonedInQueue": 1,
        "ringTimeOver": 1,
        "exceededQueue": 1,
        "userLeftInGreeting": 0,
        "userLeftInIvrWithoutInput": 0,
        "userLeftInIvr": 0,
        "userLeftInQueued": 1,
        "userLeftInWaitingManager": 1,
        "wfInputTimeout": 0,
        "wfVoiceMail": 1,
        "wfEndCall": 0,
        "managerLeft": 0,
    }

    schema_version = clean_text(schema_version).lower()
    if schema_version == "meet_v1":
        return int(v1_target.get(reason, 0))
    if schema_version == "meet_v2":
        return int(v2_target.get(reason, 0))
    return int(v2_target.get(reason, v1_target.get(reason, 0)))


def missed_flag_by_reason(reason):
    """missed_reason 원문 기준 부재 여부. schema_version 오판으로 Y가 N으로 빠지지 않도록 reason 기준을 우선한다."""
    reason = normalize_missed_reason(reason)
    y_reasons = {
        "noOperator",
        "rejectedByOperator",
        "abandonedInQueue",
        "ringTimeOver",
        "exceededQueue",
        "userLeftInQueued",
        "userLeftInWaitingManager",
        "wfVoiceMail",
        "userleft",
        "userLeft",
    }
    return 1 if reason in y_reasons else 0


def response_target_flag_by_reason(reason, direction=""):
    """missed_reason 원문 기준 응대필수 여부. outbound은 무조건 응대필수 제외한다."""
    direction = clean_text(direction).lower()
    if direction == "outbound":
        return 0

    reason = normalize_missed_reason(reason)
    y_reasons = {
        "noOperator",
        "rejectedByOperator",
        "abandonedInQueue",
        "ringTimeOver",
        "exceededQueue",
        "userLeftInQueued",
        "userLeftInWaitingManager",
        "wfVoiceMail",
        "userleft",
        "userLeft",
    }
    return 1 if reason in y_reasons else 0


def calculate_standard_meet_flags(reason):
    """missed_reason 하나만 기준으로 meet 플래그를 계산한다.

    최종 확정 기준
    - missed_reason 빈값: is_answered=1, is_missed=0, is_response_target=1
    - YY_REASONS: is_answered=0, is_missed=1, is_response_target=1
    - 그 외: is_answered=0, is_missed=0, is_response_target=0

    direction, engaged_at, schema_version은 플래그 계산에 사용하지 않는다.
    """
    reason = normalize_missed_reason(reason)

    yy_reasons = {
        "noOperator",
        "abandonedInQueue",
        "ringTimeOver",
        "userleft",
        "userLeft",
        "exceededQueue",
        "userLeftInQueued",
        "userLeftInWaitingManager",
        "wfVoiceMail",
    }

    if reason == "":
        return 1, 0, 1

    if reason in yy_reasons:
        return 0, 1, 1

    return 0, 0, 0


def build_standard_meet_row(row, df, schema_version, path, sheet):
    """meet_v1 / meet_v2를 Power BI 분석용 표준 컬럼으로 변환한다."""
    if schema_version == "meet_v1":
        meet_key = clean_id(get_first_value(row, df, ["id", "ID", "meetId"]))
        user_chat_id = clean_id(get_first_value(row, df, ["userChatId", "userchatId", "user_chat_id", "UserChatId", "유저챗ID", "유저챗_id"]))
        started_at = normalize_timestamp(get_first_value(row, df, ["startedAt"]))
        ended_at = normalize_timestamp(get_first_value(row, df, ["endedAt"]))
        engaged_at = normalize_timestamp(get_first_value(row, df, ["engagedAt"]))
        direction = clean_text(get_first_value(row, df, ["direction"]))
        call_type = clean_text(get_first_value(row, df, ["type"]))
        missed_reason = clean_text(get_first_value(row, df, ["missedReason"]))

        data = {
            "meet_key": meet_key,
            "user_chat_id": user_chat_id,
            "source_version": "meet_v1",
            "source_file": path.name,
            "source_sheet": sheet,
            "started_at": started_at,
            "ended_at": ended_at,
            "engaged_at": engaged_at,
            "direction": direction,
            "call_type": call_type,
            "from_number": clean_text(get_first_value(row, df, ["from"])),
            "to_number": clean_text(get_first_value(row, df, ["to"])),
            "primary_number": clean_text(get_first_value(row, df, ["primaryNumber"])),
            "representative_number": clean_text(get_first_value(row, df, ["representativeNumber"])),
            "missed_reason": missed_reason,
            "missed_category": classify_missed_reason(missed_reason, schema_version),
            "duration_sec": clean_number(get_first_value(row, df, ["duration"])),
            "queue_time_sec": None,
            "hold_time_sec": None,
            "hold_count": None,
            "first_waiting_started_at": normalize_timestamp(get_first_value(row, df, ["firstWaitingStartedAt"])),
            "first_ring_started_at": normalize_timestamp(get_first_value(row, df, ["firstRingStartedAt"])),
            "first_ring_ended_at": "",
            "first_queue_in_at": "",
            "first_queue_out_at": "",
            "assignee_id": "",
            "billing_type": "",
        }

    elif schema_version == "meet_v2":
        meet_key = clean_id(get_first_value(row, df, ["meetId"]))
        user_chat_id = clean_id(get_first_value(row, df, ["userChatId", "userchatId", "user_chat_id", "UserChatId", "유저챗ID", "유저챗_id"]))
        started_at = normalize_timestamp(get_first_value(row, df, ["startedAt"]))
        ended_at = normalize_timestamp(get_first_value(row, df, ["endedAt"]))
        engaged_at = normalize_timestamp(get_first_value(row, df, ["firstEngagedAt"]))
        direction = clean_text(get_first_value(row, df, ["direction"]))
        call_type = clean_text(get_first_value(row, df, ["type"]))
        missed_reason = clean_text(get_first_value(row, df, ["missedReason"]))

        data = {
            "meet_key": meet_key,
            "user_chat_id": user_chat_id,
            "source_version": "meet_v2",
            "source_file": path.name,
            "source_sheet": sheet,
            "started_at": started_at,
            "ended_at": ended_at,
            "engaged_at": engaged_at,
            "direction": direction,
            "call_type": call_type,
            "from_number": clean_text(get_first_value(row, df, ["from"])),
            "to_number": clean_text(get_first_value(row, df, ["to"])),
            "primary_number": clean_text(get_first_value(row, df, ["primaryNumber"])),
            "representative_number": clean_text(get_first_value(row, df, ["representativeNumber"])),
            "missed_reason": missed_reason,
            "missed_category": classify_missed_reason(missed_reason, schema_version),
            "duration_sec": clean_number(get_first_value(row, df, ["callDuration"])),
            "queue_time_sec": clean_number(get_first_value(row, df, ["callQueueTime"])),
            "hold_time_sec": clean_number(get_first_value(row, df, ["callHoldTime"])),
            "hold_count": clean_number(get_first_value(row, df, ["holdCount"])),
            "first_waiting_started_at": normalize_timestamp(get_first_value(row, df, ["firstWaitingStartedAt"])),
            "first_ring_started_at": normalize_timestamp(get_first_value(row, df, ["firstRingStartedAt"])),
            "first_ring_ended_at": normalize_timestamp(get_first_value(row, df, ["firstRingEndedAt"])),
            "first_queue_in_at": normalize_timestamp(get_first_value(row, df, ["firstQueueInAt"])),
            "first_queue_out_at": normalize_timestamp(get_first_value(row, df, ["firstQueueOutAt"])),
            "assignee_id": clean_id(get_first_value(row, df, ["callAssigneeId"])),
            "billing_type": clean_text(get_first_value(row, df, ["billingType"])),
        }

    else:
        return None

    direction = clean_text(data["direction"]).lower()
    reason = normalize_missed_reason(data["missed_reason"])

    # 조건 1: is_inbound는 direction만 사용한다. missed/miss는 inbound가 아니다.
    is_inbound = 1 if direction == "inbound" else 0

    # 조건 2/3: answered/missed/response_target은 missed_reason만 사용한다.
    is_answered, is_missed, is_response_target = calculate_standard_meet_flags(reason)

    parts = date_parts(data["started_at"])

    data.update({
        "missed_reason": reason,
        "missed_category": classify_missed_reason(reason, schema_version),
        "is_answered": is_answered,
        "is_missed": is_missed,
        "is_inbound": is_inbound,
        "is_response_target": is_response_target,
        "year": parts["year"],
        "month": parts["month"],
        "week_num": parts["week_num"],
        "week": parts["week"],
        "week_of_month": parts["week_of_month"],
        "week_start_date": parts["week_start_date"],
        "week_end_date": parts["week_end_date"],
        "quarter": parts["quarter"],
        "imported_at": now_text(),
    })

    return data


def upsert_standard_meet(conn, data):
    """
    standard_meet 전용 UPSERT.
    기존 파일 재적재나 수정 반영을 위해 meet_key 기준 INSERT OR REPLACE.
    """
    if not data or not data.get("meet_key"):
        return "skip"

    old = conn.execute(
        "SELECT meet_key FROM standard_meet WHERE meet_key = ?",
        (data["meet_key"],)
    ).fetchone()

    cols = list(data.keys())
    col_sql = ", ".join(f'"{c}"' for c in cols)
    q_sql = ", ".join(["?"] * len(cols))

    conn.execute(
        f'INSERT OR REPLACE INTO standard_meet ({col_sql}) VALUES ({q_sql})',
        [data[c] for c in cols]
    )

    return "update" if old else "insert"


# =========================
# 날짜 계산
# =========================


def to_datetime_safe(value):
    if value is None or pd.isna(value):
        return None
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return None
    return dt.to_pydatetime()


def operational_week_range(value):
    """
    운영주차: 목요일 시작 ~ 다음주 수요일 종료
    """
    dt = to_datetime_safe(value)
    if dt is None:
        return None, None
    days_since_thursday = (dt.weekday() - 3) % 7
    week_start = dt - timedelta(days=days_since_thursday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def report_month_by_weekdays(week_start, week_end):
    """
    운영주차 내 평일(월~금)이 더 많이 포함된 월을 리포트 월로 선택.
    동률이면 운영주 종료일이 속한 월을 우선한다.
    """
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
    """
    평일 다수 월 기준으로 n월 n주 계산.
    """
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


def date_parts(value):
    text = normalize_timestamp(value)
    dt = to_datetime_safe(text)
    if dt is None:
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

    week_start, week_end = operational_week_range(dt)
    report_year, report_month, week_no = week_of_month_by_weekday_majority(week_start, week_end)
    quarter = ((report_month - 1) // 3) + 1
    week_num = int(week_start.isocalendar().week)
    return {
        "year": report_year,
        "week_num": week_num,
        "month": f"{report_year}-{report_month:02d}",
        "week": f"W{week_num:02d}",
        "week_of_month": f"{report_month}월 {week_no}주",
        "week_start_date": week_start.strftime("%Y-%m-%d"),
        "week_end_date": week_end.strftime("%Y-%m-%d"),
        "quarter": f"Q{quarter}",
    
    }

# =========================
# description 파싱
# =========================

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

        # 구매처 / 주문번호 / 출고처
        "mall_name": clean_text(parts[0]) if len(parts) >= 1 else "",
        "order_no": clean_long_id(parts[1]) if len(parts) >= 2 else "",
        "shipment_type": clean_text(parts[2]) if len(parts) >= 3 else "",

        # 송장번호는 CSV/엑셀에서 지수표기 방지를 위해 DB에는 숫자 문자열만 TEXT로 저장
        "invoice_no": clean_long_id(extract_digits(invoice_raw)),
        "customer_issue": extract_block(description, "□ 문의내용 :", labels),
        "cs_action": extract_block(description, "◇ 안내 :", labels),

        # 원문 특이사항 + 품질전달 여부
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


# =========================
# DB 생성/마이그레이션
# =========================

def create_tables(conn):
    conn.execute("""
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

    conn.execute("""
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
        business_date TEXT,
        report_date TEXT,
        is_after_hours INTEGER,
        is_weekend INTEGER,
        operation_status TEXT,
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
        __row_hash TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS userchat_meet (
        id TEXT PRIMARY KEY,
        userChatId TEXT,
        startedAt TEXT,
        endedAt TEXT,
        engagedAt TEXT,
        direction TEXT,
        missedReason TEXT,
        duration TEXT,
        type TEXT,
        __source_file TEXT,
        __source_path TEXT,
        __source_sheet TEXT,
        __file_modified_time TEXT,
        __imported_at TEXT,
        __row_hash TEXT
    )
    """)

    conn.execute("""
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

    conn.execute("""
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

    conn.execute("""
    CREATE TABLE IF NOT EXISTS schema_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sheet_name TEXT,
        schema_version TEXT,
        schema_hash TEXT,
        column_list TEXT,
        first_detected_at TEXT,
        last_detected_at TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS import_schema_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT,
        sheet_name TEXT,
        schema_hash TEXT,
        schema_version TEXT,
        status TEXT,
        imported_at TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS standard_meet (
        meet_key TEXT PRIMARY KEY,
        user_chat_id TEXT,

        source_version TEXT,
        source_file TEXT,
        source_sheet TEXT,

        started_at TEXT,
        ended_at TEXT,
        engaged_at TEXT,

        direction TEXT,
        call_type TEXT,

        from_number TEXT,
        to_number TEXT,
        primary_number TEXT,
        representative_number TEXT,

        missed_reason TEXT,
        missed_category TEXT,

        duration_sec REAL,
        queue_time_sec REAL,
        hold_time_sec REAL,
        hold_count REAL,

        first_waiting_started_at TEXT,
        first_ring_started_at TEXT,
        first_ring_ended_at TEXT,
        first_queue_in_at TEXT,
        first_queue_out_at TEXT,

        assignee_id TEXT,
        billing_type TEXT,

        is_answered INTEGER,
        is_missed INTEGER,
        is_inbound INTEGER,
        is_response_target INTEGER,

        year INTEGER,
        month TEXT,
        week_num INTEGER,
        week TEXT,
        week_of_month TEXT,
        week_start_date TEXT,
        week_end_date TEXT,
        quarter TEXT,

        imported_at TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS import_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_file TEXT,
        source_path TEXT,
        source_sheet TEXT,
        target_table TEXT,
        inserted_count INTEGER,
        updated_count INTEGER,
        skipped_count INTEGER,
        file_modified_time TEXT,
        imported_at TEXT,
        status TEXT,
        message TEXT
    )
    """)


def ensure_column(conn, table, col_name, col_type="TEXT"):
    existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if col_name not in existing:
        conn.execute(f'ALTER TABLE {table} ADD COLUMN "{col_name}" {col_type}')



def sqlite_table_columns(conn, table):
    return conn.execute(f"PRAGMA table_info({table})").fetchall()


def ensure_standard_meet_month_text(conn):
    """기존 DB에서 standard_meet.month가 INTEGER인 경우 TEXT 스키마로 재생성한다.

    SQLite는 테이블 RENAME 시 DB 안에 깨진 VIEW가 하나라도 있으면
    `error in view ...` OperationalError를 발생시킨다. 기존 현장 DB에
    `vw_standard_meet` 같은 구버전/깨진 뷰가 남아 있을 수 있으므로,
    모든 VIEW 정의를 임시 보관 후 DROP → 테이블 재생성 → VIEW 복구 순서로 처리한다.
    fact_voc는 이후 create_fact_voc_view()에서 최신 정의로 다시 생성된다.
    """
    info = sqlite_table_columns(conn, "standard_meet")
    if not info:
        return

    month_info = next((r for r in info if r[1] == "month"), None)
    if month_info is None or str(month_info[2]).upper() == "TEXT":
        return

    existing_cols = [r[1] for r in info]

    saved_views = conn.execute("""
        SELECT name, sql
        FROM sqlite_master
        WHERE type = 'view'
          AND sql IS NOT NULL
    """).fetchall()

    for view_name, _ in saved_views:
        conn.execute(f'DROP VIEW IF EXISTS "{view_name}"')

    conn.execute("ALTER TABLE standard_meet RENAME TO standard_meet__old")

    conn.execute("""
    CREATE TABLE standard_meet (
        meet_key TEXT PRIMARY KEY,
        user_chat_id TEXT,
        source_version TEXT,
        source_file TEXT,
        source_sheet TEXT,
        started_at TEXT,
        ended_at TEXT,
        engaged_at TEXT,
        direction TEXT,
        call_type TEXT,
        from_number TEXT,
        to_number TEXT,
        primary_number TEXT,
        representative_number TEXT,
        missed_reason TEXT,
        missed_category TEXT,
        duration_sec REAL,
        queue_time_sec REAL,
        hold_time_sec REAL,
        hold_count REAL,
        first_waiting_started_at TEXT,
        first_ring_started_at TEXT,
        first_ring_ended_at TEXT,
        first_queue_in_at TEXT,
        first_queue_out_at TEXT,
        assignee_id TEXT,
        billing_type TEXT,
        is_answered INTEGER,
        is_missed INTEGER,
        is_inbound INTEGER,
        is_response_target INTEGER,
        year INTEGER,
        month TEXT,
        week_num INTEGER,
        week TEXT,
        week_of_month TEXT,
        week_start_date TEXT,
        week_end_date TEXT,
        quarter TEXT,
        imported_at TEXT
    )
    """)

    new_cols = [r[1] for r in sqlite_table_columns(conn, "standard_meet")]
    common = [c for c in new_cols if c in existing_cols]
    if common:
        col_sql = ", ".join(f'"{c}"' for c in common)
        select_sql = ", ".join(
            'CAST("month" AS TEXT)' if c == "month" else f'"{c}"'
            for c in common
        )
        conn.execute(
            f'INSERT INTO standard_meet ({col_sql}) '
            f'SELECT {select_sql} FROM standard_meet__old'
        )

    conn.execute("DROP TABLE standard_meet__old")

    for view_name, view_sql in saved_views:
        # fact_voc / vw_standard_meet는 바로 뒤에서 최신 정의로 재생성한다.
        if view_name in ("fact_voc", "vw_standard_meet"):
            continue
        try:
            conn.execute(view_sql)
        except sqlite3.OperationalError as e:
            print(f"[WARN] 기존 VIEW 복구 건너뜀: {view_name} / {e}")

def migrate_tables(conn):
    for col in ["__source_file", "__source_path", "__source_sheet", "__file_modified_time", "__imported_at"]:
        ensure_column(conn, "tag_master", col, "TEXT")

    userchat_cols = {
        "journey": "TEXT",
        "tag_a": "TEXT",
        "tag_b": "TEXT",
        "tag_c": "TEXT",
        "mediumType": "TEXT",
        "ai_status": "TEXT",
        "is_ai_inflow": "INTEGER",
        "is_ai_completed": "INTEGER",
        "is_ai_transferred": "INTEGER",
        "is_non_phone_inbound": "INTEGER",
        "is_ai_handled": "INTEGER",
        "is_agent_handled": "INTEGER",
        "handle_type": "TEXT",
        "business_date": "TEXT",
        "report_date": "TEXT",
        "is_after_hours": "INTEGER",
        "is_weekend": "INTEGER",
        "operation_status": "TEXT",
        "__schema_year": "TEXT",
        "week_start_date": "TEXT",
        "week_end_date": "TEXT",
    }
    for col, col_type in userchat_cols.items():
        ensure_column(conn, "userchat", col, col_type)

    ensure_column(conn, "userchat_description", "shipment_type", "TEXT")
    ensure_column(conn, "userchat_description", "quality_send_yn", "TEXT")
    ensure_standard_meet_month_text(conn)


    # 기존 DB에 standard_meet가 이미 생성되어 있더라도 누락 컬럼이 있으면 자동 보강
    standard_cols = {
        "user_chat_id": "TEXT",
        "source_version": "TEXT",
        "source_file": "TEXT",
        "source_sheet": "TEXT",
        "started_at": "TEXT",
        "ended_at": "TEXT",
        "engaged_at": "TEXT",
        "direction": "TEXT",
        "call_type": "TEXT",
        "from_number": "TEXT",
        "to_number": "TEXT",
        "primary_number": "TEXT",
        "representative_number": "TEXT",
        "missed_reason": "TEXT",
        "missed_category": "TEXT",
        "duration_sec": "REAL",
        "queue_time_sec": "REAL",
        "hold_time_sec": "REAL",
        "hold_count": "REAL",
        "first_waiting_started_at": "TEXT",
        "first_ring_started_at": "TEXT",
        "first_ring_ended_at": "TEXT",
        "first_queue_in_at": "TEXT",
        "first_queue_out_at": "TEXT",
        "assignee_id": "TEXT",
        "billing_type": "TEXT",
        "is_answered": "INTEGER",
        "is_missed": "INTEGER",
        "is_inbound": "INTEGER",
        "is_response_target": "INTEGER",
        "year": "INTEGER",
        "month": "TEXT",
        "week_num": "INTEGER",
        "imported_at": "TEXT",
        "week": "TEXT",
        "week_of_month": "TEXT",
        "week_start_date": "TEXT",
        "week_end_date": "TEXT",
        "quarter": "TEXT",
    }
    
    for col, col_type in standard_cols.items():
        ensure_column(conn, "standard_meet", col, col_type)



def refresh_standard_meet_reason_flags(conn):
    """기존 standard_meet 레코드의 missed_category/is_answered/is_missed/is_response_target을 최신 기준으로 보정한다."""
    existing = {r[1] for r in conn.execute("PRAGMA table_info(standard_meet)").fetchall()}
    required = {
        "meet_key",
        "source_version",
        "missed_reason",
        "missed_category",
        "is_answered",
        "is_missed",
        "is_response_target",
    }
    if not required.issubset(existing):
        return

    rows = conn.execute("""
        SELECT meet_key, source_version, missed_reason, direction
        FROM standard_meet
    """).fetchall()

    for meet_key, source_version, missed_reason, direction in rows:
        schema_version = clean_text(source_version)
        reason = normalize_missed_reason(missed_reason)
        direction_clean = clean_text(direction).lower()

        is_inbound = 1 if direction_clean == "inbound" else 0
        is_answered, is_missed, is_response_target = calculate_standard_meet_flags(reason)

        conn.execute("""
            UPDATE standard_meet
            SET missed_reason = ?,
                missed_category = ?,
                is_answered = ?,
                is_missed = ?,
                is_inbound = ?,
                is_response_target = ?
            WHERE meet_key = ?
        """, (
            reason,
            classify_missed_reason(reason, schema_version),
            is_answered,
            is_missed,
            is_inbound,
            is_response_target,
            meet_key,
        ))

# =========================
# DB 공통 처리# =========================
# DB 공통 처리
# =========================

def is_file_processed(conn, path):
    row = conn.execute("""
        SELECT COUNT(*)
        FROM import_log
        WHERE source_path = ?
          AND file_modified_time = ?
          AND status = 'OK'
    """, (str(path), file_modified_time(path))).fetchone()

    return row[0] > 0


def add_meta(data, path, sheet):
    out = dict(data)
    out["__source_file"] = path.name
    out["__source_path"] = str(path)
    out["__source_sheet"] = sheet
    out["__file_modified_time"] = file_modified_time(path)
    out["__imported_at"] = now_text()
    out["__row_hash"] = row_hash_from_dict(data)
    return out


def upsert(conn, table, data, pk_col):
    pk_value = data[pk_col]

    old = conn.execute(
        f'SELECT __file_modified_time, __row_hash FROM "{table}" WHERE "{pk_col}" = ?',
        (pk_value,)
    ).fetchone()

    cols = list(data.keys())

    if old is None:
        col_sql = ", ".join(f'"{c}"' for c in cols)
        q_sql = ", ".join(["?"] * len(cols))

        conn.execute(
            f'INSERT INTO "{table}" ({col_sql}) VALUES ({q_sql})',
            [data[c] for c in cols]
        )
        return "insert"

    old_mtime, old_hash = old

    if (data.get("__file_modified_time") or "") >= (old_mtime or "") and data.get("__row_hash") != old_hash:
        set_sql = ", ".join(f'"{c}" = ?' for c in cols if c != pk_col)

        conn.execute(
            f'UPDATE "{table}" SET {set_sql} WHERE "{pk_col}" = ?',
            [data[c] for c in cols if c != pk_col] + [pk_value]
        )
        return "update"

    return "skip"




def create_standard_meet_view(conn):
    """Power BI 호환용 vw_standard_meet 뷰를 생성/갱신한다.

    이전 버전의 vw_standard_meet는 missed_reason_rule.version 같은
    현재 DB에 없는 컬럼을 참조해 Power BI 새로 고침 오류를 만들 수 있다.
    standard_meet 테이블 자체에 missed_category/is_missed/is_response_target이
    이미 계산되어 있으므로, 뷰는 standard_meet를 그대로 노출한다.
    """
    conn.execute("DROP VIEW IF EXISTS vw_standard_meet")
    conn.execute("""
    CREATE VIEW vw_standard_meet AS
    SELECT
        s.*
    FROM standard_meet s
    """)

def create_fact_voc_view(conn):
    """Power BI 연결용 fact_voc 뷰를 생성/갱신한다.

    report_date를 기준으로 기존 목요일~수요일 운영주차 규칙을 동일하게 적용한다.
    운영주의 평일 다수 월은 목~수 구조상 그 주의 월요일이 속한 월과 같다.
    """
    conn.execute("DROP VIEW IF EXISTS fact_voc")
    conn.execute("""
    CREATE VIEW fact_voc AS
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

        -- report_date 우선, 없으면 기존 managedAt 날짜로 호환
        p.__basis_date AS date,
        p.__basis_date AS report_date,
        p.business_date,
        p.is_after_hours,
        p.is_weekend,
        p.operation_status,

        -- 기존 원본 컬럼 유지
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

        -- 기존 Power BI에서 사용하던 snake_case/별칭 컬럼 유지
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

        -- 신규 분류 컬럼
        CASE
            WHEN TRIM(COALESCE(p.journey, '')) IN ('배송/수령', '사후관리/클레임', '제품사용')
                THEN '클레임'
            ELSE '단순'
        END AS voc_type,

        CASE
            WHEN LOWER(TRIM(COALESCE(p.mediumName, ''))) = 'phonenumber'
                THEN '콜'
            ELSE '채팅'
        END AS channel_type,

        -- 태그/여정
        p.journey,
        p.tag_a,
        p.tag_b,
        p.tag_c,

        -- 지표
        p.profile_csat,
        p.is_ai_inflow,
        p.is_ai_completed,
        p.is_ai_transferred,
        p.is_non_phone_inbound,
        p.is_ai_handled,
        p.is_agent_handled,
        p.handle_type,

        -- report_date에 기존 목~수/평일다수월 규칙 적용
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

        -- description 파싱 결과
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
def log_import(conn, path, sheet, table, inserted, updated, skipped, status="OK", message=""):
    conn.execute("""
    INSERT INTO import_log (
        source_file,
        source_path,
        source_sheet,
        target_table,
        inserted_count,
        updated_count,
        skipped_count,
        file_modified_time,
        imported_at,
        status,
        message
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        path.name,
        str(path),
        sheet,
        table,
        inserted,
        updated,
        skipped,
        file_modified_time(path),
        now_text(),
        status,
        message
    ))


# =========================
# tag_master
# =========================

def load_tag_master(conn, base):
    path = find_tag_master_file(base)

    if not path:
        print("\n[TAG_MASTER] master/tag_master.xlsx 없음 - 건너뜀")
        return

    df, sheet = read_sheet(path, TAG_MASTER_SHEETS, fallback_first_sheet=True)

    if df is None:
        print(f"\n[TAG_MASTER] 읽기 실패: {path}")
        return

    c_channel = first_col(df, ["channelId", "channel_id", "태그ID", "태그_ID"])
    c_full = first_col(df, ["full_tag", "전체태그", "tag", "tags"])
    c_journey = first_col(df, ["journey", "고객여정", "여정"])
    c_a = first_col(df, ["tag_a", "대분류"])
    c_b = first_col(df, ["tag_b", "중분류"])
    c_c = first_col(df, ["tag_c", "소분류"])

    if not c_full:
        print("[TAG_MASTER] full_tag 또는 전체태그 컬럼 없음")
        print(f"[TAG_MASTER] 현재 컬럼: {list(df.columns)}")
        return

    conn.execute("DELETE FROM tag_master")

    inserted = 0
    t_mtime = file_modified_time(path)
    t_now = now_text()

    for _, row in df.iterrows():
        full_tag = clean_text(get_value(row, c_full))

        if not full_tag:
            continue

        auto = split_tag(full_tag)

        channel_id = clean_id(get_value(row, c_channel)) if c_channel else ""

        if not channel_id:
            channel_id = full_tag

        data = {
            "channelId": channel_id,
            "full_tag": full_tag,
            "journey": clean_text(get_value(row, c_journey)) if c_journey else "",
            "tag_a": clean_text(get_value(row, c_a)) if c_a else auto["tag_a"],
            "tag_b": clean_text(get_value(row, c_b)) if c_b else auto["tag_b"],
            "tag_c": clean_text(get_value(row, c_c)) if c_c else auto["tag_c"],
            "__source_file": path.name,
            "__source_path": str(path),
            "__source_sheet": sheet,
            "__file_modified_time": t_mtime,
            "__imported_at": t_now,
        }

        cols = list(data.keys())
        col_sql = ", ".join(f'"{c}"' for c in cols)
        q_sql = ", ".join(["?"] * len(cols))

        conn.execute(
            f'INSERT OR REPLACE INTO tag_master ({col_sql}) VALUES ({q_sql})',
            [data[c] for c in cols]
        )

        inserted += 1

    log_import(conn, path, sheet, "tag_master", inserted, 0, 0, "OK", "overwrite")
    conn.commit()

    print(f"\n[TAG_MASTER] {path} → tag_master / overwrite {inserted}")


# =========================
# 시트 처리
# =========================

def process_userchat(conn, df, path, sheet):

    # tag_master 로딩
    tag_map = {
        row[0]: {
            "journey": row[1],
            "tag_a": row[2],
            "tag_b": row[3],
            "tag_c": row[4]
        }
        for row in conn.execute("""
            SELECT full_tag, journey, tag_a, tag_b, tag_c
            FROM tag_master
        """)
        if row[0] is not None
    }

    c_id = first_col(df, ["id", "ID"])
    if not c_id:
        return 0, 0, len(df)

    cols = {
        "managedAt": first_col(df, ["managedAt", "createdAt", "openedAt"]),
        "name": first_col(df, ["name"]),
        "description": first_col(df, ["description"]),
        "tags": first_col(df, ["tags"]),
        "direction": first_col(df, ["direction"]),
        "assigneeId": first_col(df, ["assigneeId"]),
        "mediumName": first_col(df, ["mediumName"]),
        "mediumType": first_col(df, ["mediumType", "medium.type", "medium_type"]),
        "mediumSenderName": first_col(df, ["mediumSenderName"]),
        "alfTriggered": first_col(df, ["alfTriggered"]),
        "ai_status": first_col(df, ["ai_status", "aiStatus", "ai.status"]),
        "is_ai_inflow": first_col(df, ["is_ai_inflow", "isAiInflow"]),
        "is_ai_completed": first_col(df, ["is_ai_completed", "isAiCompleted"]),
        "is_ai_transferred": first_col(df, ["is_ai_transferred", "isAiTransferred"]),
        "is_non_phone_inbound": first_col(df, ["is_non_phone_inbound", "isNonPhoneInbound"]),
        "closedAt": first_col(df, ["closedAt"]),
        "profile_csat": first_col(df, ["profile.csat", "profile_csat"]),
    }

    inserted = updated = skipped = 0
    desc_inserted = desc_updated = desc_skipped = 0
    invalid_business_time_count = 0
    schema_year = infer_schema_year(path)

    for _, row in df.iterrows():

        row_id = clean_id(get_value(row, c_id))
        if not row_id:
            skipped += 1
            continue

        # 🔥 핵심 안전 처리
        full_tag = clean_text(get_value(row, cols.get("tags")))

        if not full_tag:
            full_tag = ""

        tag_info = tag_map.get(full_tag, {
            "journey": "",
            "tag_a": "",
            "tag_b": "",
            "tag_c": ""
        })

        raw_managed_at = get_value(row, cols["managedAt"])
        managed_at = normalize_timestamp(raw_managed_at)
        business_fields = calculate_business_fields(raw_managed_at)
        if business_fields["business_date"] is None:
            invalid_business_time_count += 1
            print(
                f"  - [WARN] 운영기준일 계산 실패: file={path.name}, "
                f"sheet={sheet}, id={row_id}, createdAt={clean_text(raw_managed_at)!r}"
            )
        parts = date_parts(managed_at)

        direction = clean_text(get_value(row, cols["direction"])).lower()
        medium_name = clean_text(get_value(row, cols["mediumName"])).lower()
        medium_type = clean_text(get_value(row, cols["mediumType"]))
        medium_type_l = medium_type.lower()
        assignee_id = clean_id(get_value(row, cols["assigneeId"]))
        alf_triggered = clean_text(get_value(row, cols["alfTriggered"]))
        raw_ai_status = clean_text(get_value(row, cols["ai_status"]))

        is_non_phone_inbound = (
            direction == "inbound"
            and medium_name not in ("phonenumber", "phone_number", "phone")
            and medium_type_l not in ("phonenumber", "phone_number", "phone")
        )

        is_ai_handled = is_non_phone_inbound and assignee_id == ""
        is_agent_handled = is_non_phone_inbound and assignee_id != ""
        is_ai_inflow = clean_flag(get_value(row, cols["is_ai_inflow"]), default=None) if cols.get("is_ai_inflow") else int(is_non_phone_inbound)
        is_ai_completed = clean_flag(get_value(row, cols["is_ai_completed"]), default=None) if cols.get("is_ai_completed") else int(is_ai_handled)
        is_ai_transferred = clean_flag(get_value(row, cols["is_ai_transferred"]), default=None) if cols.get("is_ai_transferred") else int(is_agent_handled)
        is_non_phone_inbound_value = clean_flag(get_value(row, cols["is_non_phone_inbound"]), default=None) if cols.get("is_non_phone_inbound") else int(is_non_phone_inbound)

        if raw_ai_status:
            ai_status = raw_ai_status
        elif is_ai_completed:
            ai_status = "completed"
        elif is_ai_transferred:
            ai_status = "transferred"
        elif is_ai_inflow:
            ai_status = "inflow"
        else:
            ai_status = ""

        handle_type = (
            "AI" if is_ai_handled
            else "AGENT" if is_agent_handled
            else "EXCLUDED"
        )

        data = {
            "id": row_id,
            "managedAt": managed_at,
            "name": clean_text(get_value(row, cols["name"])),
            "description": clean_text(get_value(row, cols["description"])),
            "tags": full_tag,
            "journey": tag_info["journey"],
            "tag_a": tag_info["tag_a"],
            "tag_b": tag_info["tag_b"],
            "tag_c": tag_info["tag_c"],

            "direction": clean_text(get_value(row, cols["direction"])),
            "assigneeId": assignee_id,
            "mediumName": clean_text(get_value(row, cols["mediumName"])),
            "mediumType": medium_type,
            "mediumSenderName": clean_text(get_value(row, cols["mediumSenderName"])),
            "alfTriggered": alf_triggered,
            "ai_status": ai_status,
            "closedAt": normalize_timestamp(get_value(row, cols["closedAt"])),
            "profile_csat": clean_number(get_value(row, cols["profile_csat"])),
            **business_fields,

            "is_ai_inflow": int(is_ai_inflow or 0),
            "is_ai_completed": int(is_ai_completed or 0),
            "is_ai_transferred": int(is_ai_transferred or 0),
            "is_non_phone_inbound": int(is_non_phone_inbound_value or 0),
            "is_ai_handled": 1 if is_ai_handled else 0,
            "is_agent_handled": 1 if is_agent_handled else 0,
            "handle_type": handle_type,

            "week_num": parts["week_num"],
            "month": parts["month"],
            "week": parts["week"],
            "week_of_month": parts["week_of_month"],
            "week_start_date": parts["week_start_date"],
            "week_end_date": parts["week_end_date"],
            "quarter": parts["quarter"],
            "__schema_year": schema_year,
        }

        result = upsert(conn, "userchat", add_meta(data, path, sheet), "id")

        if result == "insert":
            inserted += 1
        elif result == "update":
            updated += 1
        else:
            skipped += 1

        desc_data = {
            "id": row_id,
            **parse_description(data["description"])
        }

        desc_result = upsert(conn, "userchat_description", add_meta(desc_data, path, sheet), "id")

        if desc_result == "insert":
            desc_inserted += 1
        elif desc_result == "update":
            desc_updated += 1
        else:
            desc_skipped += 1

    log_import(
        conn,
        path,
        sheet,
        "userchat",
        inserted,
        updated,
        skipped,
        "OK",
        f"schema_year={schema_year}; invalid_business_time={invalid_business_time_count}",
    )
    log_import(conn, path, sheet, "userchat_description", desc_inserted, desc_updated, desc_skipped, "OK", f"schema_year={schema_year}")

    return inserted, updated, skipped



def process_meet(conn, df, path, sheet):
    """
    UserChat meet data 처리.
    - meet_v1 / meet_v2 자동 판별
    - 기존 호환 테이블 userchat_meet 적재
    - 분석용 표준 테이블 standard_meet 적재
    - 새로운 컬럼 구조 발견 시 import_schema_log에 new_schema 기록 후 적재 중단
    """
    schema_version = detect_meet_schema_version(df.columns)
    s_hash, col_list = register_schema_if_needed(conn, sheet, schema_version, df.columns)

    if schema_version == "unknown":
        log_schema_event(
            conn,
            path,
            sheet,
            s_hash,
            schema_version,
            "new_schema",
            f"미등록 meet 시트 구조 / columns={col_list}"
        )
        log_import(
            conn,
            path,
            sheet,
            "standard_meet",
            0,
            0,
            len(df),
            "NEW_SCHEMA",
            "새로운 UserChat meet data 구조 발견 - 매핑 확인 필요"
        )
        print("  - ⚠ 새로운 meet 시트 구조 발견: 적재 중단")
        print(f"  - 컬럼: {col_list}")
        return 0, 0, len(df)

    log_schema_event(conn, path, sheet, s_hash, schema_version, "matched")

    # 기존 호환 테이블 userchat_meet용 매핑
    if schema_version == "meet_v1":
        c_id_candidates = ["id", "ID"]
        c_engaged_candidates = ["engagedAt"]
        c_duration_candidates = ["duration"]
    else:
        c_id_candidates = ["meetId"]
        c_engaged_candidates = ["firstEngagedAt"]
        c_duration_candidates = ["callDuration"]

    c_id = first_col(df, c_id_candidates)
    if not c_id:
        return 0, 0, len(df)

    cols = {
        "userChatId": first_col(df, ["userChatId", "userchatId", "user_chat_id", "UserChatId", "유저챗ID", "유저챗_id"]),
        "startedAt": first_col(df, ["startedAt"]),
        "endedAt": first_col(df, ["endedAt"]),
        "engagedAt": first_col(df, c_engaged_candidates),
        "direction": first_col(df, ["direction"]),
        "missedReason": first_col(df, ["missedReason"]),
        "duration": first_col(df, c_duration_candidates),
        "type": first_col(df, ["type"]),
    }

    legacy_inserted = legacy_updated = legacy_skipped = 0
    std_inserted = std_updated = std_skipped = 0
    missing_userchat_id = 0

    for _, row in df.iterrows():
        row_id = clean_id(get_value(row, c_id))

        if not row_id:
            legacy_skipped += 1
            std_skipped += 1
            continue

        user_chat_id = clean_id(get_value(row, cols["userChatId"]))
        

        if not user_chat_id:
            missing_userchat_id += 1

        # 1) 기존 호환 테이블 유지 적재
        legacy_data = {
            "id": row_id,
            "userChatId": user_chat_id,
            "startedAt": normalize_timestamp(get_value(row, cols["startedAt"])),
            "endedAt": normalize_timestamp(get_value(row, cols["endedAt"])),
            "engagedAt": normalize_timestamp(get_value(row, cols["engagedAt"])),
            "direction": clean_text(get_value(row, cols["direction"])),
            "missedReason": clean_text(get_value(row, cols["missedReason"])),
            "duration": clean_text(get_value(row, cols["duration"])),
            "type": clean_text(get_value(row, cols["type"])),
        }

        result = upsert(conn, "userchat_meet", add_meta(legacy_data, path, sheet), "id")

        if result == "insert":
            legacy_inserted += 1
        elif result == "update":
            legacy_updated += 1
        else:
            legacy_skipped += 1

        # 2) Power BI 분석용 표준 테이블 적재
        std_data = build_standard_meet_row(row, df, schema_version, path, sheet)

        std_result = upsert_standard_meet(conn, std_data)

        if std_result == "insert":
            std_inserted += 1
        elif std_result == "update":
            std_updated += 1
        else:
            std_skipped += 1

    log_import(
        conn,
        path,
        sheet,
        "userchat_meet",
        legacy_inserted,
        legacy_updated,
        legacy_skipped,
        "OK",
        f"schema_version={schema_version}; missing_userChatId={missing_userchat_id}"
    )

    log_import(
        conn,
        path,
        sheet,
        "standard_meet",
        std_inserted,
        std_updated,
        std_skipped,
        "OK",
        f"schema_version={schema_version}; schema_hash={s_hash}; missing_userChatId={missing_userchat_id}"
    )

    if missing_userchat_id > 0:
        print(f"  - userChatId 빈값 {missing_userchat_id}건 확인")

    print(f"  - schema_version={schema_version}")

    return std_inserted, std_updated, std_skipped


def process_manager(conn, df, path, sheet):
    c_id = first_col(df, ["id", "ID"])
    c_name = first_col(df, ["name"])

    if not c_id:
        return 0, 0, len(df)

    inserted = updated = skipped = 0

    for _, row in df.iterrows():
        row_id = clean_id(get_value(row, c_id))

        if not row_id:
            skipped += 1
            continue

        data = {
            "id": row_id,
            "name": clean_text(get_value(row, c_name)),
        }

        result = upsert(conn, "manager", add_meta(data, path, sheet), "id")

        if result == "insert":
            inserted += 1
        elif result == "update":
            updated += 1
        else:
            skipped += 1

    log_import(conn, path, sheet, "manager", inserted, updated, skipped)

    return inserted, updated, skipped


# =========================
# 메인
# =========================

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--base", required=True)
    parser.add_argument("--db", required=True)

    # 추가
    parser.add_argument(
        "--force",
        action="store_true",
        help="import_log 무시하고 전체 재적재"
    )

    args = parser.parse_args()

    base = Path(args.base)
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    files = find_excel_files(base)

    print(f"[INFO] 기준 폴더: {base}")
    print(f"[INFO] 발견한 엑셀 파일 수: {len(files)}")
    print(f"[INFO] DB 경로: {db_path}")

    if args.force:
        print("[WARN] --force 사용 중: import_log를 무시하고 전체 파일을 재적재하므로 오래 걸릴 수 있습니다.")

    conn = sqlite3.connect(db_path)

    # 분석용 DB에서는 FK 강제 OFF
    conn.execute("PRAGMA foreign_keys = OFF")

    # 속도 개선 옵션
    # WAL: 읽기/쓰기 충돌 완화, NORMAL: 디스크 동기화 비용 절감, MEMORY: 임시 작업 메모리 사용
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA cache_size = -200000")

    create_tables(conn)
    migrate_tables(conn)
    refresh_standard_meet_reason_flags(conn)
    create_standard_meet_view(conn)
    create_fact_voc_view(conn)

    # tag_master는 매번 전체 덮어쓰기
    load_tag_master(conn, base)

    total_inserted = total_updated = total_skipped = 0
    file_skipped = 0

    try:
        for path in files:
            print(f"\n[FILE] {path}")

            if not args.force and is_file_processed(conn, path):
                print("  - 이미 처리된 파일입니다. FILE SKIP")
                file_skipped += 1
                continue

            processed_any = False

            df, sheet = read_sheet(path, USERCHAT_SHEETS)
            if df is not None:
                i, u, s = process_userchat(conn, df, path, sheet)
                total_inserted += i
                total_updated += u
                total_skipped += s
                processed_any = True
                print(f"  - {sheet} → userchat / insert {i}, update {u}, skip {s}")

            df_new, sheet_new = read_sheet(path, MEET_SHEETS)
            df_old, sheet_old = read_sheet(path, OLD_MEET_SHEETS)

            meet_dfs = []

            # 신규 시트를 먼저 넣어 중복 시 UserChat meet data 값을 우선한다.
            if df_new is not None and not df_new.dropna(how="all").empty:
                meet_dfs.append((df_new, sheet_new))

            if df_old is not None and not df_old.dropna(how="all").empty:
                meet_dfs.append((df_old, sheet_old))

            if meet_dfs:
                combined = []

                for df_meet, sheet_meet in meet_dfs:
                    temp = df_meet.copy()
                    temp["__origin_sheet"] = sheet_meet
                    combined.append(temp)

                df_meet_all = pd.concat(combined, ignore_index=True, sort=False)

                def get_meet_dedupe_key(row):
                    meet_id = clean_id(row.get("meetId", ""))
                    old_id = clean_id(row.get("id", ""))
                    return meet_id or old_id

                df_meet_all["__meet_dedupe_key"] = df_meet_all.apply(get_meet_dedupe_key, axis=1)
                before_count = len(df_meet_all)

                df_meet_all = df_meet_all[
                    df_meet_all["__meet_dedupe_key"].astype(str).str.strip() != ""
                ].copy()

                df_meet_all = df_meet_all.drop_duplicates(
                    subset=["__meet_dedupe_key"],
                    keep="first"
                )

                duplicated_count = before_count - len(df_meet_all)
                meet_i = meet_u = meet_s = 0

                # concat 후 생긴 타 시트 전용 빈 컬럼은 origin별로 제거해서 schema_version 오판을 막는다.
                for origin_sheet in [sheet_new, sheet_old]:
                    if not origin_sheet:
                        continue
                    part = df_meet_all[df_meet_all["__origin_sheet"] == origin_sheet].copy()
                    if part.empty:
                        continue
                    part = part.drop(columns=["__meet_dedupe_key", "__origin_sheet"], errors="ignore")
                    part = part.dropna(axis=1, how="all")

                    i, u, s = process_meet(conn, part, path, origin_sheet)
                    meet_i += i
                    meet_u += u
                    meet_s += s

                total_inserted += meet_i
                total_updated += meet_u
                total_skipped += meet_s
                processed_any = True

                print(
                    f"  - Old/UserChat meet data 통합 → standard_meet "
                    f"/ insert {meet_i}, update {meet_u}, skip {meet_s}, duplicate_removed {duplicated_count}"
                )

            df, sheet = read_sheet(path, MANAGER_SHEETS)
            if df is not None:
                i, u, s = process_manager(conn, df, path, sheet)
                total_inserted += i
                total_updated += u
                total_skipped += s
                processed_any = True
                print(f"  - {sheet} → manager / insert {i}, update {u}, skip {s}")

            if not processed_any:
                log_import(conn, path, "", "__file__", 0, 0, 0, "NO_TARGET_SHEET", "대상 시트 없음")
                print("  - 대상 시트 없음")

            conn.commit()

        refresh_standard_meet_reason_flags(conn)
        conn.commit()

        print("\n[DONE]")
        print(f"전체 INSERT: {total_inserted}")
        print(f"전체 UPDATE: {total_updated}")
        print(f"전체 ROW SKIP: {total_skipped}")
        print(f"전체 FILE SKIP: {file_skipped}")

    finally:
        conn.commit()
        conn.close()


if __name__ == "__main__":
    main()
