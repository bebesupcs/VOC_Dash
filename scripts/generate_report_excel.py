# -*- coding: utf-8 -*-
"""
generate_report_excel.py
CX팀 VOC 분석 종합 리포트 엑셀 생성기 (오피스 네이티브 차트 + 차트데이터셋 연동)
- Sheet 1: VOC_분석종합리포트 (KPI + 전폭 네이티브 차트 4종 + 소분류 전수 비교 + TOP 5 요약 + CX팀 종합 코멘트)
- Sheet 2: 차트데이터셋 (차트에 연동된 정갈한 원천 피벗/소분류 전수 매트릭스 테이블)
- Sheet 3: 품질raw (채널톡 고유 ID, 실제 배정 상담사 실명, 당기 파스텔 음영, 과거 행 숨김, 1행 틀고정 및 필터)
- Sheet 4: 배송raw (물류센터별 파손/오배송 클레임 전수, 당기 파스텔 음영, 과거 행 숨김, 1행 틀고정 및 필터)
- Sheet 5: 서비스raw (서비스 클레임 전수, 채널/방향/중·소분류/조치내역, 당기 파스텔 음영, 1행 틀고정 및 필터)
- Sheet 6: 클레임사진 (선택 기간 등록된 클레임 사진 전수 수록)
- Sheet 7: 보상내역서 (당기 제품별 보상 집계)
- Sheet 8: 보상내역서_전체 (연간 누적 매트릭스)
"""

import hashlib
import io
import json
import math
import os
import re
import sqlite3
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
try:
    from PIL import Image as PILImage
    from openpyxl.drawing.image import Image as OpenpyxlImage
    HAS_PIL = True
except ImportError:
    PILImage = None
    OpenpyxlImage = None
    HAS_PIL = False

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.chart.axis import ChartLines
from openpyxl.chart.data_source import AxDataSource, StrRef, StrData, StrVal


DATA_JSON_PATH = Path(__file__).resolve().parent.parent / "dashboard" / "data.json"

_VOC_DATA_CACHE = None
_VOC_DATA_MTIME = 0


def load_voc_data():
    global _VOC_DATA_CACHE, _VOC_DATA_MTIME
    if not DATA_JSON_PATH.exists():
        raise FileNotFoundError(f"data.json not found at {DATA_JSON_PATH}")
    curr_mtime = DATA_JSON_PATH.stat().st_mtime
    if _VOC_DATA_CACHE is not None and curr_mtime == _VOC_DATA_MTIME:
        return _VOC_DATA_CACHE
    with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
        _VOC_DATA_CACHE = json.load(f)
        _VOC_DATA_MTIME = curr_mtime
    return _VOC_DATA_CACHE


CLAIM_PHOTOS_BASE = r"X:\9. 클레임 사진\2026"
THUMB_CACHE_DIR = Path(tempfile.gettempdir()) / "voc_photo_thumbs"
THUMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_claim_photo_sort_key(filename):
    label = os.path.splitext(filename)[0]
    parts = label.split("_")
    if len(parts) >= 3:
        cause = "_".join(parts[2:]).strip()
        prod = parts[0].strip()
    elif len(parts) == 2:
        cause = parts[1].strip()
        prod = parts[0].strip()
    else:
        cause = label.strip()
        prod = label.strip()
    return (cause, prod, label)


def find_claim_photo_folder(week_key, voc_data=None):
    """
    단일 주차 키(예: 2026-W41) 또는 특정 날짜에 매칭되는 폴더를 검색.
    매칭되는 폴더가 없으면 (None, None) 반환 (엉뚱한 폴더로 fallback 방지).
    """
    if not os.path.exists(CLAIM_PHOTOS_BASE):
        return None, None
    if voc_data is None:
        voc_data = load_voc_data()
    weeks = voc_data.get("WEEKS", [])

    dirs = [d for d in os.listdir(CLAIM_PHOTOS_BASE) if os.path.isdir(os.path.join(CLAIM_PHOTOS_BASE, d))]

    # 1. 주차 키(2026-W41)로 매칭
    target_w = next((w for w in weeks if w.get("key") == week_key), None)
    if target_w:
        wom = target_w.get("week_of_month", "")
        s_date = target_w.get("week_start_date", "").replace("-", "")[4:]
        e_date = target_w.get("week_end_date", "").replace("-", "")[4:]

        if wom:
            for d in dirs:
                if wom in d:
                    return os.path.join(CLAIM_PHOTOS_BASE, d), d
        if s_date and e_date:
            for d in dirs:
                if s_date in d and e_date in d:
                    return os.path.join(CLAIM_PHOTOS_BASE, d), d

    # 2. week_key 문자열 자체로 검색 (폴더명 직접 매칭)
    if week_key:
        for d in dirs:
            if week_key in d:
                return os.path.join(CLAIM_PHOTOS_BASE, d), d

    return None, None


def get_all_claim_photos_for_period(period_key, voc_data=None):
    """
    주차, 월간, 분기, 연간 단위에 해당하는 모든 사진 파일 목록 및 실제 경로를 반환.
    반환: list of (full_filepath, filename, folder_name)
    """
    if not os.path.exists(CLAIM_PHOTOS_BASE):
        return []
    if voc_data is None:
        voc_data = load_voc_data()

    weeks = voc_data.get("WEEKS", [])
    months = voc_data.get("MONTHS", [])

    period_str = str(period_key).strip() if period_key else ""
    dirs = [d for d in os.listdir(CLAIM_PHOTOS_BASE) if os.path.isdir(os.path.join(CLAIM_PHOTOS_BASE, d))]

    target_folders = []

    # 1. 연간 단위 (예: '2026', '2025', '연간')
    if period_str in ["2026", "2025", "2027", "연간"] or (len(period_str) == 4 and period_str.isdigit()):
        target_folders = [d for d in dirs if "주차" in d]
        target_folders.sort()

    # 2. 분기 단위 (예: '2026-Q1', '2026-Q2', '2026-Q3', '2026-Q4')
    elif "-Q" in period_str or (len(period_str) == 2 and period_str.startswith("Q")):
        q_num = period_str.split("Q")[-1].strip()
        q_map = {
            "1": [1, 2, 3],
            "2": [4, 5, 6],
            "3": [7, 8, 9],
            "4": [10, 11, 12]
        }
        for m in q_map.get(q_num, []):
            m_flds = [d for d in dirs if re.match(rf"^{m}월\b", d)]
            m_flds.sort()
            target_folders.extend(m_flds)

    # 3. 월간 단위 (예: '2026-10', '10월')
    elif (("-" in period_str and len(period_str) == 7 and "W" not in period_str) or 
          any(m.get("key") == period_str for m in months) or 
          period_str.endswith("월")):
        target_m_num = None
        if "-" in period_str:
            try:
                target_m_num = int(period_str.split("-")[1].lstrip("0"))
            except Exception:
                pass
        elif "월" in period_str:
            num_part = re.sub(r"[^\d]", "", period_str)
            if num_part:
                target_m_num = int(num_part)
        else:
            m_obj = next((m for m in months if m.get("key") == period_str), None)
            if m_obj and "-" in m_obj.get("key", ""):
                try:
                    target_m_num = int(m_obj["key"].split("-")[1].lstrip("0"))
                except Exception:
                    pass

        if target_m_num is not None:
            target_folders = [d for d in dirs if re.match(rf"^{target_m_num}월\b", d)]
            target_folders.sort()

    # 4. 주차 단위 (예: '2026-W41')
    else:
        f_path, f_name = find_claim_photo_folder(period_str, voc_data)
        if f_name:
            target_folders = [f_name]

    collected = []
    for fld in target_folders:
        full_dir = os.path.join(CLAIM_PHOTOS_BASE, fld)
        if not os.path.exists(full_dir):
            continue
        files = [
            f for f in os.listdir(full_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
            and not f.startswith("Thumbs")
            and not f.endswith(".TMP")
        ]
        files.sort(key=get_claim_photo_sort_key)
        for fn in files:
            collected.append((os.path.join(full_dir, fn), fn, fld))

    return collected


def get_claim_photos_for_period(period_key):
    """
    주차, 월간, 분기, 연간 기간에 맞춰 클레임 사진 JSON 객체 반환.
    """
    items = get_all_claim_photos_for_period(period_key)
    from urllib.parse import quote
    photos = []
    folders_set = []

    for full_path, fn, fld in items:
        if fld not in folders_set:
            folders_set.append(fld)
        label = os.path.splitext(fn)[0]
        photos.append({
            "filename": fn,
            "folder": fld,
            "label": label,
            "thumb_url": f"/api/claim_photos/image?folder={quote(fld)}&file={quote(fn)}&thumb=1",
            "url": f"/api/claim_photos/image?folder={quote(fld)}&file={quote(fn)}"
        })

    return {
        "period": str(period_key),
        "folders": folders_set,
        "total": len(photos),
        "photos": photos
    }


def get_claim_photos_for_week(week_key):
    """하위 호환성 유지용 alias"""
    return get_claim_photos_for_period(week_key)


def read_claim_photo_bytes(folder_name, file_name, is_thumb=False):
    if not folder_name or not file_name:
        return None, None
    safe_folder = os.path.basename(folder_name)
    safe_file = os.path.basename(file_name)
    full_path = os.path.join(CLAIM_PHOTOS_BASE, safe_folder, safe_file)
    if not os.path.exists(full_path):
        return None, None

    if is_thumb and PILImage is not None:
        try:
            mtime = int(os.path.getmtime(full_path))
            cache_key = hashlib.md5(f"{safe_folder}_{safe_file}".encode("utf-8")).hexdigest()
            cache_file = THUMB_CACHE_DIR / f"{cache_key}_{mtime}.jpg"
            if cache_file.exists():
                with open(cache_file, "rb") as cf:
                    return cf.read(), "image/jpeg"

            with PILImage.open(full_path) as im:
                try:
                    im.draft("RGB", (320, 320))
                except Exception:
                    pass
                im = im.convert("RGB")
                im.thumbnail((260, 260), PILImage.Resampling.BOX)
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=75)
                thumb_bytes = buf.getvalue()
                try:
                    with open(cache_file, "wb") as cf:
                        cf.write(thumb_bytes)
                except Exception:
                    pass
                return thumb_bytes, "image/jpeg"
        except Exception as e:
            print("Thumbnail generate warning, fallback to full image:", e)

    ext = os.path.splitext(safe_file)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    with open(full_path, "rb") as fh:
        return fh.read(), mime


def get_sqlite_conn():
    candidates = [
        os.path.join(tempfile.gettempdir(), "channeltalk_voc_local.db"),
        r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db",
    ]
    for p in candidates:
        if os.path.exists(p) and os.path.getsize(p) > 1000000:
            try:
                conn = sqlite3.connect(p)
                return conn
            except Exception:
                pass
    return None


def is_qc_chat(c):
    if not c or not c.get("valid"):
        return False
    if c.get("sub") == "재통화":
        return False
    return c.get("journey") == "제품사용"


def is_delivery_chat(c):
    if not c or not c.get("valid"):
        return False
    return (
        c.get("channel") == "배송접수"
        or c.get("journey") in ("배송/수령", "구매/배송")
        or c.get("mid") == "배송"
        or str(c.get("brand") or "").startswith("배송")
        or "배송" in str(c.get("tag") or "")
    )


def is_svc_chat(c):
    if not c or not c.get("valid") or c.get("nature") != "클레임":
        return False
    if is_qc_chat(c) or is_delivery_chat(c):
        return False
    return c.get("journey") == "사후관리/클레임" or (c.get("sub") != "재통화" and not c.get("is_repeat"))


def format_insight_text(insight_val, default_text):
    """
    대시보드에서 전달되는 다양한 형태의 인사이트 데이터를 안전하게 문자열로 변환.
    - 문자열인 경우 그대로 활용 (필요시 머리말 보정)
    - 리스트 형태(UI v2 모델: [{text, author, date}, ...])인 경우 텍스트를 추출하여 줄바꿈으로 연결
    - 딕셔너리인 경우 텍스트 및 작성자 메타데이터 추출
    - 비어있을 경우 default_text 반환
    """
    if not insight_val:
        return default_text
    if isinstance(insight_val, str) and insight_val.strip():
        txt = insight_val.strip()
        if not txt.startswith("📌"):
            txt = f"📌 [이슈 코멘트 & 액션 플랜] {txt}"
        return txt
    if isinstance(insight_val, list) and len(insight_val) > 0:
        lines = []
        for item in insight_val:
            if isinstance(item, dict):
                t = item.get("text") or item.get("content") or ""
                a = item.get("author") or item.get("user") or ""
                d = item.get("date") or item.get("created_at") or ""
                meta = f" ({a} | {d})" if a or d else ""
                if t:
                    lines.append(f"📌 [이슈 코멘트 & 액션 플랜] {t}{meta}")
            elif isinstance(item, str) and item.strip():
                lines.append(f"📌 [이슈 코멘트 & 액션 플랜] {item.strip()}")
        if lines:
            return "\n".join(lines)
    if isinstance(insight_val, dict):
        t = insight_val.get("text") or insight_val.get("content") or ""
        a = insight_val.get("author") or insight_val.get("user") or ""
        d = insight_val.get("date") or insight_val.get("created_at") or ""
        meta = f" ({a} | {d})" if a or d else ""
        if t:
            return f"📌 [이슈 코멘트 & 액션 플랜] {t}{meta}"
    return default_text


def calc_comment_box_height(text, char_limit=58, line_height=20, min_height=45, padding=16):
    """
    엑셀 병합 셀에서 텍스트 줄바꿈 시 글자가 잘리지 않도록 행 높이를 정밀 계산.
    - 한글(전각) 2단위, 영문/숫자(반각) 1단위 가중치 반영
    - 문단별 래핑 줄 수와 전체 시각적 줄 수 합산하여 넉넉한 상하 패딩 확보
    """
    if not text:
        return min_height
    total_lines = 0
    for para in str(text).splitlines():
        if not para.strip():
            total_lines += 1
            continue
        w = sum(2 if ord(c) > 127 else 1 for c in para)
        lines = max(1, math.ceil(w / (char_limit * 2)))
        total_lines += lines
    return max(min_height, total_lines * line_height + padding)


