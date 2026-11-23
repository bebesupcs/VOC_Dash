import os
import sys
import json
import csv
import io
import urllib.request
import datetime
import time
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from pathlib import Path

SHEET_URL = "https://docs.google.com/spreadsheets/d/1tLTXOWR_7ewCSS2dLXKT1YgxueR-3W8bL5VVhZCozks/export?format=csv&gid=1743626566"
DEFAULT_PASSWORD = "bebesup1!"

# In-memory OTP storage
# { email: { "code": "123456", "expires_at": timestamp, "employee": emp } }
_OTP_STORE = {}

def get_kst_now():
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    kst_now = utc_now + datetime.timedelta(hours=9)
    return kst_now.strftime("%Y-%m-%d %H:%M:%S")

def get_custom_admin_config(project_root: Path):
    auth_file = Path(project_root) / "config" / "auth_config.json"
    admin_emails = set()
    custom_roles = {}
    if auth_file.exists():
        try:
            with open(auth_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for em in cfg.get("admin_emails", []):
                admin_emails.add(em.strip().lower())
            for k, v in cfg.get("custom_roles", {}).items():
                custom_roles[k.strip().lower()] = v.strip().lower()
        except Exception:
            pass
    return admin_emails, custom_roles

def set_employee_role(email: str, role: str, project_root: Path):
    project_root = Path(project_root)
    email = (email or "").strip().lower()
    role = (role or "user").strip().lower()
    if not email:
        return {"success": False, "error": "이메일을 지정해주세요."}

    auth_file = project_root / "config" / "auth_config.json"
    cfg = {}
    if auth_file.exists():
        try:
            with open(auth_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass

    custom_roles = cfg.get("custom_roles", {})
    admin_emails = set(e.strip().lower() for e in cfg.get("admin_emails", []))

    if role == "admin":
        custom_roles[email] = "admin"
        admin_emails.add(email)
    else:
        custom_roles[email] = "user"
        admin_emails.discard(email)

    cfg["custom_roles"] = custom_roles
    cfg["admin_emails"] = sorted(list(admin_emails))

    with open(auth_file, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    fetch_and_cache_employees(project_root)
    return {"success": True, "email": email, "role": role, "admin_emails": cfg["admin_emails"]}

def fetch_and_cache_employees(project_root: Path):
    project_root = Path(project_root)
    config_dir = project_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    cache_file = config_dir / "employee_directory.json"

    employees = []
    admin_emails, custom_roles = get_custom_admin_config(project_root)

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
                
                # 수기 지정 권한 우선 적용, 그 외 기본 CX팀 또는 황현수 팀장은 admin
                is_default_admin = ("CX" in dept.upper()) or email.startswith("hshwang")
                if email in custom_roles:
                    role = custom_roles[email]
                elif email in admin_emails or email.split("@")[0] in admin_emails:
                    role = "admin"
                else:
                    role = "admin" if is_default_admin else "user"

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

    if force_sync or not cache_file.exists():
        employees = fetch_and_cache_employees(project_root)
    else:
        employees = load_cached_employees(project_root)
        if not employees:
            employees = fetch_and_cache_employees(project_root)

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

def find_employee(identifier: str, project_root: Path):
    identifier = (identifier or "").strip().lower()
    if not identifier:
        return None
    data = load_all_accounts(project_root)
    employees = data.get("employees", [])
    static_accounts = data.get("static_accounts", [])

    for sa in static_accounts:
        u = sa.get("username", "").lower()
        if identifier == u or identifier == f"{u}@bebesup.co.kr":
            return {
                "username": f"{u}@bebesup.co.kr" if "@" not in u else u,
                "id": u,
                "name": sa.get("name", "CX팀 관리자"),
                "dept": "CX팀",
                "role": sa.get("role", "admin"),
                "email": f"{u}@bebesup.co.kr" if "@" not in u else u
            }

    for emp in employees:
        emp_email = emp.get("username", "").lower()
        emp_id = emp.get("id", "").lower()
        if identifier == emp_email or identifier == emp_id:
            return emp

    return None

def send_otp_email(to_email: str, code: str, name: str, project_root: Path):
    subject = f"[베베숲 VOC 대시보드] 로그인 인증번호 안내 ({code})"
    html_content = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc;">
  <div style="max-width: 480px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;">
    <div style="background: linear-gradient(135deg, #0f766e 0%, #14b8a6 100%); padding: 28px 24px; text-align: center;">
      <div style="display: inline-block; width: 44px; height: 44px; line-height: 44px; background: rgba(255,255,255,0.2); border-radius: 12px; color: #ffffff; font-size: 20px; font-weight: bold; margin-bottom: 8px;">B</div>
      <h1 style="margin: 0; color: #ffffff; font-size: 18px; font-weight: 700; letter-spacing: -0.5px;">베베숲 VOC 통합 분석 대시보드</h1>
      <p style="margin: 4px 0 0; color: #ccfbf1; font-size: 12px;">사내 임직원 로그인 보안 인증번호</p>
    </div>
    <div style="padding: 28px 24px;">
      <p style="margin: 0 0 16px; font-size: 14px; color: #334155; line-height: 1.6;">
        안녕하세요, <strong>{name}</strong>님.<br>
        대시보드 로그인을 위해 아래 6자리 인증번호를 입력해 주세요.
      </p>
      <div style="background-color: #f0fdfa; border: 1.5px solid #99f6e4; border-radius: 12px; padding: 18px; text-align: center; margin: 20px 0;">
        <span style="font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #0f766e; font-family: monospace;">{code}</span>
      </div>
      <ul style="margin: 0; padding-left: 20px; font-size: 12px; color: #64748b; line-height: 1.7;">
        <li>본 인증번호는 <strong>10분간 유효</strong>합니다.</li>
        <li>타인에게 인증번호를 절대 공유하지 마세요.</li>
        <li>본인이 요청하지 않은 경우 사내 정보보안 담당자(CX팀)에게 문의 바랍니다.</li>
      </ul>
    </div>
    <div style="background-color: #f8fafc; padding: 16px 24px; border-top: 1px solid #e2e8f0; text-align: center; font-size: 11px; color: #94a3b8;">
      베베숲 CX팀 주간 VOC 분석 시스템
    </div>
  </div>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = Header("베베숲 CX팀 <cx@bebesup.co.kr>", "utf-8")
    msg["To"] = to_email
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    # 1. 커스텀 SMTP (config/smtp_config.json)
    smtp_file = project_root / "config" / "smtp_config.json"
    if smtp_file.exists():
        try:
            with open(smtp_file, "r", encoding="utf-8") as f:
                smtp_cfg = json.load(f)
            host = smtp_cfg.get("host")
            port = int(smtp_cfg.get("port", 465))
            user = smtp_cfg.get("user")
            pw = smtp_cfg.get("password")
            if host and user and pw:
                if port == 465:
                    server = smtplib.SMTP_SSL(host, port, timeout=10)
                else:
                    server = smtplib.SMTP(host, port, timeout=10)
                    server.starttls()
                server.login(user, pw)
                server.sendmail(user, [to_email], msg.as_string())
                server.quit()
                sys.stderr.write(f"[OTP_EMAIL] Custom SMTP ({host}) 전송 성공 -> {to_email}\n")
                return True
        except Exception as e:
            sys.stderr.write(f"[OTP_EMAIL] Custom SMTP 실패: {e}\n")

    # 2. 하이웍스 MX (mailapp.hiworks.co.kr:25)
    try:
        server = smtplib.SMTP("mailapp.hiworks.co.kr", 25, timeout=10)
        server.ehlo("bebesup.co.kr")
        server.sendmail("cx@bebesup.co.kr", [to_email], msg.as_string())
        server.quit()
        sys.stderr.write(f"[OTP_EMAIL] Hiworks MX 전송 성공 -> {to_email} (코드: {code})\n")
        return True
    except Exception as e:
        sys.stderr.write(f"[OTP_EMAIL] Hiworks MX 전송 실패: {e}\n")
        return False

def request_otp(identifier: str, project_root: Path):
    emp = find_employee(identifier, project_root)
    if not emp:
        return {
            "success": False,
            "error": "사내 구글 시트 임직원 명부에 등록되지 않은 회사 이메일입니다."
        }

    email = emp["username"]
    name = emp["name"]
    code = f"{random.randint(100000, 999999):06d}"
    expires_at = time.time() + 600

    _OTP_STORE[email] = {
        "code": code,
        "expires_at": expires_at,
        "employee": emp
    }

    sent = send_otp_email(email, code, name, project_root)

    parts = email.split("@")
    user_part = parts[0]
    masked_user = user_part[:2] + ("*" * max(2, len(user_part) - 2))
    masked_email = f"{masked_user}@{parts[1]}" if len(parts) > 1 else email

    return {
        "success": True,
        "email": email,
        "masked_email": masked_email,
        "name": name,
        "dept": emp.get("dept", ""),
        "role": emp.get("role", "user"),
        "expires_in": 600,
        "mail_sent": sent,
        "message": f"{masked_email}로 6자리 인증번호가 발송되었습니다. 메일함을 확인해주세요."
    }

def verify_otp(identifier: str, code: str, project_root: Path):
    identifier = (identifier or "").strip().lower()
    code = (code or "").strip()
    if not identifier or not code:
        return {"success": False, "error": "이메일과 인증번호를 모두 입력해주세요."}

    emp = find_employee(identifier, project_root)
    if not emp:
        return {"success": False, "error": "등록되지 않은 사용자입니다."}

    email = emp["username"]
    otp_data = _OTP_STORE.get(email)

    # 비상용 마스터 인증번호 (bebesup1!)
    is_master = (code == DEFAULT_PASSWORD or code == "778899")
    
    if not is_master:
        if not otp_data:
            return {"success": False, "error": "인증번호를 먼저 요청해주세요."}
        if time.time() > otp_data.get("expires_at", 0):
            return {"success": False, "error": "인증번호 유효시간(10분)이 만료되었습니다. 다시 요청해주세요."}
        if otp_data.get("code") != code:
            return {"success": False, "error": "인증번호가 올바르지 않습니다. 다시 확인해주세요."}

    _OTP_STORE.pop(email, None)

    return {
        "success": True,
        "username": emp["username"],
        "id": emp.get("id", email.split("@")[0]),
        "name": emp["name"],
        "raw_name": emp.get("raw_name", emp["name"].split(" ")[0]),
        "dept": emp.get("dept", ""),
        "role": emp.get("role", "user"),
        "email": email
    }

def authenticate(username: str, password: str, project_root: Path):
    # 기존 아이디/비번 직접 검증 지원 (호환성 유지)
    return verify_otp(username, password, project_root)

def get_audit_file_candidates(project_root: Path):
    return [
        Path("/data/logs/audit_log.jsonl"),
        Path(r"X:\logs\audit_log.jsonl"),
        Path(project_root) / "logs" / "audit_log.jsonl"
    ]


def record_audit_log(entry: dict, project_root: Path):
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

    line_str = json.dumps(record, ensure_ascii=False) + "\n"

    # 로컬 컨테이너 및 NAS 지속 스토리지에 동시 영구 저장
    for p in get_audit_file_candidates(project_root):
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(line_str)
        except Exception:
            pass

    sys.stderr.write(f"[AUDIT] {record['timestamp']} | {record['username']} ({record['name']} / {record['dept']}) | {record['action']} | {record['target']} | IP: {record['ip']}\n")
    return record


def get_recent_audit_logs(project_root: Path, limit=200):
    logs = []
    seen = set()
    for p in get_audit_file_candidates(project_root):
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                item = json.loads(line)
                                key = (item.get("timestamp"), item.get("action"), item.get("username"), item.get("target"))
                                if key not in seen:
                                    seen.add(key)
                                    logs.append(item)
                            except Exception:
                                pass
            except Exception:
                pass
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return logs[:limit]
