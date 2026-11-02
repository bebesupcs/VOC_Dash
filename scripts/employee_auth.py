import os
import sys
import json
import csv
import io
import urllib.request
import datetime
from pathlib import Path

SHEET_URL = "https://docs.google.com/spreadsheets/d/1tLTXOWR_7ewCSS2dLXKT1YgxueR-3W8bL5VVhZCozks/export?format=csv&gid=1743626566"
DEFAULT_PASSWORD = "bebesup1!"

def get_kst_now():
    # KST timezone (UTC+9)
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    kst_now = utc_now + datetime.timedelta(hours=9)
    return kst_now.strftime("%Y-%m-%d %H:%M:%S")

def fetch_and_cache_employees(project_root: Path):
    project_root = Path(project_root)
    config_dir = project_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    cache_file = config_dir / "employee_directory.json"

    employees = []
    try:
        req = urllib.request.Request(SHEET_URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            text = resp.read().decode("utf-8")

        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        for r in rows[1:]:
            if len(r) >= 4 and "@" in r[3]:
                dept = r[0].strip()
                name = r[1].strip()
                title = r[2].strip()
                email = r[3].strip().lower()
                phone = r[4].strip() if len(r) > 4 else ""
                
                # CX팀 또는 황현수 팀장 계정은 관리자(admin)
                is_admin = ("CX" in dept.upper()) or email.startswith("hshwang")
                role = "admin" if is_admin else "user"

                employees.append({
                    "username": email,
                    "id": email.split("@")[0],
                    "name": f"{name} {title}".strip(),
                    "raw_name": name,
                    "title": title,
                    "dept": dept,
                    "phone": phone,
                    "role": role,
                    "source": "google_sheet"
                })

        if employees:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "employees": employees,
                    "last_synced": get_kst_now(),
                    "total_count": len(employees)
                }, f, ensure_ascii=False, indent=2)
            sys.stderr.write(f"[EMPLOYEE_AUTH] Google Sheets에서 {len(employees)}명 임직원 정보 동기화 완료\n")
    except Exception as e:
        sys.stderr.write(f"[EMPLOYEE_AUTH] Google Sheets 동기화 실패 (캐시 사용): {e}\n")

    return employees

def load_cached_employees(project_root: Path):
    project_root = Path(project_root)
    cache_file = project_root / "config" / "employee_directory.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("employees", [])
        except Exception:
            pass
    return []

def load_all_accounts(project_root: Path, force_sync=False):
    project_root = Path(project_root)
    cache_file = project_root / "config" / "employee_directory.json"

    # 캐시가 없거나 force_sync이면 구글 시트에서 가져오기
    if force_sync or not cache_file.exists():
        employees = fetch_and_cache_employees(project_root)
    else:
        employees = load_cached_employees(project_root)
        if not employees:
            employees = fetch_and_cache_employees(project_root)

    # 정적 계정(cx, bebesup 등) 병합
    static_accounts = []
    auth_file = project_root / "config" / "auth_config.json"
    if auth_file.exists():
        try:
            with open(auth_file, "r", encoding="utf-8") as f:
                auth_cfg = json.load(f)
                static_accounts = auth_cfg.get("accounts", [])
        except Exception:
            pass

    return {
        "employees": employees,
        "static_accounts": static_accounts
    }

def authenticate(username: str, password: str, project_root: Path):
    username = (username or "").strip().lower()
    password = (password or "").strip()
    if not username or not password:
        return {"success": False, "error": "아이디(회사 이메일)와 비밀번호를 입력해주세요."}

    data = load_all_accounts(project_root)
    static_accounts = data.get("static_accounts", [])
    employees = data.get("employees", [])

    # 1. 정적 관리자/사원 계정 체크
    for sa in static_accounts:
        sa_user = sa.get("username", "").strip().lower()
        if sa_user == username:
            if sa.get("password") == password:
                return {
                    "success": True,
                    "username": sa.get("username"),
                    "name": sa.get("name", "CX팀 관리자"),
                    "dept": "CX팀",
                    "role": sa.get("role", "admin"),
                    "email": sa.get("email", f"{sa_user}@bebesup.co.kr")
                }
            else:
                return {"success": False, "error": "비밀번호가 올바르지 않습니다."}

    # 2. 구글 시트 임직원 계정 체크 (이메일 풀주소 또는 @ 앞 아이디 둘 다 매칭)
    for emp in employees:
        emp_email = emp.get("username", "").lower()
        emp_id = emp.get("id", "").lower()

        if username == emp_email or username == emp_id:
            # 기본 비밀번호 또는 커스텀 비밀번호 체크
            if password == DEFAULT_PASSWORD or password == emp.get("password"):
                return {
                    "success": True,
                    "username": emp["username"],
                    "id": emp["id"],
                    "name": emp["name"],
                    "dept": emp["dept"],
                    "role": emp["role"],
                    "email": emp["username"]
                }
            else:
                return {"success": False, "error": "비밀번호가 올바르지 않습니다. (기본 비밀번호: bebesup1!)"}

    return {
        "success": False,
        "error": "등록되지 않은 회사 이메일입니다. 사내 임직원 명부를 확인해주세요."
    }

def record_audit_log(entry: dict, project_root: Path):
    project_root = Path(project_root)
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    audit_file = logs_dir / "audit_log.jsonl"

    record = {
        "timestamp": get_kst_now(),
        "action": entry.get("action", "UNKNOWN"),
        "username": entry.get("username", "anonymous"),
        "name": entry.get("name", ""),
        "dept": entry.get("dept", ""),
        "role": entry.get("role", "user"),
        "target": entry.get("target", ""),
        "detail": entry.get("detail", ""),
        "ip": entry.get("ip", ""),
        "user_agent": entry.get("user_agent", "")
    }

    try:
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        sys.stderr.write(f"[AUDIT] {record['timestamp']} | {record['username']} ({record['name']} / {record['dept']}) | {record['action']} | {record['target']} | IP: {record['ip']}\n")
    except Exception as e:
        sys.stderr.write(f"[AUDIT_ERROR] 감사 로그 기록 실패: {e}\n")

    return record

def get_recent_audit_logs(project_root: Path, limit=200):
    project_root = Path(project_root)
    audit_file = project_root / "logs" / "audit_log.jsonl"
    logs = []
    if audit_file.exists():
        try:
            with open(audit_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            logs.append(json.loads(line))
                        except Exception:
                            pass
        except Exception:
            pass
    # 최신순 정렬
    logs.reverse()
    return logs[:limit]