def load_clean_quality_raw(cur_week, voc_data):
    """
    voc_data의 CHATS_BY_WEEK에서 고객여정 '제품사용' 기준 품질 클레임 건 추출.
    - 웹 대시보드(render.js, engine.js)와 100% 동일한 데이터 및 건수 보장
    - compensation_overrides.json 수기 제외/추가 완벽 반영
    """
    override_file = os.path.join(os.path.dirname(__file__), "..", "dashboard", "compensation_overrides.json")
    excluded_ids = set()
    excluded_reasons_map = {}
    manual_additions = []
    if os.path.exists(override_file):
        try:
            with open(override_file, "r", encoding="utf-8") as f:
                ov_data = json.load(f)
                excluded_ids = set(str(x) for x in ov_data.get("excluded_ids", []))
                excluded_reasons_map = ov_data.get("excluded_reasons", {})
                manual_additions = ov_data.get("manual_additions", [])
        except Exception as e:
            print("Warning: failed to load compensation_overrides.json:", e)

    weeks = voc_data.get("WEEKS", [])
    week_map = {w["key"]: w for w in weeks}

    raw_records = []
    chats_by_week = voc_data.get("CHATS_BY_WEEK", {})

    for wk_key, clist in chats_by_week.items():
        w_obj = week_map.get(wk_key, {})
        for c in clist:
            if not is_qc_chat(c):
                continue
            cid = str(c.get("id") or "")
            sp_note = str(c.get("note") or "").strip()
            is_manual_excluded = (cid in excluded_ids) or ("제외" in sp_note) or ("미신청" in sp_note)
            is_comp = not is_manual_excluded
            ex_reason = ""
            if is_manual_excluded:
                ex_obj = excluded_reasons_map.get(cid)
                if isinstance(ex_obj, dict):
                    ex_reason = ex_obj.get("reason", "관리자 수기 제외")
                elif isinstance(ex_obj, str):
                    ex_reason = ex_obj
                elif "제외" in sp_note or "미신청" in sp_note:
                    ex_reason = f"특이사항 메모 ({sp_note})"
                else:
                    ex_reason = "관리자 수기 제외"

            raw_mgr = str(c.get("agent") or "AI")
            clean_mgr = re.sub(r'[\U00010000-\U0010ffff]', '', raw_mgr).replace("CX_", "").replace("CX", "").strip() or "AI"
            cust_val = c.get("custName") or c.get("cust") or "고객"

            date_str = c.get("date") or ""
            if not date_str and c.get("time"):
                date_str = str(c.get("time"))[:10]
            if not date_str:
                date_str = w_obj.get("week_start_date", "")

            wom = w_obj.get("week_of_month") or c.get("week_of_month", "")
            w_match = re.search(r'(\d+)주', wom)
            w_str = f"{w_match.group(1)}주" if w_match else "1주"
            raw_m = str(w_obj.get("month") or c.get("month") or "10월")
            if "-" in raw_m and len(raw_m) == 7:
                m_str = f"{int(raw_m.split('-')[1])}월"
            elif raw_m.isdigit():
                m_str = f"{int(raw_m)}월"
            else:
                m_str = raw_m
            mw = wom if wom else f"{m_str} {w_str}"

            raw_q = str(w_obj.get("quarter") or c.get("quarter") or "4분기")
            q_str = f"{raw_q}분기" if ("분기" not in raw_q and raw_q.isdigit()) else raw_q

            # Compute report month based on actual inflow time
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
            })

    # 수기 추가(manual_additions) 보상 건 병합
    if manual_additions:
        for m_item in manual_additions:
            m_wk = m_item.get("weekKey", cur_week.get("key", "2026-W41"))
            raw_records.append({
                "year": m_item.get("year", cur_week.get("year", "2026")),
                "quarter": m_item.get("quarter", cur_week.get("quarter", "4분기")),
                "month": m_item.get("month", "10월"),
                "week": m_item.get("week", "2주"),
                "mw": m_item.get("mw", "10월 2주"),
                "id": m_item.get("id", "manual_comp"),
                "cust": m_item.get("cust", "수기등록고객"),
                "date": m_item.get("date", cur_week.get("week_start_date", "")),
                "mgr": m_item.get("mgr", "관리자"),
                "tagA": m_item.get("tagA", "물티슈"),
                "tagB": m_item.get("tagB", "품질"),
                "tagC": m_item.get("tagC", "수기보상"),
                "prod": m_item.get("prod", "기타"),
                "mfg": m_item.get("mfg", "-"),
                "issue": m_item.get("issue", "수기 추가 보상 건"),
                "journey": "제품사용(수기)",
                "qualitySend": "O",
                "isComp": True,
                "compMonth": "O",
                "compAll": "O",
                "mall": m_item.get("mall", "-"),
                "orderNo": m_item.get("orderNo", "-"),
                "shipmentType": "-", "invoice": "-",
                "weekKey": m_wk
            })

    return raw_records


def load_clean_service_raw(cur_week, voc_data):
    """
    voc_data의 CHATS_BY_WEEK에서 서비스 클레임 전수 추출.
    - 웹 대시보드 및 리포트 집계와 100% 동일한 기준 적용
    """
    weeks = voc_data.get("WEEKS", [])
    week_map = {w["key"]: w for w in weeks}

    raw_records = []
    chats_by_week = voc_data.get("CHATS_BY_WEEK", {})

    for wk_key, clist in chats_by_week.items():
        w_obj = week_map.get(wk_key, {})
        for c in clist:
            if not is_svc_chat(c):
                continue
            cid = str(c.get("id") or "")
            raw_mgr = str(c.get("agent") or "AI")
            clean_mgr = re.sub(r'[\U00010000-\U0010ffff]', '', raw_mgr).replace("CX_", "").replace("CX", "").strip() or "AI"
            cust_val = c.get("custName") or c.get("cust") or "고객"

            date_str = c.get("date") or ""
            if not date_str and c.get("time"):
                date_str = str(c.get("time"))[:10]
            if not date_str:
                date_str = w_obj.get("week_start_date", "")

            wom = w_obj.get("week_of_month") or c.get("week_of_month", "")
            w_match = re.search(r'(\d+)주', wom)
            w_str = f"{w_match.group(1)}주" if w_match else "1주"
            raw_m = str(w_obj.get("month") or c.get("month") or "10월")
            if "-" in raw_m and len(raw_m) == 7:
                m_str = f"{int(raw_m.split('-')[1])}월"
            elif raw_m.isdigit():
                m_str = f"{int(raw_m)}월"
            else:
                m_str = raw_m
            mw = wom if wom else f"{m_str} {w_str}"

            raw_q = str(w_obj.get("quarter") or c.get("quarter") or "4분기")
            q_str = f"{raw_q}분기" if ("분기" not in raw_q and raw_q.isdigit()) else raw_q

            channel_str = c.get("channel") or "채팅"
            raw_dir = c.get("direction") or ""
            if raw_dir in ("INBOUND", "인바운드"):
                direction_str = "인바운드"
            elif raw_dir in ("OUTBOUND", "아웃바운드"):
                direction_str = "아웃바운드"
            else:
                direction_str = "아웃바운드" if "발신" in channel_str else "인바운드"

            raw_records.append({
                "year": str(w_obj.get("year") or c.get("year") or "2026"),
                "quarter": q_str,
                "month": m_str,
                "week": w_str,
                "mw": mw,
                "id": cid,
                "cust": cust_val,
                "date": date_str,
                "mgr": clean_mgr,
                "channel": channel_str,
                "direction": direction_str,
                "tagB": c.get("mid") or "",
                "tagC": c.get("sub") or "",
                "prod": c.get("prod") or "",
                "issue": c.get("issue") or "",
                "act": c.get("act") or c.get("action") or "",
                "mall": c.get("mall") or "",
                "time": c.get("time") or "",
                "weekKey": wk_key
            })

    return raw_records


