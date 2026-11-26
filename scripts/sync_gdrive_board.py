"""
구글 스프레드시트 게시판 데이터 -> NAS 엑셀(게시판_통합운영.xlsx) 자동 동기화 모듈
- Google Sheet URL: https://docs.google.com/spreadsheets/d/175Sv85WFWRww9CHpG7HapYHsCq_3yKRx594lCiXAiXI/edit?gid=2031984485
- 대상 파일: X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\raw\게시판 데이터 원본\게시판_통합운영.xlsx
- 원본 템플릿의 디자인, 서식, 열 너비, 수식(=SUM), 테두리를 100% 보존하면서 구글 시트의 수치 데이터만 깨끗하게 갱신
"""

import os
import sys
import csv
import io
import urllib.request
import datetime
import openpyxl
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_FILE = PROJECT_ROOT / "templates" / "게시판_통합운영_template.xlsx"

SHEET_ID = "175Sv85WFWRww9CHpG7HapYHsCq_3yKRx594lCiXAiXI"
SHEET_GID = "2031984485"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"

NAS_BOARD_FILE = Path(r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\raw\게시판 데이터 원본\게시판_통합운영.xlsx")
BACKUP_BOARD_FILE = Path(r"D:\VOC_SHARE\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\raw\게시판 데이터 원본\게시판_통합운영.xlsx")
CONTAINER_BOARD_FILE = Path(r"/data/26년/raw/게시판 데이터 원본/게시판_통합운영.xlsx")


def norm_dt(v):
    if not v:
        return None
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.strftime("%Y-%m-%d")
    s = str(v).strip().replace(".", "-").replace(" ", "").rstrip("-")
    parts = s.split("-")
    if len(parts) == 3:
        try:
            return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        except Exception:
            pass
    return None


def sync_board_from_google_sheet(log_func=print):
    """
    구글 시트의 최신 데이터를 가져와 기존 원본 디자인 서식 템플릿에 데이터만 갱신하여 저장
    """
    log_func("▶ [게시판 구글 시트 연동] 최신 수기접수 데이터 다운로드 및 서식 보존 갱신 중...")

    # 1. 원본 디자인 템플릿 로드
    tpl_path = None
    container_tpl = PROJECT_ROOT / "templates" / "게시판_통합운영_template.xlsx"
    for cand in [TEMPLATE_FILE, container_tpl, Path("/app/templates/게시판_통합운영_template.xlsx"), NAS_BOARD_FILE, CONTAINER_BOARD_FILE, BACKUP_BOARD_FILE]:
        if cand.exists() and cand.stat().st_size > 1024:
            tpl_path = cand
            break

    if not tpl_path:
        log_func("  ❌ 게시판 원본 디자인 템플릿을 찾을 수 없습니다.")
        return False, "템플릿 없음"

    try:
        wb = openpyxl.load_workbook(str(tpl_path))
        sheet_name = "게시판 25~" if "게시판 25~" in wb.sheetnames else wb.sheetnames[0]
        ws = wb[sheet_name]

        # 템플릿 열 매핑 (2행 기준)
        tpl_col_map = {}
        for c in range(1, ws.max_column + 1):
            val = ws.cell(2, c).value
            if val:
                tpl_col_map[str(val).strip()] = c

        # 템플릿 일자 매핑 (4행부터)
        tpl_date_row = {}
        for r in range(4, ws.max_row + 1):
            val = ws.cell(r, 1).value
            ndt = norm_dt(val)
            if ndt:
                tpl_date_row[ndt] = r

        # 2. 구글 스프레드시트 데이터 다운로드
        req = urllib.request.Request(CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8", errors="ignore")

        gs_rows = list(csv.reader(io.StringIO(text)))
        if len(gs_rows) < 10:
            log_func(f"  ⚠️ 구글 시트 행 수 부족 ({len(gs_rows)}행)으로 건너뜁니다.")
            return False, "데이터 부족"

        gs_header = [c.strip() for c in gs_rows[2]]
        gs_col_map = {}
        for idx, col_name in enumerate(gs_header):
            if col_name in tpl_col_map and col_name not in ["일자"]:
                gs_col_map[idx] = col_name

        # 3. 데이터 셀만 정밀 갱신 (서식, 폰트, 테두리, 수식 그대로 보존)
        # 3-1. 3행(상단 전체합계 요약행) 갱신
        if len(gs_rows) > 3 and "합계" in gs_rows[3][1]:
            summary_row = gs_rows[3]
            for gs_idx, mall_name in gs_col_map.items():
                if gs_idx < len(summary_row):
                    raw_val = summary_row[gs_idx].strip()
                    if raw_val and raw_val != "":
                        try:
                            num = int(float(raw_val.replace(",", "")))
                            ws.cell(3, tpl_col_map[mall_name]).value = num
                        except Exception:
                            pass

        # 3-2. 4행부터 일자별 데이터 및 일자별 합계 갱신
        updated_dates = 0
        for r_data in gs_rows[4:]:
            if len(r_data) < 8:
                continue
            dt_str = r_data[6].strip()
            ndt = norm_dt(dt_str)
            if not ndt or ndt not in tpl_date_row:
                continue

            row_idx = tpl_date_row[ndt]
            updated_dates += 1
            for gs_idx, mall_name in gs_col_map.items():
                if gs_idx < len(r_data):
                    raw_val = r_data[gs_idx].strip()
                    cell_target = ws.cell(row_idx, tpl_col_map[mall_name])
                    if raw_val and raw_val != "":
                        try:
                            num = int(float(raw_val.replace(",", "")))
                            cell_target.value = num if num > 0 else 0
                        except Exception:
                            cell_target.value = raw_val
                    else:
                        pass

        # 4. 대상 경로에 저장
        target_paths = [NAS_BOARD_FILE, BACKUP_BOARD_FILE, CONTAINER_BOARD_FILE]
        saved_any = False
        for tp in target_paths:
            try:
                if tp.parent.parent.exists() or tp.parent.exists():
                    tp.parent.mkdir(parents=True, exist_ok=True)
                    wb.save(str(tp))
                    saved_any = True
            except Exception:
                pass

        log_func(f"  ✨ 원본 디자인·서식 100% 유지하며 구글 시트 최신 {updated_dates}일치 데이터 동기화 완료!")
        return True, f"총 {updated_dates}일치 서식 보존 갱신 완료"
    except Exception as e:
        log_func(f"  ❌ 서식 보존 동기화 오류: {e}")
        return False, str(e)


if __name__ == "__main__":
    sync_board_from_google_sheet(print)
