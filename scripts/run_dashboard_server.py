# -*- coding: utf-8 -*-
"""
run_dashboard_server.py
베베숲 VOC 대시보드 항시 가동 웹 서버 (포트 8080)
- 로컬 (http://localhost:8080)
- 사내 네트워크 (http://192.168.0.24:8080) 동시 지원
"""

import http.server
import json
import os
from pathlib import Path
import socketserver
import sys
import threading
from datetime import datetime

# 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PORT = 8080
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIRECTORY = str(PROJECT_ROOT / "dashboard")
CLOUDFLARED_BIN = PROJECT_ROOT / "tools" / "cloudflared.exe"

sync_lock = threading.Lock()
sync_status = {
    "is_syncing": False,
    "last_synced": None,
    "last_result": None
}

tunnel_info = {
    "url": None,
    "proc": None
}

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # 캐시 방지 및 사내망 접속 CORS 허용
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        clean_path = self.path.split("?")[0].rstrip("/")
        if clean_path == "/api/sync/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(sync_status, ensure_ascii=False).encode("utf-8"))
            return
        elif clean_path == "/api/sync":
            self.handle_sync_request()
            return
        elif clean_path == "/api/export_report_excel":
            from urllib.parse import parse_qs, urlparse
            query_params = parse_qs(urlparse(self.path).query)
            target_period = query_params.get("period", [None])[0]
            self.handle_export_excel(target_period)
            return
        elif clean_path == "/api/claim_photos":
            from urllib.parse import parse_qs, urlparse
            query_params = parse_qs(urlparse(self.path).query)
            target_week = query_params.get("week", [None])[0]
            self.handle_claim_photos_list(target_week)
            return
        elif clean_path == "/api/claim_photos/image":
            from urllib.parse import parse_qs, urlparse, unquote
            query_params = parse_qs(urlparse(self.path).query)
            folder = unquote(query_params.get("folder", [""])[0])
            file_name = unquote(query_params.get("file", [""])[0])
            is_thumb = query_params.get("thumb", ["0"])[0] in ("1", "true", "True")
            self.handle_claim_photo_file(folder, file_name, is_thumb=is_thumb)
            return
        elif clean_path == "/api/compensation_overrides":
            self.handle_get_compensation_overrides()
            return
        elif clean_path == "/api/server_info":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            info = {
                "local": f"http://localhost:{PORT}",
                "network": f"http://192.168.0.24:{PORT}",
                "tunnel": tunnel_info.get("url")
            }
            self.wfile.write(json.dumps(info, ensure_ascii=False).encode("utf-8"))
            return
        # 정적 파일(.js, .json, .html, .css) 초고속 GZIP 압축 스트리밍 (54MB -> 5.8MB, 외부 접속 10배 가속)
        accept_encoding = self.headers.get("Accept-Encoding", "")
        if "gzip" in accept_encoding:
            rel_path = clean_path.lstrip("/")
            if not rel_path:
                rel_path = "index.html"
            file_path = Path(DIRECTORY) / rel_path
            if file_path.is_file() and file_path.suffix.lower() in [".js", ".json", ".html", ".css"]:
                gz_cache = file_path.parent / f"{file_path.name}.gz"
                try:
                    mtime = file_path.stat().st_mtime
                    if not gz_cache.exists() or gz_cache.stat().st_mtime < mtime:
                        import gzip
                        with open(file_path, "rb") as f_in, gzip.open(gz_cache, "wb", compresslevel=6) as f_out:
                            f_out.write(f_in.read())
                    if gz_cache.exists():
                        self.send_response(200)
                        mime_map = {
                            ".js": "application/javascript; charset=utf-8",
                            ".json": "application/json; charset=utf-8",
                            ".html": "text/html; charset=utf-8",
                            ".css": "text/css; charset=utf-8",
                        }
                        self.send_header("Content-Type", mime_map.get(file_path.suffix.lower(), "application/octet-stream"))
                        self.send_header("Content-Encoding", "gzip")
                        self.send_header("Content-Length", str(gz_cache.stat().st_size))
                        self.end_headers()
                        with open(gz_cache, "rb") as gf:
                            self.wfile.write(gf.read())
                        return
                except Exception:
                    pass

        try:
            super().do_GET()
        except (ConnectionResetError, BrokenPipeError):
            pass

    def do_POST(self):
        clean_path = self.path.split("?")[0].rstrip("/")
        if clean_path == "/api/sync":
            self.handle_sync_request()
            return
        elif clean_path == "/api/login":
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length) if content_length > 0 else b""
            body_data = {}
            if body_bytes:
                try:
                    body_data = json.loads(body_bytes.decode("utf-8"))
                except Exception:
                    pass
            self.handle_login(body_data)
            return
        elif clean_path == "/api/compensation_overrides":
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length) if content_length > 0 else b""
            body_data = {}
            if body_bytes:
                try:
                    body_data = json.loads(body_bytes.decode("utf-8"))
                except Exception:
                    pass
            self.handle_save_compensation_overrides(body_data)
            return
        elif clean_path == "/api/export_report_excel":
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length) if content_length > 0 else b""
            body_data = {}
            if body_bytes:
                try:
                    body_data = json.loads(body_bytes.decode("utf-8"))
                except Exception:
                    pass
            target_period = body_data.get("period")
            memos = body_data.get("memos", [])
            insights = body_data.get("insights", {})
            self.handle_export_excel(target_period, memos=memos, insights=insights)
            return
        self.send_error(404, "Not Found")

    def handle_export_excel(self, target_period, memos=None, insights=None):
        from urllib.parse import quote
        try:
            sys.path.append(str(Path(__file__).resolve().parent))
            import importlib
            import generate_report_excel
            importlib.reload(generate_report_excel)
            excel_bytes, period_disp = generate_report_excel.generate_report_excel_bytes(
                target_period, memos=memos, insights=insights
            )
            
            safe_name = period_disp.replace(" ", "_").replace("(", "").replace(")", "")
            filename_ascii = f"VOC_report_{target_period or 'latest'}.xlsx"
            filename_utf8 = f"[CX팀]_VOC_분석종합리포트_{safe_name}.xlsx"
            encoded_utf8 = quote(filename_utf8)

            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", f'attachment; filename="{filename_ascii}"; filename*=UTF-8\'\'{encoded_utf8}')
            self.send_header("Content-Length", str(len(excel_bytes)))
            self.end_headers()
            self.wfile.write(excel_bytes)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False).encode("utf-8"))

    def handle_claim_photos_list(self, target_week):
        try:
            sys.path.append(str(Path(__file__).resolve().parent))
            import generate_report_excel
            res = generate_report_excel.get_claim_photos_for_period(target_week)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e), "photos": []}, ensure_ascii=False).encode("utf-8"))

    def handle_claim_photo_file(self, folder, file_name, is_thumb=False):
        try:
            sys.path.append(str(Path(__file__).resolve().parent))
            import generate_report_excel
            img_bytes, mime = generate_report_excel.read_claim_photo_bytes(folder, file_name, is_thumb=is_thumb)
            if not img_bytes:
                self.send_error(404, "Photo Not Found")
                return
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(img_bytes)))
            self.send_header("Cache-Control", "public, max-age=604800, immutable")
            self.end_headers()
            self.wfile.write(img_bytes)
        except Exception as e:
            try:
                self.send_response(500)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"Server Error: {str(e)}".encode("utf-8"))
            except Exception:
                pass

    def handle_sync_request(self):
        if sync_status["is_syncing"]:
            self.send_response(429)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": "동기화 작업이 이미 진행 중입니다."}, ensure_ascii=False).encode("utf-8"))
            return

        with sync_lock:
            sync_status["is_syncing"] = True
            try:
                sys.path.append(str(Path(__file__).resolve().parent))
                import fast_unified_sync
                result = fast_unified_sync.run_fast_patch(sync_api=True, api_days=7)
                sync_status["last_synced"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sync_status["last_result"] = result
            except Exception as e:
                result = {"success": False, "error": str(e)}
                sync_status["last_result"] = result
            finally:
                sync_status["is_syncing"] = False

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

    def handle_get_compensation_overrides(self):
        ov_file = Path(DIRECTORY) / "compensation_overrides.json"
        data = {"excluded_ids": [], "manual_additions": []}
        if ov_file.exists():
            try:
                with open(ov_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def handle_save_compensation_overrides(self, payload):
        ov_file = Path(DIRECTORY) / "compensation_overrides.json"
        try:
            with open(ov_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False).encode("utf-8"))

    def handle_login(self, body_data):
        username = (body_data.get("username") or "").strip()
        password = (body_data.get("password") or "").strip()

        auth_file = PROJECT_ROOT / "config" / "auth_config.json"
        accounts = []
        if auth_file.exists():
            try:
                with open(auth_file, "r", encoding="utf-8") as f:
                    auth_cfg = json.load(f)
                    accounts = auth_cfg.get("accounts", [])
            except Exception:
                pass

        if not accounts:
            accounts = [
                {"username": "cx", "password": "bebesup1!", "role": "admin", "name": "CX팀 관리자"},
                {"username": "bebesup", "password": "bebesup1!", "role": "user", "name": "CX팀 사원"}
            ]

        matched = None
        for acc in accounts:
            if acc.get("username") == username and acc.get("password") == password:
                matched = acc
                break

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()

        if matched:
            resp = {
                "success": True,
                "role": matched.get("role", "user"),
                "username": matched.get("username"),
                "name": matched.get("name", "CX팀")
            }
        else:
            resp = {
                "success": False,
                "error": "아이디 또는 비밀번호가 올바르지 않습니다."
            }
        self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        # 표준 로깅
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

def start_cloudflare_tunnel():
    if not CLOUDFLARED_BIN.exists():
        return
    import subprocess
    import re

    def _worker():
        cmd = [str(CLOUDFLARED_BIN), "tunnel", "--url", f"http://localhost:{PORT}"]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            tunnel_info["proc"] = proc
            url_file = Path(DIRECTORY) / "public_url.txt"

            for line in proc.stdout:
                m = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                if m:
                    tunnel_url = m.group(0)
                    tunnel_info["url"] = tunnel_url
                    print("--------------------------------------------------")
                    print(f" ★ [외부/모바일 공유 주소 발급 완료] -> {tunnel_url}")
                    print("--------------------------------------------------")
                    try:
                        with open(url_file, "w", encoding="utf-8") as f:
                            f.write(tunnel_url + "\n")
                    except Exception:
                        pass
        except Exception as e:
            print(f"[경고] Cloudflare 터널 실행 실패: {e}")

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

if __name__ == "__main__":
    os.chdir(DIRECTORY)
    start_cloudflare_tunnel()
    # 0.0.0.0 바인딩으로 로컬 및 사내 IP 접속 모두 허용 (멀티스레드 지원)
    with ThreadedTCPServer(("0.0.0.0", PORT), CustomHandler) as httpd:
        print("==================================================")
        print("[START] 베베숲 VOC 대시보드 항시 가동 서버 시작!")
        print(f" - 로컬 PC 접속:     http://localhost:{PORT}")
        print(f" - 사내 와이파이:    http://192.168.0.24:{PORT}")
        print(f" - 외부/재택/모바일:  Cloudflare 보안 터널 주소 연결 중...")
        print("==================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
            if tunnel_info.get("proc"):
                tunnel_info["proc"].terminate()