def build_report_excel(target_period_key=None, memos=None, insights=None):
    voc_data = load_voc_data()
    weeks = voc_data.get("WEEKS", [])
    quarters = voc_data.get("QUARTERS", [])
    years = voc_data.get("YEARS", [])
    months = voc_data.get("MONTHS", [])
    if not weeks:
        raise ValueError("No WEEKS metadata in voc_data")

    # 기간 유형 판별 (주간 / 월간 / 분기 / 연간)
    is_month = False
    is_quarter = False
    is_year = False
    is_week = False
    
    if target_period_key:
        if "-Q" in str(target_period_key) or any(q["key"] == target_period_key for q in quarters):
            is_quarter = True
        elif (len(str(target_period_key)) == 4 and str(target_period_key).isdigit()) or any(y["key"] == target_period_key for y in years):
            is_year = True
        elif any(m["key"] == target_period_key for m in months) or (len(str(target_period_key)) == 7 and "-" in str(target_period_key) and str(target_period_key).split("-")[1].isdigit()):
            is_month = True
        else:
            is_week = True
    else:
        is_week = True

    # 기간 객체, 이전 기간, 대상 주차군(target_week_keys), 추이 기간군(trend_periods) 산출
    period_obj = None
    prev_period_obj = None
    trend_periods = []
    target_week_keys = set()
    prev_week_keys = set()

    if is_quarter:
        q_idx = next((i for i, q in enumerate(quarters) if q["key"] == target_period_key), -1)
        if q_idx == -1 and quarters:
            q_idx = len(quarters) - 1
        period_obj = quarters[q_idx] if q_idx != -1 else None
        prev_period_obj = quarters[q_idx - 1] if q_idx > 0 else None
        target_week_keys = set(period_obj.get("weekKeys", [])) if period_obj else set()
        prev_week_keys = set(prev_period_obj.get("weekKeys", [])) if prev_period_obj else set()
        trend_periods = quarters[max(0, q_idx - 3):q_idx + 1] if q_idx != -1 else []
        year_str = target_period_key.split("-")[0] if "-" in target_period_key else "2026"
        q_name = target_period_key.split("-")[1] if "-" in target_period_key else "4분기"
        period_disp = f"{year_str}년 {q_name} (분기 요약)"
        period_badge = f"{q_name} 분기"
        date_range = f"{year_str}년 {q_name} 전체"

    elif is_year:
        year_str = str(target_period_key) if target_period_key else "2026"
        y_idx = next((i for i, y in enumerate(years) if str(y["key"]) == year_str), -1)
        if y_idx == -1 and years:
            y_idx = len(years) - 1
        period_obj = years[y_idx] if y_idx != -1 else None
        prev_period_obj = years[y_idx - 1] if y_idx > 0 else None
        target_week_keys = set(period_obj.get("weekKeys", [])) if period_obj else set()
        prev_week_keys = set(prev_period_obj.get("weekKeys", [])) if prev_period_obj else set()
        trend_periods = years[max(0, y_idx - 3):y_idx + 1] if y_idx != -1 else []
        period_disp = f"{year_str}년 (연간 요약)"
        period_badge = f"{year_str}년 연간"
        date_range = f"{year_str}년 전체"

    elif is_month:
        m_idx = next((i for i, m in enumerate(months) if m["key"] == target_period_key), -1)
        if m_idx == -1 and months:
            m_idx = len(months) - 1
        period_obj = months[m_idx] if m_idx != -1 else None
        prev_period_obj = months[m_idx - 1] if m_idx > 0 else None
        target_week_keys = set(period_obj.get("weekKeys", [])) if period_obj else set()
        prev_week_keys = set(prev_period_obj.get("weekKeys", [])) if prev_period_obj else set()
        trend_periods = months[max(0, m_idx - 3):m_idx + 1] if m_idx != -1 else []
        m_num = target_period_key.split("-")[1].lstrip("0") if (target_period_key and "-" in str(target_period_key)) else "10"
        year_str = target_period_key.split("-")[0] if (target_period_key and "-" in str(target_period_key)) else "2026"
        period_disp = f"{year_str}년 {m_num}월 (월간)"
        period_badge = f"{m_num}월 월간"
        date_range = f"{year_str}-{m_num.zfill(2)}월 전체"

    else: # is_week
        w_idx = next((i for i, w in enumerate(weeks) if w["key"] == target_period_key), -1)
        if w_idx == -1:
            w41_idx = next((i for i, w in enumerate(weeks) if w["key"] == "2026-W41"), -1)
            w_idx = w41_idx if w41_idx != -1 else len(weeks) - 1
        period_obj = weeks[w_idx]
        prev_period_obj = weeks[w_idx - 1] if w_idx > 0 else None
        target_week_keys = {period_obj["key"]}
        prev_week_keys = {prev_period_obj["key"]} if prev_period_obj else set()
        trend_periods = weeks[max(0, w_idx - 3):w_idx + 1]
        year_str = str(period_obj.get("year", "2026"))
        w_lbl = period_obj.get("week_of_month") or period_obj["key"]
        period_disp = f"{year_str}년 {w_lbl} (주간)"
        period_badge = f"{w_lbl} 주간"
        date_range = period_obj.get("label", "").replace("2026년 ", "").replace("2025년 ", "")

    # 기준 대표 주차(cur_week) 및 인덱스(p_idx) 설정
    cur_week = None
    if is_week:
        cur_week = period_obj
    else:
        for wk_key in reversed(list(target_week_keys)):
            wk_cand = next((w for w in weeks if w["key"] == wk_key), None)
            if wk_cand:
                cur_week = wk_cand
                break
    if not cur_week:
        cur_week = weeks[-1]
    p_idx = next((i for i, w in enumerate(weeks) if w["key"] == cur_week["key"]), len(weeks) - 1)

    def get_period_label(p):
        if is_month:
            return (p.get("label") or p.get("key") or "").replace("2026년 ", "").replace("2025년 ", "")
        elif is_quarter:
            return (p.get("label") or p.get("key") or "").replace("2026년 ", "").replace("2025년 ", "")
        elif is_year:
            return f"{p.get('key')}년"
        else:
            return p.get("week_of_month") or p.get("key")

    recent_labels = [get_period_label(p) for p in trend_periods]
    legend_w_labels = [lbl + (" (현재)" if i == len(recent_labels) - 1 else "") for i, lbl in enumerate(recent_labels)]

    wb = openpyxl.Workbook()

    # -------------------------------------------------------------
    # 스타일 공통 정의
    # -------------------------------------------------------------
    font_title = Font(name="맑은 고딕", size=15, bold=True, color="0F766E")
    font_sec = Font(name="맑은 고딕", size=11, bold=True, color="111827")
    font_tbl_h = Font(name="맑은 고딕", size=9.5, bold=True, color="FFFFFF")
    font_regular = Font(name="맑은 고딕", size=9.5, color="1F2937")
    font_bold = Font(name="맑은 고딕", size=9.5, bold=True, color="1F2937")
    font_muted = Font(name="맑은 고딕", size=8.5, color="6B7280")
    font_meta = Font(name="맑은 고딕", size=9.5, color="4B5563")

    fill_teal_header = PatternFill(fill_type="solid", fgColor="0F766E")
    fill_slate_header = PatternFill(fill_type="solid", fgColor="475569")
    fill_total = PatternFill(fill_type="solid", fgColor="F1F5F9")
    fill_zebra = PatternFill(fill_type="solid", fgColor="F8FAFC")
    fill_banner = PatternFill(fill_type="solid", fgColor="F0FDFA")
    fill_amber_banner = PatternFill(fill_type="solid", fgColor="FEF3C7")
    fill_rose_banner = PatternFill(fill_type="solid", fgColor="FFE4E6")
    fill_teal_banner = PatternFill(fill_type="solid", fgColor="CCFBF1")
    fill_pastel_orange = PatternFill(fill_type="solid", fgColor="FFF3D6")

    thin_side = Side(style="thin", color="D4D4D4")
    border_thin = Border(top=thin_side, left=thin_side, bottom=thin_side, right=thin_side)
    border_double_bottom = Border(top=thin_side, left=thin_side, bottom=Side(style="double", color="0F766E"), right=thin_side)

    def apply_box(ws, start_r, start_c, end_r, end_c, fill=None, border=None):
        for r in range(start_r, end_r + 1):
            for c in range(start_c, end_c + 1):
                cell = ws.cell(row=r, column=c)
                if fill: cell.fill = fill
                if border: cell.border = border

    def make_pillar_chart(min_row, max_row, colors, y_unit=5, y_max=None):
        """
        사용자 요구사항 반영 클러스터 기둥 차트:
        - 가로 전폭 (28.5cm: A~F열 여백 없이 꽉 채움)
        - 세로 슬림화 (7.5cm: 컴팩트한 비주얼)
        - 눈금선: 3~4개 선 유지 (과도한 눈금 배제)
        """
        c = BarChart()
        c.type = "col"
        c.grouping = "clustered"
        c.overlap = 0
        c.gapWidth = 120
        c.width = 28.5
        c.height = 7.5
        c.title = None
        c.legend.position = "t"
        c.legend.legendPos = "t"
        c.roundedCorners = False
        c.visible_cells_only = False

        c.graphical_properties = GraphicalProperties()
        c.graphical_properties.line = LineProperties(noFill=True)

        c.x_axis.delete = False
        c.y_axis.delete = False
        c.x_axis.axPos = "b"
        c.x_axis.tickLblPos = "nextTo"
        c.y_axis.axPos = "l"
        c.y_axis.tickLblPos = "nextTo"
        c.x_axis.title = None
        c.y_axis.title = None

        c.y_axis.scaling.min = 0
        if y_unit: c.y_axis.majorUnit = y_unit
        if y_max: c.y_axis.scaling.max = y_max

        grid_line = LineProperties(solidFill="F1F5F9", w=9525)
        c.y_axis.majorGridlines = ChartLines()
        c.y_axis.majorGridlines.spPr = GraphicalProperties(ln=grid_line)
        c.x_axis.majorGridlines = None
        c.x_axis.line = LineProperties(solidFill="CBD5E1", w=12700)
        c.y_axis.line = LineProperties(noFill=True)
        c.y_axis.majorTickMark = "none"
        c.x_axis.majorTickMark = "none"

        data_ref = Reference(ws_data, min_col=2, min_row=min_row, max_col=1 + len(trend_periods), max_row=max_row)
        c.add_data(data_ref, titles_from_data=True, from_rows=False)

        cats_ref = Reference(ws_data, min_col=1, min_row=min_row + 1, max_col=1, max_row=max_row)
        c.set_categories(cats_ref)

        types_list = [ws_data.cell(row=r, column=1).value for r in range(min_row + 1, max_row + 1)]
        sc = StrData(ptCount=len(types_list), pt=[StrVal(idx=i, v=str(t)) for i, t in enumerate(types_list)])
        str_f = f"'차트데이터셋'!$A${min_row+1}:$A${max_row}"
        for s in c.series:
            s.cat = AxDataSource(strRef=StrRef(f=str_f, strCache=sc))

        for i, s in enumerate(c.series):
            s.graphicalProperties.solidFill = colors[i % len(colors)]
            s.graphicalProperties.line = LineProperties(noFill=True)

        c.dataLabels = DataLabelList()
        c.dataLabels.showVal = True
        c.dataLabels.showCatName = False
        c.dataLabels.showSerName = False
        c.dataLabels.showPercent = False
        c.dataLabels.showLegendKey = False
        c.dataLabels.position = "outEnd"

        return c

    # =============================================================
    # [Sheet 1: VOC_분석종합리포트 기본 레이아웃]
    # =============================================================
    ws_rep = wb.active
    ws_rep.title = "VOC_분석종합리포트"
    ws_rep.views.sheetView[0].showGridLines = True

    # 컬럼 너비 설정 (A~F열: 여백 줄이고 눈에 잘 띄도록 가독성 최적화)
    col_widths = {"A": 10, "B": 28, "C": 15, "D": 22, "E": 16, "F": 28}
    for col_letter, width in col_widths.items():
        ws_rep.column_dimensions[col_letter].width = width

    ws_rep.row_dimensions[1].height = 12

    # Title Banner (A2:F2)
    ws_rep.merge_cells("A2:F2")
    ws_rep.row_dimensions[2].height = 38
    apply_box(ws_rep, 2, 1, 2, 6, fill_banner, border_double_bottom)
    t_cell = ws_rep.cell(row=2, column=1)
    t_cell.value = f"[CX팀] VOC 분석 종합 리포트 ({period_disp})"
    t_cell.font = font_title
    t_cell.alignment = Alignment(vertical="center", horizontal="center")

    ws_rep.row_dimensions[3].height = 8

    # Metadata (Row 4-6)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws_rep.cell(row=4, column=1, value=f"● 분석 대상 기간 : {period_disp} ({date_range})").font = font_meta
    ws_rep.cell(row=5, column=1, value="● 데이터 연동 기준 : 채널톡 채팅 / CTI 전화 / 자사몰 및 스토어 게시판 전수 (작성부서: CX팀)").font = font_meta
    ws_rep.cell(row=6, column=1, value=f"● 보고서 추출 일시 : {now_str}").font = font_meta
    for r in range(4, 7):
        ws_rep.row_dimensions[r].height = 18

    # =============================================================
    # [데이터 집계: 기간 추이 & 소분류 전수 매트릭스 구축]
    # =============================================================
    raw_summary = voc_data.get("RAW_SUMMARY", {})
    all_chats_flat = [c for clist in voc_data.get("CHATS_BY_WEEK", {}).values() for c in clist]
    all_cti_flat = [c for clist in voc_data.get("CTI_BY_WEEK", {}).values() for c in clist]
    all_ships_flat = [s for slist in voc_data.get("SHIPMENTS_BY_WEEK", {}).values() for s in slist]

    def get_chats_for_p(p):
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
        return []
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
        return []
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
        return voc_data.get("CHATS_BY_WEEK", {}).get(pk, [])

    def get_cti_for_p(p):
        if not p: return []
        pk = str(p.get("key", ""))
        if is_week:
            return voc_data.get("CTI_BY_WEEK", {}).get(pk, [])
        if "-" in pk and len(pk) == 7 and "W" not in pk and "-Q" not in pk:
            return [c for c in all_cti_flat if c.get("time") and str(c.get("time")).startswith(pk)]
        if "-Q" in pk:
            y, q = pk.split("-Q")
            qm = [f"{y}-{str((int(q)-1)*3 + i).zfill(2)}" for i in [1, 2, 3]]
            return [c for c in all_cti_flat if any(c.get("time") and str(c.get("time")).startswith(m) for m in qm)]
        if len(pk) == 4 and pk.isdigit():
            return [c for c in all_cti_flat if c.get("time") and str(c.get("time")).startswith(pk)]
        return voc_data.get("CTI_BY_WEEK", {}).get(pk, [])

    def is_item_in_p(item, p):
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
        return False
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
        return False
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
        return item.get("weekKey") in p.get("weekKeys", []) or item.get("week") in p.get("weekKeys", [])

    def get_channel_metrics_for_p(p):
        if not p: return 0, 0, 0, 0
        pk = str(p.get("key", ""))
        is_w = "W" in pk
        if is_w:
            rs = raw_summary.get(pk)
            if rs:
                c = rs.get("raw_call", 0)
                ch = rs.get("raw_chat", 0)
                b = rs.get("raw_board", 0)
                return c, ch, b, rs.get("total_offered_raw", c + ch + b)
        p_c = get_chats_for_p(p)
        p_cti = get_cti_for_p(p)
        in_target_reasons = [
            "응대 가능 상담원 없음", "상담원 수신 거절", "대기열 최대 대기시간 초과",
            "링 울리는 시간 초과", "최대 대기열 수 초과", "링 울리는 중 고객 종료",
            "음성 사서함", "고객이 먼저 끊었을 때"
        ]
        calls_in = sum(1 for c in p_cti if c.get("dir") in ["inbound", "missed"] and (
            c.get("ans") == 1 or 
            (c.get("reason") in in_target_reasons) or 
            (c.get("reason") == "대기열에서 고객 종료" and c.get("is_in_hours"))
        ))
        calls_out = sum(1 for c in p_cti if c.get("dir") == "outbound" and c.get("ans") == 1 and "부재" not in (c.get("tag") or "") and "부재" not in (c.get("reason") or ""))
        tot_calls = calls_in + calls_out
        tot_chat = sum(1 for c in p_c if c.get("channel") in ["채팅", "상담사챗", "챗봇(ALF)"] and c.get("channel") != "배송접수")
        board_by_week = voc_data.get("BOARD_COUNT_BY_WEEK", {})
        if p.get("weekKeys"):
            tot_board = sum(board_by_week.get(wk, 0) for wk in p["weekKeys"])
        else:
            tot_board = board_by_week.get(pk, 0)
        tot_all = tot_calls + tot_chat + tot_board
        return tot_calls, tot_chat, tot_board, tot_all

    def get_ships_for_p(p):
        if not p: return []
        pk = str(p.get("key", ""))
        if is_week:
            s_list = voc_data.get("SHIPMENTS_BY_WEEK", {}).get(pk, [])
            if not s_list:
                w_chats = voc_data.get("CHATS_BY_WEEK", {}).get(pk, [])
                s_list = [{"type": c.get("sub") or c.get("mid") or "배송"} for c in w_chats if c.get("valid") and (c.get("channel") == "배송접수" or c.get("mid") == "배송")]
            return s_list
        if "-" in pk and len(pk) == 7 and "W" not in pk and "-Q" not in pk:
            return [s for s in all_ships_flat if any(str(s.get(k, "")).startswith(pk) for k in ["date", "claimDate", "orderDate", "inboundDate"])]
        if "-Q" in pk:
            y, q = pk.split("-Q")
            qm = [f"{y}-{str((int(q)-1)*3 + i).zfill(2)}" for i in [1, 2, 3]]
            return [s for s in all_ships_flat if any(any(str(s.get(k, "")).startswith(m) for k in ["date", "claimDate", "orderDate", "inboundDate"]) for m in qm)]
        if len(pk) == 4 and pk.isdigit():
            return [s for s in all_ships_flat if any(str(s.get(k, "")).startswith(pk) for k in ["date", "claimDate", "orderDate", "inboundDate"])]
        return [s for wk in p.get("weekKeys", []) for s in voc_data.get("SHIPMENTS_BY_WEEK", {}).get(wk, [])]

    # 1) 채널별 인입 실적 & 기간 추이
    channel_recent_data = []
    for p in trend_periods:
        c, ch, b, t = get_channel_metrics_for_p(p)
        channel_recent_data.append((get_period_label(p), c, ch, b, t))

    cur_calls, cur_chat, cur_board, cur_tot_all = get_channel_metrics_for_p(period_obj)
    if prev_period_obj:
        prv_calls, prv_chat, prv_board, prv_tot_all = get_channel_metrics_for_p(prev_period_obj)
    else:
        prv_calls = prv_chat = prv_board = 0
        prv_tot_all = None

    # 2) 품질 소분류 전수 매트릭스 (4개 제한 없이 전수 나열)
    def get_q_sub(c):
        return c.get("sub") or c.get("mid") or "기타"

    recent_q_chats_by_period = []
    for p in trend_periods:
        recent_q_chats_by_period.append([c for c in get_chats_for_p(p) if is_qc_chat(c)])

    cur_q_chats = [c for c in get_chats_for_p(period_obj) if is_qc_chat(c)]
    prv_q_chats = [c for c in get_chats_for_p(prev_period_obj) if is_qc_chat(c)] if prev_period_obj else []

    cur_q_subs = Counter(get_q_sub(c) for c in cur_q_chats)
    all_q_subs = Counter(get_q_sub(c) for ql in recent_q_chats_by_period for c in ql)
    all_q_sorted = sorted(all_q_subs.keys(), key=lambda s: (cur_q_subs.get(s, 0), all_q_subs.get(s, 0)), reverse=True)

    q_matrix = []
    for s in all_q_sorted:
        row = [s]
        for ql in recent_q_chats_by_period:
            row.append(len([c for c in ql if get_q_sub(c) == s]))
        q_matrix.append(row)
    top_q_items = [(s, cur_q_subs.get(s, 0)) for s in all_q_sorted[:5]]
    prv_q_subs = Counter(get_q_sub(c) for c in prv_q_chats)

    # 3) 배송 유형 전수 매트릭스 (전수 나열)
    recent_ships_by_period = []
    for p in trend_periods:
        recent_ships_by_period.append(get_ships_for_p(p))

    cur_ships = get_ships_for_p(period_obj)
    prv_ships = get_ships_for_p(prev_period_obj) if prev_period_obj else []

    cur_d_types = Counter(s.get("type") for s in cur_ships if s.get("type"))
    all_d_types = Counter(s.get("type") for sl in recent_ships_by_period for s in sl if s.get("type"))
    all_d_sorted = sorted(all_d_types.keys(), key=lambda t: (cur_d_types.get(t, 0), all_d_types.get(t, 0)), reverse=True)

    d_matrix = []
    for t in all_d_sorted:
        row = [t]
        for sl in recent_ships_by_period:
            row.append(len([s for s in sl if s.get("type") == t]))
        d_matrix.append(row)
    top_ship_items = [(t, cur_d_types.get(t, 0)) for t in all_d_sorted[:5]]
    prv_d_types = Counter(s.get("type") for s in prv_ships if s.get("type"))

    # 4) 서비스 유형 전수 매트릭스 (전수 나열)
    def get_svc_sub(c):
        return c.get("sub") or c.get("mid") or "기타"

    recent_svc_chats_by_period = []
    for p in trend_periods:
        recent_svc_chats_by_period.append([c for c in get_chats_for_p(p) if is_svc_chat(c)])

    cur_svc_chats = [c for c in get_chats_for_p(period_obj) if is_svc_chat(c)]
    prv_svc_chats = [c for c in get_chats_for_p(prev_period_obj) if is_svc_chat(c)] if prev_period_obj else []

    cur_s_types = Counter(get_svc_sub(c) for c in cur_svc_chats)
    all_s_types = Counter(get_svc_sub(c) for sl in recent_svc_chats_by_period for c in sl)
    all_s_sorted = sorted(all_s_types.keys(), key=lambda s: (cur_s_types.get(s, 0), all_s_types.get(s, 0)), reverse=True)

    s_matrix = []
    for s in all_s_sorted:
        row = [s]
        for sl in recent_svc_chats_by_period:
            row.append(len([c for c in sl if get_svc_sub(c) == s]))
        s_matrix.append(row)
    top_svc_items = [(s, cur_s_types.get(s, 0)) for s in all_s_sorted[:5]]
    prv_s_types = Counter(get_svc_sub(c) for c in prv_svc_chats)

    def calc_item_diff(cur_val, prv_val):
        d = cur_val - prv_val
        if prv_val > 0:
            pct = (d / prv_val) * 100
            if d > 0:
                return f"▲{d} (+{pct:.1f}%)", "rose"
            elif d < 0:
                return f"▼{abs(d)} ({pct:.1f}%)", "teal"
            else:
                return "- (0.0%)", "muted"
        else:
            return (f"▲{d} (신규)", "rose") if d > 0 else ("-", "muted")

    # =============================================================
    # [Sheet 2: 차트데이터셋 기록 (숨김 시트로 설정)]
    # =============================================================
    ws_data = wb.create_sheet("차트데이터셋")
    ws_data.sheet_state = "hidden"
    ws_data.views.sheetView[0].showGridLines = True

    # 표 1: 채널별 인입 추이 (Row 1 ~ 6)
    ws_data.cell(row=1, column=1, value="[표 1] 채널별 인입 실적 & 최근 4주 추이 데이터").font = font_bold
    chan_headers = ["운영주차", "전화 (콜)", "채팅 (상담사/챗봇)", "게시판 (스토어/몰)", "전체 VOC 인입량 (Total)"]
    for ci, h in enumerate(chan_headers, 1):
        cell = ws_data.cell(row=2, column=ci, value=h)
        cell.font = font_tbl_h; cell.fill = fill_slate_header; cell.alignment = Alignment(vertical="center", horizontal="center"); cell.border = border_thin
    for ri, row_vals in enumerate(channel_recent_data, 3):
        for ci, val in enumerate(row_vals, 1):
            cell = ws_data.cell(row=ri, column=ci, value=val)
            cell.font = font_regular; cell.alignment = Alignment(vertical="center", horizontal="center" if ci == 1 else "right"); cell.border = border_thin
            if ci > 1: cell.number_format = "#,##0;;"

    # 표 2: [품질 불만] 소분류 전수 매트릭스
    q_start_row = 10
    ws_data.cell(row=q_start_row - 1, column=1, value=f"[표 2] [품질 불만] 소분류별 최근 4주 발생 추이 매트릭스 (전수 {len(all_q_sorted)}개 유형)").font = font_bold
    q_headers = ["품질 소분류 태그"] + legend_w_labels
    for ci, h in enumerate(q_headers, 1):
        cell = ws_data.cell(row=q_start_row, column=ci, value=h)
        cell.font = font_tbl_h; cell.fill = fill_teal_header; cell.alignment = Alignment(vertical="center", horizontal="center"); cell.border = border_thin
    for ri, r in enumerate(q_matrix, q_start_row + 1):
        for ci, val in enumerate(r, 1):
            cell = ws_data.cell(row=ri, column=ci, value=val)
            cell.font = font_regular; cell.alignment = Alignment(vertical="center", horizontal="left" if ci == 1 else "right"); cell.border = border_thin
            if ci > 1: cell.number_format = "#,##0;;"
    q_end_row = q_start_row + len(q_matrix)

    # 표 3: [배송 클레임] 세부 유형 전수 매트릭스
    d_start_row = q_end_row + 3
    ws_data.cell(row=d_start_row - 1, column=1, value=f"[표 3] [배송 클레임] 세부 유형별 최근 4주 발생 추이 매트릭스 (전수 {len(all_d_sorted)}개 유형)").font = font_bold
    d_headers = ["배송 세부 유형"] + legend_w_labels
    for ci, h in enumerate(d_headers, 1):
        cell = ws_data.cell(row=d_start_row, column=ci, value=h)
        cell.font = font_tbl_h; cell.fill = PatternFill(fill_type="solid", fgColor="0D9488"); cell.alignment = Alignment(vertical="center", horizontal="center"); cell.border = border_thin
    for ri, r in enumerate(d_matrix, d_start_row + 1):
        for ci, val in enumerate(r, 1):
            cell = ws_data.cell(row=ri, column=ci, value=val)
            cell.font = font_regular; cell.alignment = Alignment(vertical="center", horizontal="left" if ci == 1 else "right"); cell.border = border_thin
            if ci > 1: cell.number_format = "#,##0;;"
    d_end_row = d_start_row + len(d_matrix)

    # 표 4: [서비스 클레임] 세부 유형 전수 매트릭스
    s_start_row = d_end_row + 3
    ws_data.cell(row=s_start_row - 1, column=1, value=f"[표 4] [서비스 클레임] 세부 유형별 최근 4주 발생 추이 매트릭스 (전수 {len(all_s_sorted)}개 유형)").font = font_bold
    s_headers = ["서비스 세부 유형"] + legend_w_labels
    for ci, h in enumerate(s_headers, 1):
        cell = ws_data.cell(row=s_start_row, column=ci, value=h)
        cell.font = font_tbl_h; cell.fill = PatternFill(fill_type="solid", fgColor="6D28D9"); cell.alignment = Alignment(vertical="center", horizontal="center"); cell.border = border_thin
    for ri, r in enumerate(s_matrix, s_start_row + 1):
        for ci, val in enumerate(r, 1):
            cell = ws_data.cell(row=ri, column=ci, value=val)
            cell.font = font_regular; cell.alignment = Alignment(vertical="center", horizontal="left" if ci == 1 else "right"); cell.border = border_thin
            if ci > 1: cell.number_format = "#,##0;;"
    s_end_row = s_start_row + len(s_matrix)

    for c in ["A", "B", "C", "D", "E"]:
        ws_data.column_dimensions[c].width = 24

    # =============================================================
    # [Sheet 1 본문 구성]
    # =============================================================
    row_idx = 8

    # 1. VOC 요약 (KPI)
    ws_rep.cell(row=row_idx, column=1, value="1. VOC 요약 (인입 및 3대 클레임 총괄)").font = font_sec
    ws_rep.row_dimensions[row_idx].height = 24
    row_idx += 1

    kpi_headers = ["구분", "현재 건수", "이전 건수", "이전 대비 증감", "증감율", "비중 (전체 대비)"]
    ws_rep.row_dimensions[row_idx].height = 24
    for ci, h in enumerate(kpi_headers, 1):
        cell = ws_rep.cell(row=row_idx, column=ci, value=h)
        cell.font = font_tbl_h; cell.fill = fill_teal_header; cell.alignment = Alignment(vertical="center", horizontal="center"); cell.border = border_thin
    row_idx += 1

    cur_tot = cur_tot_all
    prv_tot = prv_tot_all

    q_cur_cnt = len(cur_q_chats)
    q_prv_cnt = len(prv_q_chats) if prev_week_keys else None
    
    d_cur_cnt = len(cur_ships)
    d_prv_cnt = len(prv_ships) if prev_week_keys else None

    s_cur_cnt = len(cur_svc_chats)
    s_prv_cnt = len(prv_svc_chats) if prev_week_keys else None

    def calc_diff(cur, prv):
        if prv is None: return "-"
        d = cur - prv
        return f"▲ +{d:,}" if d > 0 else (f"▼ -{abs(d):,}" if d < 0 else "0")

    def calc_pct(cur, prv):
        if prv is None or prv == 0: return "-"
        p = ((cur - prv) / prv) * 100
        return f"{'+' if p > 0 else ''}{p:.1f}%"

    cur_contact = cur_calls + cur_chat
    prv_contact = (prv_calls + prv_chat) if prev_week_keys else None

    # 대시보드와 동일 공식: 전화 + 채팅 실응대 인입량 대비 클레임 비율 산출
    kpi_items = [
        ("총 인입 전수 (공식 Total)", cur_tot, prv_tot, "100.0%"),
        ("품질 클레임 (전화·채팅 대비)", q_cur_cnt, q_prv_cnt, f"{(q_cur_cnt/cur_contact*100):.1f}%" if cur_contact else "0%"),
        ("배송 클레임 (전화·채팅 대비)", d_cur_cnt, d_prv_cnt, f"{(d_cur_cnt/cur_contact*100):.1f}%" if cur_contact else "0%"),
        ("서비스 클레임 (전화·채팅 대비)", s_cur_cnt, s_prv_cnt, f"{(s_cur_cnt/cur_contact*100):.1f}%" if cur_contact else "0%"),
    ]

    for is_first, (k_name, k_cur, k_prv, k_sh) in enumerate(kpi_items):
        ws_rep.row_dimensions[row_idx].height = 21
        c1 = ws_rep.cell(row=row_idx, column=1, value=k_name)
        c2 = ws_rep.cell(row=row_idx, column=2, value=k_cur)
        c3 = ws_rep.cell(row=row_idx, column=3, value=k_prv if k_prv is not None else "-")
        c4 = ws_rep.cell(row=row_idx, column=4, value=calc_diff(k_cur, k_prv))
        c5 = ws_rep.cell(row=row_idx, column=5, value=calc_pct(k_cur, k_prv))
        c6 = ws_rep.cell(row=row_idx, column=6, value=k_sh)

        for ci, cell in enumerate([c1, c2, c3, c4, c5, c6], 1):
            cell.font = font_bold if is_first == 0 else font_regular
            cell.border = border_thin
            if ci == 1: cell.alignment = Alignment(vertical="center", horizontal="left", indent=1)
            elif ci in (2, 3): 
                cell.alignment = Alignment(vertical="center", horizontal="right")
                if isinstance(cell.value, (int, float)): cell.number_format = "#,##0"
            else: cell.alignment = Alignment(vertical="center", horizontal="center")

        if is_first == 0:
            apply_box(ws_rep, row_idx, 1, row_idx, 6, fill_total, border_thin)
        row_idx += 1

    row_idx += 1 # Spacer

    # 2. 채널별 인입 실적 & 최근 추이
    trend_sfx = "4주" if is_week else ("월별" if is_month else ("분기별" if is_quarter else "연도별"))
    ws_rep.cell(row=row_idx, column=1, value=f"2. 채널별 인입 실적 & 최근 추이 ({'최근 4주' if is_week else '추이 요약'})").font = font_sec
    ws_rep.row_dimensions[row_idx].height = 24
    row_idx += 1

    # [차트 1: 채널별 추이 복합 차트 - 전폭 28.5cm, 슬림 높이 7.5cm, 눈금선 3선]
    chart_chan = BarChart()
    chart_chan.type = "col"
    chart_chan.grouping = "clustered"
    chart_chan.overlap = 0
    chart_chan.gapWidth = 110
    chart_chan.width = 28.5
    chart_chan.height = 7.5
    chart_chan.title = None
    chart_chan.legend.position = "t"
    chart_chan.legend.legendPos = "t"
    chart_chan.roundedCorners = False
    chart_chan.visible_cells_only = False
    chart_chan.graphical_properties = GraphicalProperties()
    chart_chan.graphical_properties.line = LineProperties(noFill=True)

    chart_chan.x_axis.delete = False
    chart_chan.y_axis.delete = False
    chart_chan.x_axis.axPos = "b"
    chart_chan.x_axis.tickLblPos = "nextTo"
    chart_chan.y_axis.axPos = "l"
    chart_chan.y_axis.tickLblPos = "nextTo"

    # Y축 눈금선: 데이터 규모에 맞춰 최적 스케일링
    max_tot = max([r[4] for r in channel_recent_data] + [1000])
    y_max = ((max_tot // 500) + 1) * 500 if max_tot < 5000 else ((max_tot // 2000) + 1) * 2000
    chart_chan.y_axis.scaling.min = 0
    chart_chan.y_axis.scaling.max = y_max
    chart_chan.y_axis.majorUnit = y_max // 2 if y_max >= 1000 else 250

    grid_line = LineProperties(solidFill="E2E8F0", w=9525)
    chart_chan.y_axis.majorGridlines = ChartLines()
    chart_chan.y_axis.majorGridlines.spPr = GraphicalProperties(ln=grid_line)
    chart_chan.x_axis.majorGridlines = None
    chart_chan.x_axis.line = LineProperties(solidFill="CBD5E1", w=12700)
    chart_chan.y_axis.line = LineProperties(noFill=True)
    chart_chan.y_axis.majorTickMark = "none"
    chart_chan.x_axis.majorTickMark = "none"

    data_ref1 = Reference(ws_data, min_col=2, min_row=2, max_col=4, max_row=2 + len(channel_recent_data))
    chart_chan.add_data(data_ref1, titles_from_data=True, from_rows=False)

    cats1 = Reference(ws_data, min_col=1, min_row=3, max_col=1, max_row=2 + len(channel_recent_data))
    chart_chan.set_categories(cats1)

    sc1 = StrData(ptCount=len(recent_labels), pt=[StrVal(idx=i, v=w) for i, w in enumerate(recent_labels)])
    str_f1 = f"'차트데이터셋'!$A$3:$A${2 + len(channel_recent_data)}"
    for s in chart_chan.series:
        s.cat = AxDataSource(strRef=StrRef(f=str_f1, strCache=sc1))

    chan_colors = ["0F766E", "0284C7", "F59E0B"]
    for i, s in enumerate(chart_chan.series):
        s.graphicalProperties.solidFill = chan_colors[i % len(chan_colors)]
        s.graphicalProperties.line = LineProperties(noFill=True)

    chart_chan.dataLabels = DataLabelList()
    chart_chan.dataLabels.showVal = True
    chart_chan.dataLabels.showCatName = False
    chart_chan.dataLabels.showSerName = False
    chart_chan.dataLabels.showPercent = False
    chart_chan.dataLabels.showLegendKey = False
    chart_chan.dataLabels.position = "outEnd"

    line_tot = LineChart()
    line_tot.style = 13
    line_tot.visible_cells_only = False
    data_line = Reference(ws_data, min_col=5, min_row=2, max_col=5, max_row=2 + len(channel_recent_data))
    line_tot.add_data(data_line, titles_from_data=True)
    line_tot.y_axis = chart_chan.y_axis
    line_tot.series[0].graphicalProperties.line.solidFill = "18181B"
    line_tot.series[0].graphicalProperties.line.width = 25000
    line_tot.series[0].marker.symbol = "circle"
    line_tot.series[0].marker.size = 7
    line_tot.series[0].marker.graphicalProperties.solidFill = "18181B"
    line_tot.series[0].marker.graphicalProperties.line.solidFill = "FFFFFF"

    line_tot.dataLabels = DataLabelList()
    line_tot.dataLabels.showVal = True
    line_tot.dataLabels.showCatName = False
    line_tot.dataLabels.showSerName = False
    line_tot.dataLabels.showPercent = False
    line_tot.dataLabels.showLegendKey = False
    line_tot.dataLabels.position = "t"

    chart_chan += line_tot
    ws_rep.add_chart(chart_chan, f"A{row_idx}")
    row_idx += 16 # 차트 크기에 딱 맞춘 행 오프셋 (불필요한 세로 여백 제거)

    # 채널별 상세 테이블
    recent_labels = [r[0] + (" (현재)" if i == len(channel_recent_data)-1 else "") for i, r in enumerate(channel_recent_data)]
    chan_tbl_headers = ["채널 구분"] + recent_labels + ["현재 점유율"]
    ws_rep.row_dimensions[row_idx].height = 24
    for ci, h in enumerate(chan_tbl_headers, 1):
        cell = ws_rep.cell(row=row_idx, column=ci, value=h)
        cell.font = font_tbl_h; cell.fill = fill_teal_header; cell.alignment = Alignment(vertical="center", horizontal="center"); cell.border = border_thin
    row_idx += 1

    chan_rows = [
        ("전화 (인바운드)", [r[1] for r in channel_recent_data]),
        ("채팅 (인 & 아웃)", [r[2] for r in channel_recent_data]),
        ("게시판 (스토어/자사몰)", [r[3] for r in channel_recent_data]),
    ]
    cur_tot_val = channel_recent_data[-1][4] if channel_recent_data else 1
    for ch_name, counts in chan_rows:
        ws_rep.row_dimensions[row_idx].height = 20
        c1 = ws_rep.cell(row=row_idx, column=1, value=ch_name)
        c1.font = font_regular; c1.alignment = Alignment(vertical="center", horizontal="left", indent=1); c1.border = border_thin
        for ci, cnt in enumerate(counts, 2):
            cell = ws_rep.cell(row=row_idx, column=ci, value=cnt)
            cell.font = font_regular; cell.alignment = Alignment(vertical="center", horizontal="center"); cell.border = border_thin; cell.number_format = "#,##0"
        last_val = counts[-1]
        c_sh = ws_rep.cell(row=row_idx, column=len(counts) + 2, value=f"{(last_val/cur_tot_val*100):.1f}%" if cur_tot_val else "0.0%")
        c_sh.font = font_regular; c_sh.alignment = Alignment(vertical="center", horizontal="center"); c_sh.border = border_thin
        row_idx += 1

    # 채널 합계 행
    ws_rep.row_dimensions[row_idx].height = 22
    c_tot1 = ws_rep.cell(row=row_idx, column=1, value="인입 총합계")
    c_tot1.font = font_bold; c_tot1.alignment = Alignment(vertical="center", horizontal="center"); c_tot1.border = border_thin
    for ci, r in enumerate(channel_recent_data, 2):
        cell = ws_rep.cell(row=row_idx, column=ci, value=r[4])
        cell.font = font_bold; cell.alignment = Alignment(vertical="center", horizontal="center"); cell.border = border_thin; cell.number_format = "#,##0"
    c_tot_sh = ws_rep.cell(row=row_idx, column=len(channel_recent_data) + 2, value="100.0%")
    c_tot_sh.font = font_bold; c_tot_sh.alignment = Alignment(vertical="center", horizontal="center"); c_tot_sh.border = border_thin
    apply_box(ws_rep, row_idx, 1, row_idx, len(chan_tbl_headers), fill_total, border_thin)
    row_idx += 2

    # 2.5 [신규] AI 상담(ALF 챗봇) 처리율 코멘트 배너 (웹 대시보드와 동일 배치)
    cur_alf_chats = [c for c in get_chats_for_p(period_obj) if c.get("valid") and c.get("channel") != "전화" and c.get("alfInflow")]
    alf_inflow = len(cur_alf_chats)
    alf_comp = len([c for c in cur_alf_chats if c.get("alfResolved")])
    alf_trans = alf_inflow - alf_comp
    alf_rate = (alf_comp / alf_inflow * 100) if alf_inflow > 0 else 0.0

    prev_alf_chats = [c for c in get_chats_for_p(prev_period_obj) if c.get("valid") and c.get("channel") != "전화" and c.get("alfInflow")] if prev_period_obj else []
    prev_alf_inflow = len(prev_alf_chats)
    prev_alf_comp = len([c for c in prev_alf_chats if c.get("alfResolved")])
    prev_alf_rate = (prev_alf_comp / prev_alf_inflow * 100) if prev_alf_inflow > 0 else None

    diff_rate_str = "–"
    if prev_alf_rate is not None:
        diff_r = alf_rate - prev_alf_rate
        diff_rate_str = f"▲+{diff_r:.1f}%p" if diff_r > 0 else (f"▼{abs(diff_r):.1f}%p" if diff_r < 0 else "0.0%p")

    ws_rep.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=6)
    apply_box(ws_rep, row_idx, 1, row_idx, 6, fill_banner, border_thin)
    ws_rep.row_dimensions[row_idx].height = 24
    c_alf_title = ws_rep.cell(row=row_idx, column=1, value=f"🤖 [AI 상담(ALF) 챗봇 처리율 분석]  챗봇 자체 완결율 {alf_rate:.1f}%")
    c_alf_title.font = font_bold
    c_alf_title.alignment = Alignment(vertical="center", horizontal="left", indent=1)
    row_idx += 1

    ws_rep.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=6)
    apply_box(ws_rep, row_idx, 1, row_idx, 6, fill_zebra, border_thin)
    ws_rep.row_dimensions[row_idx].height = 24
    prev_disp_str = f"{prev_alf_rate:.1f}%" if prev_alf_rate is not None else "–"
    alf_comment_line = f"• 자체 완결: {alf_comp:,}건 ({alf_rate:.1f}%) · 총 인입: {alf_inflow:,}건 (상담사 연결: {alf_trans:,}건)  |  선택: {alf_rate:.1f}%  |  직전: {prev_disp_str}  |  증감: {diff_rate_str}"
    c_alf_body = ws_rep.cell(row=row_idx, column=1, value=alf_comment_line)
    c_alf_body.font = font_regular
    c_alf_body.alignment = Alignment(vertical="center", horizontal="left", indent=1)
    row_idx += 2

    # 3. 부문별 클레임 현황 & 이슈 인사이트
    ws_rep.cell(row=row_idx, column=1, value="3. 부문별 클레임 현황 & 이슈 인사이트 (품질 · 배송 · 서비스 3대 부문)").font = font_sec
    ws_rep.row_dimensions[row_idx].height = 24
    row_idx += 1

    top_headers = ["순위", "주요 세부 클레임 유형", "현재 건수", "이전 대비 증감", "부문 내 비중", "비고 (특이사항)"]
    font_rose = Font(name="맑은 고딕", size=9, bold=True, color="DC2626")
    font_teal = Font(name="맑은 고딕", size=9, bold=True, color="0F766E")
    font_diff_muted = Font(name="맑은 고딕", size=9, color="6B7280")

    # 3-1. [품질 클레임]
    q_chart_rows = min(8, len(q_matrix))
    ws_rep.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=6)
    apply_box(ws_rep, row_idx, 1, row_idx, 6, fill_amber_banner, border_thin)
    ws_rep.row_dimensions[row_idx].height = 24
    q_diff_str = calc_diff(q_cur_cnt, q_prv_cnt)
    q_pct_str = calc_pct(q_cur_cnt, q_prv_cnt)
    ws_rep.cell(row=row_idx, column=1, value=f"■ [품질 불만 주요 유형 Top {q_chart_rows} {trend_sfx} 인입 추이] 현재 {q_cur_cnt:,}건 (이전 대비 {q_diff_str}, {q_pct_str})  |  현재 최다순 정렬").font = font_bold
    ws_rep.cell(row=row_idx, column=1).alignment = Alignment(vertical="center", horizontal="left", indent=1)
    row_idx += 1

    # [차트 2: 품질 소분류 전수 클러스터 기둥 차트 - 상위 8개 유형]
    q_max_v = max([max(r[1:]) for r in q_matrix[:q_chart_rows]] + [10])
    q_y_unit = 5 if q_max_v <= 30 else (10 if q_max_v <= 100 else 25)
    chart_q = make_pillar_chart(min_row=q_start_row, max_row=q_start_row + q_chart_rows, colors=["BAE6FD", "7DD3FC", "38BDF8", "0F766E"], y_unit=q_y_unit)
    ws_rep.add_chart(chart_q, f"A{row_idx}")
    row_idx += 16

    # 품질 TOP 5 테이블 (전기간 대비 증감 포함)
    ws_rep.row_dimensions[row_idx].height = 22
    for ci in range(1, 7):
        cell = ws_rep.cell(row=row_idx, column=ci, value=top_headers[ci-1])
        cell.font = Font(name="맑은 고딕", size=9, bold=True, color="374151"); cell.fill = fill_total; cell.alignment = Alignment(vertical="center", horizontal="center"); cell.border = border_thin
    row_idx += 1

    for idx, (m_label, m_count) in enumerate(top_q_items, 1):
        ws_rep.row_dimensions[row_idx].height = 20
        c1 = ws_rep.cell(row=row_idx, column=1, value=idx)
        c2 = ws_rep.cell(row=row_idx, column=2, value=m_label)
        c3 = ws_rep.cell(row=row_idx, column=3, value=m_count)
        
        prv_c = prv_q_subs.get(m_label, 0)
        diff_str, diff_type = calc_item_diff(m_count, prv_c)
        c4 = ws_rep.cell(row=row_idx, column=4, value=diff_str)
        c5 = ws_rep.cell(row=row_idx, column=5, value=f"{(m_count/q_cur_cnt*100):.1f}%" if q_cur_cnt else "0.0%")
        c6 = ws_rep.cell(row=row_idx, column=6, value="최다 접수 유형 (집중 모니터링)" if idx == 1 else ("이전 대비 증가" if diff_type == "rose" and m_count > prv_c else ""))

        for ci, cell in enumerate([c1, c2, c3, c4, c5, c6], 1):
            cell.font = font_regular; cell.border = border_thin
            if ci == 1: cell.alignment = Alignment(vertical="center", horizontal="center")
            elif ci == 2: cell.alignment = Alignment(vertical="center", horizontal="left", indent=1)
            elif ci == 3: cell.alignment = Alignment(vertical="center", horizontal="center"); cell.number_format = "#,##0"
            elif ci == 4:
                cell.alignment = Alignment(vertical="center", horizontal="center")
                cell.font = font_rose if diff_type == "rose" else (font_teal if diff_type == "teal" else font_diff_muted)
            elif ci == 5: cell.alignment = Alignment(vertical="center", horizontal="center")
            elif ci == 6:
                cell.alignment = Alignment(vertical="center", horizontal="center")
                cell.font = font_muted
        row_idx += 1

    # 품질 코멘트
    q_comment = format_insight_text(
        insights.get("quality") if insights else None,
        "📌 [이슈 코멘트 & 액션 플랜] 발진, 거품과다, 제조일자불만 등 주요 품질 리스크에 대해 생산공정 역추적 및 맞교환 조치 완료. 전수 상세는 '품질raw' 시트 확인 가능."
    )
    ws_rep.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=6)
    apply_box(ws_rep, row_idx, 1, row_idx, 6, fill_zebra, border_thin)
    ws_rep.row_dimensions[row_idx].height = calc_comment_box_height(q_comment, char_limit=58, line_height=20, min_height=48, padding=16)
    ws_rep.cell(row=row_idx, column=1, value=q_comment).font = font_regular
    ws_rep.cell(row=row_idx, column=1).alignment = Alignment(vertical="center", horizontal="left", wrap_text=True, indent=1)
    row_idx += 2

    # 3-2. [배송 클레임]
    d_chart_rows = min(8, len(d_matrix))
    ws_rep.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=6)
    apply_box(ws_rep, row_idx, 1, row_idx, 6, fill_rose_banner, border_thin)
    ws_rep.row_dimensions[row_idx].height = 24
    d_diff_str = calc_diff(d_cur_cnt, d_prv_cnt)
    d_pct_str = calc_pct(d_cur_cnt, d_prv_cnt)
    ws_rep.cell(row=row_idx, column=1, value=f"■ [배송 클레임 주요 유형 Top {d_chart_rows} {trend_sfx} 인입 추이] 물류원장 {d_cur_cnt:,}건 (이전 대비 {d_diff_str}, {d_pct_str})  |  현재 최다순 정렬").font = font_bold
    ws_rep.cell(row=row_idx, column=1).alignment = Alignment(vertical="center", horizontal="left", indent=1)
    row_idx += 1

    # [차트 3: 배송 유형 클러스터 기둥 차트 - 상위 8개 유형]
    d_max_v = max([max(r[1:]) for r in d_matrix[:d_chart_rows]] + [10])
    d_y_unit = 5 if d_max_v <= 30 else (10 if d_max_v <= 100 else 25)
    chart_d = make_pillar_chart(min_row=d_start_row, max_row=d_start_row + d_chart_rows, colors=["99F6E4", "5EEAD4", "2DD4BF", "0F766E"], y_unit=d_y_unit)
    ws_rep.add_chart(chart_d, f"A{row_idx}")
    row_idx += 16

    # 배송 TOP 5 테이블 (전기간 대비 증감 포함)
    ws_rep.row_dimensions[row_idx].height = 22
    for ci in range(1, 7):
        cell = ws_rep.cell(row=row_idx, column=ci, value=top_headers[ci-1])
        cell.font = Font(name="맑은 고딕", size=9, bold=True, color="374151"); cell.fill = fill_total; cell.alignment = Alignment(vertical="center", horizontal="center"); cell.border = border_thin
    row_idx += 1

    for idx, (dtype, dtot) in enumerate(top_ship_items, 1):
        ws_rep.row_dimensions[row_idx].height = 20
        c1 = ws_rep.cell(row=row_idx, column=1, value=idx)
        c2 = ws_rep.cell(row=row_idx, column=2, value=dtype)
        c3 = ws_rep.cell(row=row_idx, column=3, value=dtot)

        prv_d = prv_d_types.get(dtype, 0)
        diff_str, diff_type = calc_item_diff(dtot, prv_d)
        c4 = ws_rep.cell(row=row_idx, column=4, value=diff_str)
        c5 = ws_rep.cell(row=row_idx, column=5, value=f"{(dtot/d_cur_cnt*100):.1f}%" if d_cur_cnt else "0.0%")
        c6 = ws_rep.cell(row=row_idx, column=6, value="최다 배송 불만 (물류 벤더 확인)" if idx == 1 else ("이전 대비 증가" if diff_type == "rose" and dtot > prv_d else ""))

        for ci, cell in enumerate([c1, c2, c3, c4, c5, c6], 1):
            cell.font = font_regular; cell.border = border_thin
            if ci == 1: cell.alignment = Alignment(vertical="center", horizontal="center")
            elif ci == 2: cell.alignment = Alignment(vertical="center", horizontal="left", indent=1)
            elif ci == 3: cell.alignment = Alignment(vertical="center", horizontal="center"); cell.number_format = "#,##0"
            elif ci == 4:
                cell.alignment = Alignment(vertical="center", horizontal="center")
                cell.font = font_rose if diff_type == "rose" else (font_teal if diff_type == "teal" else font_diff_muted)
            elif ci == 5: cell.alignment = Alignment(vertical="center", horizontal="center")
            elif ci == 6:
                cell.alignment = Alignment(vertical="center", horizontal="center")
                cell.font = font_muted
        row_idx += 1

    # 배송 코멘트
    d_comment = format_insight_text(
        insights.get("delivery") if insights else None,
        "📌 [이슈 코멘트 & 액션 플랜] 운임비불만 및 파손반송 관련 물류 벤더사(풀필먼트 및 CJ) 오출고 재발 방지 및 택배 파손 맞교환 조치 완료."
    )
    ws_rep.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=6)
    apply_box(ws_rep, row_idx, 1, row_idx, 6, fill_zebra, border_thin)
    ws_rep.row_dimensions[row_idx].height = calc_comment_box_height(d_comment, char_limit=58, line_height=20, min_height=48, padding=16)
    ws_rep.cell(row=row_idx, column=1, value=d_comment).font = font_regular
    ws_rep.cell(row=row_idx, column=1).alignment = Alignment(vertical="center", horizontal="left", wrap_text=True, indent=1)
    row_idx += 2

    # 3-3. [서비스 클레임]
    s_chart_rows = min(8, len(s_matrix))
    ws_rep.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=6)
    apply_box(ws_rep, row_idx, 1, row_idx, 6, fill_teal_banner, border_thin)
    ws_rep.row_dimensions[row_idx].height = 24
    s_diff_str = calc_diff(s_cur_cnt, s_prv_cnt)
    s_pct_str = calc_pct(s_cur_cnt, s_prv_cnt)
    ws_rep.cell(row=row_idx, column=1, value=f"■ [서비스 클레임 주요 유형 Top {s_chart_rows} {trend_sfx} 인입 추이] 현재 {s_cur_cnt:,}건 (이전 대비 {s_diff_str}, {s_pct_str})  |  현재 최다순 정렬").font = font_bold
    ws_rep.cell(row=row_idx, column=1).alignment = Alignment(vertical="center", horizontal="left", indent=1)
    row_idx += 1

    # [차트 4: 서비스 세부 유형 클러스터 기둥 차트 - 상위 8개 유형]
    s_max_v = max([max(r[1:]) for r in s_matrix[:s_chart_rows]] + [10])
    s_y_unit = 2 if s_max_v <= 15 else (5 if s_max_v <= 50 else 10)
    chart_s = make_pillar_chart(min_row=s_start_row, max_row=s_start_row + s_chart_rows, colors=["DDD6FE", "C4B5FD", "A78BFA", "7C3AED"], y_unit=s_y_unit)
    ws_rep.add_chart(chart_s, f"A{row_idx}")
    row_idx += 16

    # 서비스 TOP 5 테이블 (전기간 대비 증감 포함)
    ws_rep.row_dimensions[row_idx].height = 22
    for ci in range(1, 7):
        cell = ws_rep.cell(row=row_idx, column=ci, value=top_headers[ci-1])
        cell.font = Font(name="맑은 고딕", size=9, bold=True, color="374151"); cell.fill = fill_total; cell.alignment = Alignment(vertical="center", horizontal="center"); cell.border = border_thin
    row_idx += 1

    for idx, (stype, scnt) in enumerate(top_svc_items, 1):
        ws_rep.row_dimensions[row_idx].height = 20
        c1 = ws_rep.cell(row=row_idx, column=1, value=idx)
        c2 = ws_rep.cell(row=row_idx, column=2, value=stype)
        c3 = ws_rep.cell(row=row_idx, column=3, value=scnt)

        prv_s = prv_s_types.get(stype, 0)
        diff_str, diff_type = calc_item_diff(scnt, prv_s)
        c4 = ws_rep.cell(row=row_idx, column=4, value=diff_str)
        c5 = ws_rep.cell(row=row_idx, column=5, value=f"{(scnt/s_cur_cnt*100):.1f}%" if s_cur_cnt else "0.0%")
        c6 = ws_rep.cell(row=row_idx, column=6, value="집중 모니터링 문의" if idx == 1 else ("이전 대비 증가" if diff_type == "rose" and scnt > prv_s else ""))

        for ci, cell in enumerate([c1, c2, c3, c4, c5, c6], 1):
            cell.font = font_regular; cell.border = border_thin
            if ci == 1: cell.alignment = Alignment(vertical="center", horizontal="center")
            elif ci == 2: cell.alignment = Alignment(vertical="center", horizontal="left", indent=1)
            elif ci == 3: cell.alignment = Alignment(vertical="center", horizontal="center"); cell.number_format = "#,##0"
            elif ci == 4:
                cell.alignment = Alignment(vertical="center", horizontal="center")
                cell.font = font_rose if diff_type == "rose" else (font_teal if diff_type == "teal" else font_diff_muted)
            elif ci == 5: cell.alignment = Alignment(vertical="center", horizontal="center")
            elif ci == 6:
                cell.alignment = Alignment(vertical="center", horizontal="center")
                cell.font = font_muted
        row_idx += 1

    # 서비스 코멘트
    s_comment = format_insight_text(
        insights.get("service") if insights else None,
        "📌 [이슈 코멘트 & 액션 플랜] 판매처 및 시스템 문의 중심. 첫 통화/채팅 해결율 집중 관리 및 에스컬레이션 방지 조치 진행 중."
    )
    ws_rep.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=6)
    apply_box(ws_rep, row_idx, 1, row_idx, 6, fill_zebra, border_thin)
    ws_rep.row_dimensions[row_idx].height = calc_comment_box_height(s_comment, char_limit=58, line_height=20, min_height=48, padding=16)
    ws_rep.cell(row=row_idx, column=1, value=s_comment).font = font_regular
    ws_rep.cell(row=row_idx, column=1).alignment = Alignment(vertical="center", horizontal="left", wrap_text=True, indent=1)
    row_idx += 2

    # 4. 리스크 모니터링 배너 및 CX팀 종합 코멘트
    ws_rep.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=6)
    apply_box(ws_rep, row_idx, 1, row_idx, 6, PatternFill(fill_type="solid", fgColor="FFFBEB"), border_thin)
    ws_rep.row_dimensions[row_idx].height = 24
    ws_rep.cell(row=row_idx, column=1, value="⚠️ [리스크 모니터링] 고위험 클레임 및 세부 고객 문의 원문은 '품질raw', '배송raw', '서비스raw' 시트에서 전수 확인하실 수 있습니다.").font = Font(name="맑은 고딕", size=9, bold=True, color="B45309")
    ws_rep.cell(row=row_idx, column=1).alignment = Alignment(vertical="center", horizontal="left", indent=1)
    row_idx += 2

    # CX팀 종합 코멘트 (대시보드 실시간 동기화)
    ws_rep.cell(row=row_idx, column=1, value="4. CX팀 종합 코멘트 (대시보드 이슈 메모)").font = font_sec
    ws_rep.row_dimensions[row_idx].height = 24
    row_idx += 1

    memo_lines = []
    if memos and isinstance(memos, list) and len(memos) > 0:
        for idx, m in enumerate(memos, 1):
            if isinstance(m, dict):
                m_txt = m.get("text") or m.get("content") or ""
                m_author = m.get("author") or m.get("user") or "CX팀"
                m_dt = m.get("date") or m.get("created_at") or ""
                memo_lines.append(f"● [메모 {idx}] {m_txt} ({m_author} | {m_dt})")
            elif isinstance(m, str) and m.strip():
                memo_lines.append(f"● [메모 {idx}] {m.strip()}")

    if not memo_lines:
        memo_lines = [
            f"● [총평] {period_disp} 전체 VOC 인입량은 {cur_tot:,}건으로 안정적인 운영 수준을 유지하고 있습니다.",
            f"● [품질 관리] 물티슈 및 스킨케어 품질 클레임은 {q_cur_cnt:,}건 발생하였으며, 주요 이슈 건에 대해 제조공정 역추적 및 맞교환 조치를 완료하였습니다.",
            f"● [배송 및 서비스] 배송 클레임 {d_cur_cnt:,}건, 서비스 클레임 {s_cur_cnt:,}건에 대해 물류 벤더사 오배송/파손 방지 조치 및 실시간 응대율 95% 이상을 달성하였습니다."
        ]

    memo_text = "\n".join(memo_lines)
    box_height = calc_comment_box_height(memo_text, char_limit=58, line_height=20, min_height=70, padding=20)

    ws_rep.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=6)
    apply_box(ws_rep, row_idx, 1, row_idx, 6, fill_zebra, border_thin)
    ws_rep.row_dimensions[row_idx].height = box_height
    ws_rep.cell(row=row_idx, column=1, value=memo_text).font = font_regular
    ws_rep.cell(row=row_idx, column=1).alignment = Alignment(vertical="top", horizontal="left", wrap_text=True, indent=1)
    row_idx += 2

    # Footer
    ws_rep.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=6)
    ws_rep.row_dimensions[row_idx].height = 20
    ws_rep.cell(row=row_idx, column=1, value="베베숲 CX팀 공식 VOC 분석 시스템 · 채널톡 / 게시판 / CTI 전화 / 배송 DB 실시간 연동").font = font_muted
    ws_rep.cell(row=row_idx, column=1).alignment = Alignment(vertical="center", horizontal="center")

    # =============================================================
    # [Sheet 3: 품질raw]
    # =============================================================
    ws_qraw = wb.create_sheet("품질raw")
    ws_qraw.views.sheetView[0].showGridLines = True
    ws_qraw.freeze_panes = "A2"

    q_col_names = [
        "연도", "분기", "월보고용 월", "주차월(MONTH)", "WEEK", "M&W", "id", "고객명",
        "인입일시", "접수일자(DATE)", "담당자", "대분류", "중분류", "소분류",
        "제품명", "제조일자", "문의내용", "품질발송여부", "보상내역서(월)", "보상내역서_전체",
        "유통채널", "주문번호", "출고처", "송장번호"
    ]
    ws_qraw.append(q_col_names)
    ws_qraw.row_dimensions[1].height = 25
    for ci in range(1, len(q_col_names) + 1):
        cell = ws_qraw.cell(row=1, column=ci)
        cell.font = font_tbl_h; cell.fill = fill_slate_header; cell.alignment = Alignment(vertical="center", horizontal="center"); cell.border = border_thin

    raw_records = load_clean_quality_raw(cur_week, voc_data)

    # 이전 비교 대상 주차군 (주간이면 직전 4주, 월/분기/연간이면 직전 기간)
    prev_lookback_keys = prev_week_keys if (is_month or is_quarter or is_year) else set(w["key"] for w in weeks[max(0, p_idx - 4):p_idx])

    # 선택 기간 데이터 (최상단 + 파스텔 오렌지 음영 + 노출)
    # 직전 비교 기간 데이터 (음영 제외 + 노출)
    # 그 외 과거 데이터 (행 숨김 처리, 필터 해제 시 조회 가능)
    if is_week:
        selected_raw = [r for r in raw_records if r.get("weekKey") in target_week_keys]
        lookback_raw = [r for r in raw_records if r.get("weekKey") not in target_week_keys and r.get("weekKey") in prev_lookback_keys]
        older_raw = [r for r in raw_records if r.get("weekKey") not in target_week_keys and r.get("weekKey") not in prev_lookback_keys]
    else:
        selected_raw = [r for r in raw_records if is_item_in_p(r, period_obj)]
        lookback_raw = [r for r in raw_records if not is_item_in_p(r, period_obj) and is_item_in_p(r, prev_period_obj)]
        older_raw = [r for r in raw_records if not is_item_in_p(r, period_obj) and not is_item_in_p(r, prev_period_obj)]
    sorted_raw = [(r, True, False) for r in selected_raw] + [(r, False, True) for r in lookback_raw] + [(r, False, False) for r in older_raw]

    ws_qraw.auto_filter.ref = f"A1:X{len(sorted_raw) + 1}"

    for ri, (r, is_sel, is_lookback) in enumerate(sorted_raw, 2):
        ws_qraw.row_dimensions[ri].height = 20
        # 현재 선택 기간 및 직전 비교 기간 데이터는 표시하고, 그 이전 과거 데이터만 행 숨김
        if not is_sel and not is_lookback:
            ws_qraw.row_dimensions[ri].hidden = True

        row_vals = [
            r.get("year", ""), r.get("quarter", ""), r.get("reportMonth", ""), r.get("month", ""),
            r.get("week", ""), r.get("mw", ""), r.get("id", ""), r.get("cust", ""),
            r.get("time", ""), r.get("date", ""), r.get("mgr", ""), r.get("tagA", ""),
            r.get("tagB", ""), r.get("tagC", ""), r.get("prod", ""), r.get("mfg", ""),
            r.get("issue", ""), r.get("qualitySend", ""), r.get("compMonth", ""), r.get("compAll", ""),
            r.get("mall", ""), r.get("orderNo", ""), r.get("shipmentType", ""), r.get("invoice", "")
        ]
        for ci, val in enumerate(row_vals, 1):
            cell = ws_qraw.cell(row=ri, column=ci, value=val)
            cell.font = font_bold if is_sel else font_regular
            cell.border = border_thin
            if is_sel: cell.fill = fill_pastel_orange
            is_left = ci in (15, 17)  # 제품명(13)과 문의내용(15)만 좌측 정렬, 나머지 전 컬럼 가운데 정렬!
            cell.alignment = Alignment(vertical="center", horizontal="left" if is_left else "center", indent=1 if is_left else 0)

    # 컬럼 너비 설정 (문의내용은 48 고정 유지, 나머지 컬럼은 여백 최적화)
    q_widths = [8, 9, 12, 12, 8, 12, 18, 12, 20, 14, 11, 13, 13, 15, 34, 15, 48, 12, 14, 14, 14, 16, 12, 16]
    for ci, w in enumerate(q_widths, 1):
        ws_qraw.column_dimensions[get_column_letter(ci)].width = w

    # =============================================================
    # [Sheet 4: 배송raw] (품질raw 바로 다음 배치)
    # =============================================================
    ws_sraw = wb.create_sheet("배송raw")
    ws_sraw.views.sheetView[0].showGridLines = True
    ws_sraw.freeze_panes = "A2"

    s_col_names = [
        "NO", "연도", "분기", "MONTH", "WEEK", "물류센터(출고처)",
        "클레임유형", "위험도", "고객명", "주문번호", "송장번호",
        "제품명", "파손/불량수량", "클레임내용", "조치내역"
    ]
    ws_sraw.append(s_col_names)
    ws_sraw.row_dimensions[1].height = 25
    for ci in range(1, len(s_col_names) + 1):
        cell = ws_sraw.cell(row=1, column=ci)
        cell.font = font_tbl_h
        cell.fill = fill_slate_header
        cell.alignment = Alignment(vertical="center", horizontal="center")
        cell.border = border_thin

    # 배송 raw 대상 주차군
    ship_lookback_keys = prev_week_keys if (is_month or is_quarter or is_year) else set(w["key"] for w in weeks[max(0, p_idx - 4):p_idx])
    shipments_by_week_dict = voc_data.get("SHIPMENTS_BY_WEEK", {})
    all_ship_records = []

    for w in reversed(weeks):
        wk = w["key"]
        w_ships = shipments_by_week_dict.get(wk, [])
        for s in w_ships:
            is_sel = (wk in target_week_keys) if is_week else is_item_in_p(s, period_obj)
            is_prev = (wk in ship_lookback_keys) if is_week else is_item_in_p(s, prev_period_obj)
            all_ship_records.append((s, w, is_sel, is_prev))

    sorted_ship_raw = sorted(all_ship_records, key=lambda x: (not x[2], not x[3]))
    ws_sraw.auto_filter.ref = f"A1:{get_column_letter(len(s_col_names))}{len(sorted_ship_raw) + 1}"

    for ri, (s, w, is_sel, is_prev) in enumerate(sorted_ship_raw, 2):
        ws_sraw.row_dimensions[ri].height = 20
        if not is_sel and not is_prev:
            ws_sraw.row_dimensions[ri].hidden = True

        y_str = str(w.get("year", ""))
        q_str = f"{w.get('quarter', '')}Q" if w.get('quarter') else ""
        m_str = f"{w.get('month', '')}월" if w.get('month') else ""
        w_str = w.get("week_of_month") or w.get("key", "")

        row_vals = [
            ri - 1,
            y_str,
            q_str,
            m_str,
            w_str,
            s.get("vendor", ""),
            s.get("type", ""),
            s.get("risk", "LOW"),
            s.get("cust", ""),
            s.get("orderNo", ""),
            s.get("invoice", ""),
            s.get("prod", ""),
            s.get("qty") if s.get("qty") is not None else 1,
            s.get("text", ""),
            s.get("action", "")
        ]
        for ci, val in enumerate(row_vals, 1):
            cell = ws_sraw.cell(row=ri, column=ci, value=val)
            cell.font = font_bold if is_sel else font_regular
            cell.border = border_thin
            if is_sel:
                cell.fill = fill_pastel_orange
            is_left = ci in (12, 14, 15)
            cell.alignment = Alignment(vertical="center", horizontal="left" if is_left else "center", indent=1 if is_left else 0)

    s_widths = [6, 8, 8, 8, 12, 16, 14, 10, 12, 18, 16, 32, 12, 45, 30]
    for ci, w in enumerate(s_widths, 1):
        ws_sraw.column_dimensions[get_column_letter(ci)].width = w

    # =============================================================
    # [Sheet 5: 서비스raw] (배송raw 바로 다음 배치)
    # =============================================================
    ws_svcraw = wb.create_sheet("서비스raw")
    ws_svcraw.views.sheetView[0].showGridLines = True
    ws_svcraw.freeze_panes = "A2"

    svc_col_names = [
        "연도", "분기", "MONTH", "WEEK", "M&W", "id", "고객명", "DATE", "담당자",
        "채널", "방향", "중분류", "소분류", "제품명", "문의내용", "조치내역", "유통채널"
    ]
    ws_svcraw.append(svc_col_names)
    ws_svcraw.row_dimensions[1].height = 25
    for ci in range(1, len(svc_col_names) + 1):
        cell = ws_svcraw.cell(row=1, column=ci)
        cell.font = font_tbl_h
        cell.fill = fill_slate_header
        cell.alignment = Alignment(vertical="center", horizontal="center")
        cell.border = border_thin

    svc_raw_records = load_clean_service_raw(cur_week, voc_data)

    svc_lookback_keys = prev_week_keys if (is_month or is_quarter or is_year) else set(w["key"] for w in weeks[max(0, p_idx - 4):p_idx])

    if is_week:
        selected_svc = [r for r in svc_raw_records if r.get("weekKey") in target_week_keys]
        lookback_svc = [r for r in svc_raw_records if r.get("weekKey") not in target_week_keys and r.get("weekKey") in svc_lookback_keys]
        older_svc = [r for r in svc_raw_records if r.get("weekKey") not in target_week_keys and r.get("weekKey") not in svc_lookback_keys]
    else:
        selected_svc = [r for r in svc_raw_records if is_item_in_p(r, period_obj)]
        lookback_svc = [r for r in svc_raw_records if not is_item_in_p(r, period_obj) and is_item_in_p(r, prev_period_obj)]
        older_svc = [r for r in svc_raw_records if not is_item_in_p(r, period_obj) and not is_item_in_p(r, prev_period_obj)]
    sorted_svc = [(r, True, False) for r in selected_svc] + [(r, False, True) for r in lookback_svc] + [(r, False, False) for r in older_svc]

    ws_svcraw.auto_filter.ref = f"A1:Q{len(sorted_svc) + 1}"

    for ri, (r, is_sel, is_lookback) in enumerate(sorted_svc, 2):
        ws_svcraw.row_dimensions[ri].height = 20
        if not is_sel and not is_lookback:
            ws_svcraw.row_dimensions[ri].hidden = True

        row_vals = [
            r.get("year", ""), r.get("quarter", ""), r.get("month", ""), r.get("week", ""),
            r.get("mw", ""), r.get("id", ""), r.get("cust", ""), r.get("date", ""),
            r.get("mgr", ""), r.get("channel", ""), r.get("direction", ""),
            r.get("tagB", ""), r.get("tagC", ""), r.get("prod", ""),
            r.get("issue", ""), r.get("act", ""), r.get("mall", "")
        ]
        for ci, val in enumerate(row_vals, 1):
            cell = ws_svcraw.cell(row=ri, column=ci, value=val)
            cell.font = font_bold if is_sel else font_regular
            cell.border = border_thin
            if is_sel:
                cell.fill = fill_pastel_orange
            is_left = ci in (14, 15, 16)  # 제품명(14), 문의내용(15), 조치내역(16) 좌측 정렬
            cell.alignment = Alignment(vertical="center", horizontal="left" if is_left else "center", indent=1 if is_left else 0)

    svc_widths = [8, 9, 9, 8, 12, 18, 12, 14, 11, 12, 12, 14, 16, 30, 45, 35, 14]
    for ci, w in enumerate(svc_widths, 1):
        ws_svcraw.column_dimensions[get_column_letter(ci)].width = w

    # =============================================================
    # [Sheet 6: 클레임사진] (품질/배송/서비스 raw 바로 다음 배치 · 클레임 유형별 정렬)
    # =============================================================
    photo_items = []
    if not is_year:
        photo_items = get_all_claim_photos_for_period(target_period_key or cur_week["key"], voc_data)

    if is_year:
        # 연도 엑셀 추출의 경우 수기 관리 필요 안내 보드 생성
        ws_photo = wb.create_sheet("클레임사진")
        ws_photo.views.sheetView[0].showGridLines = True
        ws_photo.merge_cells("A2:F2")
        ws_photo.row_dimensions[2].height = 38
        apply_box(ws_photo, 2, 1, 2, 6, fill_banner, border_double_bottom)
        t_photo = ws_photo.cell(row=2, column=1, value=f"[CX팀] {period_disp} 클레임 사진 (수기 관리 필요 안내)")
        t_photo.font = font_title
        t_photo.alignment = Alignment(vertical="center", horizontal="center")

        for c in range(1, 7):
            ws_photo.column_dimensions[get_column_letter(c)].width = 24

        ws_photo.merge_cells("A4:F10")
        apply_box(ws_photo, 4, 1, 10, 6, fill_amber_banner, border_thin)
        guide_text = (
            "■ [연도 클레임 사진 수기 관리 안내]\n\n"
            "1. 연도 엑셀 추출의 경우 방대한 파일 용량(수백 장의 고화질 이미지)으로 인해 파일 경량화 및 수기 관리가 필요합니다.\n"
            "2. 원본 사진 확인 경로: X:\\9. 클레임 사진\\2026\\ (주차별 폴더를 통해 직접 확인 & 수기 관리 필요)\n"
            "3. 웹 대시보드 조회: VOC 웹 대시보드 [클레임 사진 갤러리] 탭에서 5KB 초고속 썸네일로 전수 조회가 가능합니다.\n"
            "4. 주간, 월간, 분기 리포트에서는 시트 내 사진이 기간별로 자동 배치됩니다."
        )
        cell_g = ws_photo.cell(row=4, column=1, value=guide_text)
        cell_g.font = Font(name="맑은 고딕", size=11, bold=True, color="92400E")
        cell_g.alignment = Alignment(vertical="center", horizontal="left", wrap_text=True)

    elif photo_items:
        ws_photo = wb.create_sheet("클레임사진")
        ws_photo.views.sheetView[0].showGridLines = True

        # 선택 기간 등록된 클레임 사진 전수 수록 (제한 없이 100% 전수 추출)
        display_items = photo_items

        # Title Banner (A2:D2)
        ws_photo.merge_cells("A2:D2")
        ws_photo.row_dimensions[2].height = 38
        apply_box(ws_photo, 2, 1, 2, 4, fill_banner, border_double_bottom)
        t_photo_text = f"[CX팀] {period_disp} 클레임 사진 (총 {len(display_items)}건 전수 수록)"
        t_photo = ws_photo.cell(row=2, column=1, value=t_photo_text)
        t_photo.font = font_title
        t_photo.alignment = Alignment(vertical="center", horizontal="center")

        # Column widths (A~D each width 34 -> approx 240px wide)
        for c in range(1, 5):
            ws_photo.column_dimensions[get_column_letter(c)].width = 34

        fill_caption = PatternFill(fill_type="solid", fgColor="F8FAFC")
        font_caption = Font(name="맑은 고딕", size=9.5, bold=True, color="1F2937")

        cur_row = 4
        for i, (fp, fn, fld) in enumerate(display_items):
            col = (i % 4) + 1
            if i > 0 and col == 1:
                cur_row += 3

            ws_photo.row_dimensions[cur_row].height = 150    # Photo row
            ws_photo.row_dimensions[cur_row + 1].height = 24 # Caption row
            ws_photo.row_dimensions[cur_row + 2].height = 12 # Spacing row

            if HAS_PIL and OpenpyxlImage is not None:
                try:
                    # 썸네일 캐시를 활용하여 고속 로드 및 메모리 절감
                    thumb_bytes, mime = read_claim_photo_bytes(fld, fn, is_thumb=True)
                    if thumb_bytes:
                        img_buf = io.BytesIO(thumb_bytes)
                        img = OpenpyxlImage(img_buf)
                        img.width = 220
                        img.height = 170
                        cell_ref = f"{get_column_letter(col)}{cur_row}"
                        ws_photo.add_image(img, cell_ref)
                    elif PILImage is not None:
                        with PILImage.open(fp) as im:
                            w, h = im.size
                            scale = min(220 / w, 170 / h)
                            nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
                            img = OpenpyxlImage(fp)
                            img.width = nw
                            img.height = nh
                            cell_ref = f"{get_column_letter(col)}{cur_row}"
                            ws_photo.add_image(img, cell_ref)
                except Exception as img_err:
                    print(f"Warning: Failed to add image {fn}:", img_err)

            label_txt = os.path.splitext(fn)[0]
            if is_month or is_quarter:
                clean_fld = fld.split("(")[0].strip()
                display_label = f"[{clean_fld}] {label_txt}"
            else:
                display_label = label_txt

            cell_lbl = ws_photo.cell(row=cur_row + 1, column=col, value=display_label)
            cell_lbl.font = font_caption
            cell_lbl.alignment = Alignment(vertical="center", horizontal="center")
            cell_lbl.border = border_thin
            cell_lbl.fill = fill_caption

    # =============================================================
    # [Sheet 4: 보상내역서]
    # =============================================================
    ws_comp = wb.create_sheet("보상내역서")
    ws_comp.views.sheetView[0].showGridLines = True
    ws_comp.column_dimensions["A"].width = 46
    ws_comp.column_dimensions["B"].width = 16
    ws_comp.column_dimensions["C"].width = 15
    ws_comp.column_dimensions["D"].width = 16
    ws_comp.column_dimensions["E"].width = 38
    ws_comp.column_dimensions["F"].width = 25

    # Title Banner (A2:F2)
    ws_comp.merge_cells("A2:F2")
    ws_comp.row_dimensions[2].height = 36
    apply_box(ws_comp, 2, 1, 2, 6, fill_banner, border_double_bottom)
    t_c = ws_comp.cell(row=2, column=1, value=f"[CX팀] 품질 클레임 보상 내역 및 수기 제외 관리 ({period_disp})")
    t_c.font = font_title; t_c.alignment = Alignment(vertical="center", horizontal="center")

    # Metadata (Row 4-6)
    ws_comp.cell(row=4, column=1, value=f"● 데이터 추출기간 : {period_disp} ({date_range})").font = font_meta
    ws_comp.cell(row=5, column=1, value="● 데이터 추출 기준 : 고객여정 기준 품질 클레임 보상 신청 및 수기 예외 관리 건 전수").font = font_meta
    for r in range(4, 6):
        ws_comp.row_dimensions[r].height = 18

    # Data Rows (사용자 원칙: 품질 raw 추출 건은 기본 무조건 보상 신청, 수기 제외 건만 배제)
    target_raw_for_comp = selected_raw

    comp_chats = [r for r in target_raw_for_comp if r.get("isComp", True)]
    excluded_chats = [r for r in target_raw_for_comp if not r.get("isComp", True)]
    comp_counts = Counter(r.get("prod", "기타") for r in comp_chats)
    sorted_comp = comp_counts.most_common()

    # Section 1 Header (Row 7)
    ws_comp.cell(row=7, column=1, value=f"1. 품질 클레임 보상 신청 집계 ({period_disp} - 총 {sum(comp_counts.values())}건)").font = font_sec
    ws_comp.row_dimensions[7].height = 24

    # Table Header (Row 9)
    ws_comp.row_dimensions[9].height = 26
    c_h1 = ws_comp.cell(row=9, column=1, value="제품명")
    c_h2 = ws_comp.cell(row=9, column=2, value=period_disp)
    for c in (c_h1, c_h2):
        c.font = font_tbl_h; c.fill = fill_teal_header; c.alignment = Alignment(vertical="center", horizontal="center"); c.border = border_thin

    cur_r = 10
    for pname, pcnt in sorted_comp:
        ws_comp.row_dimensions[cur_r].height = 20
        c1 = ws_comp.cell(row=cur_r, column=1, value=pname)
        c2 = ws_comp.cell(row=cur_r, column=2, value=pcnt)
        c1.font = font_regular; c1.alignment = Alignment(vertical="center", horizontal="left", indent=1); c1.border = border_thin
        c2.font = font_regular; c2.alignment = Alignment(vertical="center", horizontal="right"); c2.border = border_thin; c2.number_format = "#,##0"
        cur_r += 1

    # Total Row
    ws_comp.row_dimensions[cur_r].height = 24
    f1 = ws_comp.cell(row=cur_r, column=1, value="총합계")
    f2 = ws_comp.cell(row=cur_r, column=2, value=sum(comp_counts.values()))
    f1.font = font_bold; f1.alignment = Alignment(vertical="center", horizontal="center"); f1.border = border_double_bottom; f1.fill = fill_total
    f2.font = font_bold; f2.alignment = Alignment(vertical="center", horizontal="right"); f2.border = border_double_bottom; f2.fill = fill_total; f2.number_format = "#,##0"

    # Section 2: 보상 제외 내역 (수기 예외 관리)
    cur_r += 3
    ws_comp.row_dimensions[cur_r].height = 22
    sec2_t = ws_comp.cell(row=cur_r, column=1, value=f"2. 보상 제외 내역 (수기 예외 관리 - 총 {len(excluded_chats)}건)")
    sec2_t.font = font_sec

    cur_r += 1
    ws_comp.row_dimensions[cur_r].height = 18
    sec2_desc = ws_comp.cell(row=cur_r, column=1, value="※ 단순 변심 교환, 고객 귀책 파손, 중복 접수, 정상 판정 등으로 보상 신청 목록에서 제외된 내역입니다.")
    sec2_desc.font = font_muted

    cur_r += 2
    ws_comp.row_dimensions[cur_r].height = 25
    ex_headers = ["대상 제품명", "고객명", "문의일자", "클레임 유형", "고객 불만 내용 원문", "보상 제외 사유"]
    for ci, h_txt in enumerate(ex_headers, 1):
        cell = ws_comp.cell(row=cur_r, column=ci, value=h_txt)
        cell.font = font_tbl_h
        cell.fill = fill_slate_header
        cell.alignment = Alignment(vertical="center", horizontal="center")
        cell.border = border_thin

    if excluded_chats:
        for ex_r in excluded_chats:
            cur_r += 1
            ws_comp.row_dimensions[cur_r].height = 22
            c_p = ws_comp.cell(row=cur_r, column=1, value=ex_r.get("prod", "기타"))
            c_c = ws_comp.cell(row=cur_r, column=2, value=ex_r.get("cust", "고객"))
            c_d = ws_comp.cell(row=cur_r, column=3, value=ex_r.get("date", "-"))
            c_t = ws_comp.cell(row=cur_r, column=4, value=ex_r.get("tagB", "") or ex_r.get("tagC", "") or "-")
            c_i = ws_comp.cell(row=cur_r, column=5, value=ex_r.get("issue", "-"))
            c_r = ws_comp.cell(row=cur_r, column=6, value=ex_r.get("exReason", "관리자 수기 제외"))

            c_p.font = font_regular; c_p.alignment = Alignment(vertical="center", horizontal="left", indent=1); c_p.border = border_thin
            c_c.font = font_bold; c_c.alignment = Alignment(vertical="center", horizontal="center"); c_c.border = border_thin
            c_d.font = font_regular; c_d.alignment = Alignment(vertical="center", horizontal="center"); c_d.border = border_thin
            c_t.font = font_regular; c_t.alignment = Alignment(vertical="center", horizontal="center"); c_t.border = border_thin
            c_i.font = font_muted; c_i.alignment = Alignment(vertical="center", horizontal="left"); c_i.border = border_thin
            c_r.font = Font(name="맑은 고딕", size=9.5, bold=True, color="9F1239"); c_r.alignment = Alignment(vertical="center", horizontal="center"); c_r.border = border_thin; c_r.fill = fill_rose_banner
    else:
        cur_r += 1
        ws_comp.row_dimensions[cur_r].height = 24
        ws_comp.merge_cells(start_row=cur_r, start_column=1, end_row=cur_r, end_column=6)
        c_emp = ws_comp.cell(row=cur_r, column=1, value="※ 해당 기간 수기 보상 제외 내역 없음 (품질 클레임 전건 정상 보상 신청)")
        c_emp.font = font_regular; c_emp.alignment = Alignment(vertical="center", horizontal="center"); c_emp.fill = fill_total
        apply_box(ws_comp, cur_r, 1, cur_r, 6, fill=fill_total, border=border_thin)

    # =============================================================
    # [Sheet 5: 보상내역서_전체] (1월~12월 연간 월별 누적 피벗 매트릭스)
    # =============================================================
    ws_comp_all = wb.create_sheet("보상내역서_전체")
    ws_comp_all.views.sheetView[0].showGridLines = True
    
    month_cols = [f"{m}월" for m in range(1, 13)]
    total_cols = 1 + len(month_cols) + 1 # 제품명 + 12개 월 + 총합계 (14열)

    ws_comp_all.column_dimensions["A"].width = 50
    for ci in range(2, total_cols):
        ws_comp_all.column_dimensions[get_column_letter(ci)].width = 11
    ws_comp_all.column_dimensions[get_column_letter(total_cols)].width = 14

    # Title Banner
    ws_comp_all.merge_cells(start_row=2, start_column=1, end_row=2, end_column=total_cols)
    ws_comp_all.row_dimensions[2].height = 36
    apply_box(ws_comp_all, 2, 1, 2, total_cols, fill_banner, border_double_bottom)
    t_c_all = ws_comp_all.cell(row=2, column=1, value=f"[CX팀] 품질 클레임 보상 내역 ({year_str}년 1~12월 월별 누적 매트릭스)")
    t_c_all.font = font_title; t_c_all.alignment = Alignment(vertical="center", horizontal="center")

    # Metadata
    ws_comp_all.cell(row=4, column=1, value=f"● 데이터 추출기간 : {year_str}년 연간 월별 누적 (1월 ~ 12월 전수)").font = font_meta
    ws_comp_all.cell(row=5, column=1, value="● 데이터 추출 기준 : 고객여정 기준 품질 클레임 보상/교환 조치 전수 집계 (실제품 규격별 · 월별 추이)").font = font_meta
    ws_comp_all.cell(row=6, column=1, value=f"보상내역서_전체 ({year_str}년 월별 추이 피벗 매트릭스)").font = font_sec
    for r in range(4, 7):
        ws_comp_all.row_dimensions[r].height = 18

    # Table Header (Row 8)
    ws_comp_all.row_dimensions[8].height = 26
    c_a_h1 = ws_comp_all.cell(row=8, column=1, value="제품명")
    c_a_h1.font = font_tbl_h; c_a_h1.fill = fill_slate_header; c_a_h1.alignment = Alignment(vertical="center", horizontal="center"); c_a_h1.border = border_thin
    
    # 현재 월(cur_month_num) 하이라이트용
    cur_m_match = re.search(r'(\d+)', str(cur_week.get("month", "10")))
    cur_m_num = int(cur_m_match.group(1)) if cur_m_match else 10

    for idx, m_lbl in enumerate(month_cols, 2):
        cell = ws_comp_all.cell(row=8, column=idx, value=m_lbl)
        is_cur = (idx - 1 == cur_m_num)
        cell.font = font_tbl_h
        cell.fill = fill_teal_header if is_cur else fill_slate_header
        cell.alignment = Alignment(vertical="center", horizontal="center")
        cell.border = border_thin
    c_a_last = ws_comp_all.cell(row=8, column=total_cols, value="총합계")
    c_a_last.font = font_tbl_h; c_a_last.fill = fill_slate_header; c_a_last.alignment = Alignment(vertical="center", horizontal="center"); c_a_last.border = border_thin

    # Matrix Data Aggregation (월별 1~12월 기준)
    matrix = defaultdict(lambda: defaultdict(int))
    month_totals = [0] * 12
    grand_total = 0

    for r in raw_records:
        if not r.get("isComp", True):
            continue
        r_year = str(r.get("year", year_str))
        if r_year != str(year_str):
            continue
        m_str = str(r.get("reportMonth") or r.get("month", ""))
        m_match = re.search(r'(\d+)', m_str)
        if not m_match:
            continue
        m_idx = int(m_match.group(1)) - 1
        if 0 <= m_idx < 12:
            m_col_name = f"{m_idx + 1}월"
            pname = r.get("prod", "기타")
            matrix[pname][m_col_name] += 1
            matrix[pname]["total"] += 1
            month_totals[m_idx] += 1
            grand_total += 1

    sorted_matrix = sorted(matrix.items(), key=lambda x: x[1]["total"], reverse=True)

    cur_r = 9
    for pname, row_map in sorted_matrix:
        ws_comp_all.row_dimensions[cur_r].height = 20
        c1 = ws_comp_all.cell(row=cur_r, column=1, value=pname)
        c1.font = font_regular; c1.alignment = Alignment(vertical="center", horizontal="left", indent=1); c1.border = border_thin
        for idx, m_lbl in enumerate(month_cols, 2):
            val = row_map.get(m_lbl, 0)
            cell = ws_comp_all.cell(row=cur_r, column=idx, value=val if val > 0 else "")
            cell.font = font_bold if val > 0 else font_muted
            cell.alignment = Alignment(vertical="center", horizontal="right"); cell.border = border_thin
            if val > 0: cell.number_format = "#,##0"
        c_tot = ws_comp_all.cell(row=cur_r, column=total_cols, value=row_map["total"])
        c_tot.font = font_bold; c_tot.alignment = Alignment(vertical="center", horizontal="right"); c_tot.border = border_thin; c_tot.number_format = "#,##0"
        cur_r += 1

    # Total Row
    ws_comp_all.row_dimensions[cur_r].height = 24
    f_all_1 = ws_comp_all.cell(row=cur_r, column=1, value="총합계")
    f_all_1.font = font_bold; f_all_1.alignment = Alignment(vertical="center", horizontal="center"); f_all_1.border = border_double_bottom; f_all_1.fill = fill_total
    for idx, m_tot in enumerate(month_totals, 2):
        cell = ws_comp_all.cell(row=cur_r, column=idx, value=m_tot)
        cell.font = font_bold; cell.alignment = Alignment(vertical="center", horizontal="right"); cell.border = border_double_bottom; cell.fill = fill_total
        cell.number_format = "#,##0"
    f_grand = ws_comp_all.cell(row=cur_r, column=total_cols, value=grand_total)
    f_grand.font = font_bold; f_grand.alignment = Alignment(vertical="center", horizontal="right"); f_grand.border = border_double_bottom; f_grand.fill = fill_total; f_grand.number_format = "#,##0"

    # 수기 제외 건수 월별 참고 행 (별도 표시)
    cur_r += 2
    ws_comp_all.row_dimensions[cur_r].height = 22
    ex_row_label = ws_comp_all.cell(row=cur_r, column=1, value="[참고] 수기 보상 제외 건수 (월별 예외 관리)")
    ex_row_label.font = Font(name="맑은 고딕", size=9.5, bold=True, color="9F1239")
    ex_row_label.alignment = Alignment(vertical="center", horizontal="left", indent=1)
    ex_row_label.border = border_thin
    ex_row_label.fill = fill_rose_banner

    # 월별 제외 건수 집계
    ex_month_totals = [0] * 12
    ex_grand_total = 0
    for r in raw_records:
        if r.get("isComp", True):
            continue
        r_year = str(r.get("year", year_str))
        if r_year != str(year_str):
            continue
        m_str = str(r.get("month", ""))
        m_match = re.search(r'(\d+)', m_str)
        if not m_match:
            continue
        m_idx = int(m_match.group(1)) - 1
        if 0 <= m_idx < 12:
            ex_month_totals[m_idx] += 1
            ex_grand_total += 1

    for idx, ex_cnt in enumerate(ex_month_totals, 2):
        c_ex = ws_comp_all.cell(row=cur_r, column=idx, value=ex_cnt if ex_cnt > 0 else "-")
        c_ex.font = Font(name="맑은 고딕", size=9.5, bold=(ex_cnt > 0), color="9F1239" if ex_cnt > 0 else "9CA3AF")
        c_ex.alignment = Alignment(vertical="center", horizontal="right")
        c_ex.border = border_thin
        c_ex.fill = fill_rose_banner
        if ex_cnt > 0: c_ex.number_format = "#,##0"

    c_ex_tot = ws_comp_all.cell(row=cur_r, column=total_cols, value=ex_grand_total)
    c_ex_tot.font = Font(name="맑은 고딕", size=9.5, bold=True, color="9F1239")
    c_ex_tot.alignment = Alignment(vertical="center", horizontal="right")
    c_ex_tot.border = border_thin
    c_ex_tot.fill = fill_rose_banner
    c_ex_tot.number_format = "#,##0"

    # =============================================================
    # Section 2: 연간 수기 보상 제외 내역 상세 리스트 (총 N건)
    # =============================================================
    cur_r += 3
    ws_comp_all.row_dimensions[cur_r].height = 24
    all_year_excluded = [
        r for r in raw_records
        if not r.get("isComp", True) and str(r.get("year", year_str)) == str(year_str)
    ]
    sec2_t = ws_comp_all.cell(
        row=cur_r, column=1,
        value=f"2. {year_str}년 연간 수기 보상 제외 내역 상세 리스트 (총 {len(all_year_excluded)}건)"
    )
    sec2_t.font = font_sec

    cur_r += 1
    ws_comp_all.row_dimensions[cur_r].height = 18
    sec2_desc = ws_comp_all.cell(
        row=cur_r, column=1,
        value="※ 연간 피벗 매트릭스에서 제외 처리된 건들의 상세 명단입니다. (단순 변심 교환, 고객 귀책 파손, 중복 접수, 정상 판정 등)"
    )
    sec2_desc.font = font_muted

    cur_r += 2
    ws_comp_all.row_dimensions[cur_r].height = 25
    ex_headers = ["대상 제품명", "고객명", "문의일자", "클레임 유형", "고객 불만 내용 원문", "보상 제외 사유"]
    for ci, h_txt in enumerate(ex_headers, 1):
        cell = ws_comp_all.cell(row=cur_r, column=ci, value=h_txt)
        cell.font = font_tbl_h
        cell.fill = fill_slate_header
        cell.alignment = Alignment(vertical="center", horizontal="center")
        cell.border = border_thin

    if all_year_excluded:
        for ex_r in all_year_excluded:
            cur_r += 1
            ws_comp_all.row_dimensions[cur_r].height = 22
            c_p = ws_comp_all.cell(row=cur_r, column=1, value=ex_r.get("prod", "기타"))
            c_c = ws_comp_all.cell(row=cur_r, column=2, value=ex_r.get("cust", "고객"))
            c_d = ws_comp_all.cell(row=cur_r, column=3, value=ex_r.get("date", "-"))
            c_t = ws_comp_all.cell(row=cur_r, column=4, value=ex_r.get("tagB", "") or ex_r.get("tagC", "") or "-")
            c_i = ws_comp_all.cell(row=cur_r, column=5, value=ex_r.get("issue", "-"))
            c_r = ws_comp_all.cell(row=cur_r, column=6, value=ex_r.get("exReason", "관리자 수기 제외"))

            c_p.font = font_regular; c_p.alignment = Alignment(vertical="center", horizontal="left", indent=1); c_p.border = border_thin
            c_c.font = font_bold; c_c.alignment = Alignment(vertical="center", horizontal="center"); c_c.border = border_thin
            c_d.font = font_regular; c_d.alignment = Alignment(vertical="center", horizontal="center"); c_d.border = border_thin
            c_t.font = font_regular; c_t.alignment = Alignment(vertical="center", horizontal="center"); c_t.border = border_thin
            c_i.font = font_muted; c_i.alignment = Alignment(vertical="center", horizontal="left"); c_i.border = border_thin
            c_r.font = Font(name="맑은 고딕", size=9.5, bold=True, color="9F1239"); c_r.alignment = Alignment(vertical="center", horizontal="center"); c_r.border = border_thin; c_r.fill = fill_rose_banner
    else:
        cur_r += 1
        ws_comp_all.row_dimensions[cur_r].height = 24
        ws_comp_all.merge_cells(start_row=cur_r, start_column=1, end_row=cur_r, end_column=6)
        c_emp = ws_comp_all.cell(row=cur_r, column=1, value=f"※ {year_str}년 연간 수기 보상 제외 내역 없음 (품질 클레임 전건 정상 보상 신청)")
        c_emp.font = font_regular; c_emp.alignment = Alignment(vertical="center", horizontal="center"); c_emp.fill = fill_total
        apply_box(ws_comp_all, cur_r, 1, cur_r, 6, fill=fill_total, border=border_thin)

    return wb, period_disp


def generate_report_excel_bytes(target_period_key=None, memos=None, insights=None):
    wb, period_disp = build_report_excel(target_period_key, memos=memos, insights=insights)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue(), period_disp


if __name__ == "__main__":
    print("▶ 엑셀 생성 테스트 시작...")
    test_memos = [
        {"text": "10월 2주차 물티슈 캡/라벨 불만 집중 모니터링 진행 중", "author": "김민정", "date": "2026-10-21"},
        {"text": "CJ택배 파손율 개선을 위한 에어캡 포장 보강 요청 완료", "author": "이진우", "date": "2026-10-22"}
    ]
    test_insights = {
        "quality": "📌 [이슈 코멘트 & 액션 플랜] 발진(3건) 및 캡단차(2건) 발생 건에 대해 해당 LOT 생산 샘플 긴급 공정 검사 진행.",
        "delivery": "📌 [이슈 코멘트 & 액션 플랜] 파손반송 건수 3건 발생으로 포장 완충재 규격 상향 테스트 진행 중.",
        "service": "📌 [이슈 코멘트 & 액션 플랜] 사은행사 문의 관련 상담 스크립트 배포 및 1차 처리율 제고."
    }
    wb, p_disp = build_report_excel("2026-W41", memos=test_memos, insights=test_insights)
    out_path = Path(r"C:\Users\hshwa\.gemini\antigravity\brain\b03b6ae5-cbf8-495a-90ec-dc58447986ca\scratch\final_verified_report.xlsx")
    wb.save(out_path)
    print(f"★ 엑셀 생성 성공! 경로: {out_path} (크기: {out_path.stat().st_size:,} bytes)")
