# -*- coding: utf-8 -*-
r"""
backup_source_code.py
D:\dev\VOC리포트 개발 소스 코드를 NAS(X:\_개발소스_백업) 및 Git으로 자동 백업하는 모듈
"""

import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

LOCAL_SRC = Path("D:/dev/VOC리포트")
NAS_BACKUP_DIR = Path("X:/_개발소스_백업")
NAS_GIT_DIR = NAS_BACKUP_DIR / "VOC리포트.git"
NAS_CODE_MIRROR = NAS_BACKUP_DIR / "최신소스"


def backup_source_to_nas(log_func=print):
    log_func("============================================================")
    log_func("[개발 소스 코드 NAS 및 Git 백업 시작]")
    log_func(f"   원본: {LOCAL_SRC}")
    log_func(f"   대상: {NAS_BACKUP_DIR}")
    log_func("============================================================")

    if not Path("X:/").exists():
        log_func("❌ X: 드라이브(NAS)가 연결되어 있지 않아 백업을 중단합니다.")
        return False, "NAS 드라이브 연결 없음"

    NAS_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # 1. NAS에 Git Bare 저장소 초기화 및 Git Push (커밋 히스토리 보존 백업)
    try:
        if not NAS_GIT_DIR.exists():
            log_func("▶ [1/3] NAS Git Bare 저장소 초기화 중...")
            subprocess.run(["git", "init", "--bare", str(NAS_GIT_DIR)], check=True, cwd=str(LOCAL_SRC), encoding="utf-8", errors="replace")

        # remote 등록 여부 확인
        remotes_out = subprocess.run(["git", "remote"], capture_output=True, encoding="utf-8", errors="replace", cwd=str(LOCAL_SRC)).stdout.split()
        if "nas" not in remotes_out:
            subprocess.run(["git", "remote", "add", "nas", str(NAS_GIT_DIR)], check=True, cwd=str(LOCAL_SRC), encoding="utf-8", errors="replace")
        else:
            subprocess.run(["git", "remote", "set-url", "nas", str(NAS_GIT_DIR)], check=True, cwd=str(LOCAL_SRC), encoding="utf-8", errors="replace")

        log_func("▶ [2/3] NAS Git 저장소로 커밋 동기화(git push)...")
        push_res = subprocess.run(["git", "push", "nas", "master", "-f"], capture_output=True, encoding="utf-8", errors="replace", cwd=str(LOCAL_SRC))
        if push_res.returncode == 0:
            log_func(f"  ✨ Git 히스토리 전체 동기화 성공: {NAS_GIT_DIR}")
        else:
            err_msg = (push_res.stderr or push_res.stdout or "").strip()
            log_func(f"  ⚠️ Git push 알림: {err_msg}")
    except Exception as ge:
        log_func(f"  ❌ Git 백업 오류: {ge}")

    # 2. 일반 파일 형태로도 최신 코드 미러링 (누구나 바로 열어볼 수 있도록)
    try:
        log_func("▶ [3/3] NAS 최신 소스 파일 복제(미러링)...")
        NAS_CODE_MIRROR.mkdir(parents=True, exist_ok=True)

        include_folders = ["dashboard", "scripts", "templates", "config", "tools", "docs"]
        include_files = ["Dockerfile", "docker-compose.yml", "requirements.txt", ".gitignore", "start_dashboard.bat", "start_dashboard_hidden.vbs"]

        for item_name in include_folders:
            src_f = LOCAL_SRC / item_name
            dst_f = NAS_CODE_MIRROR / item_name
            if src_f.exists():
                shutil.copytree(src_f, dst_f, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "data.js*", "data.json*"))

        for f_name in include_files:
            src_file = LOCAL_SRC / f_name
            dst_file = NAS_CODE_MIRROR / f_name
            if src_file.exists():
                shutil.copy2(src_file, dst_file)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        (NAS_CODE_MIRROR / "BACKUP_INFO.txt").write_text(f"최종 소스 백업 시각: {now_str}\n백업 출처: {LOCAL_SRC}\n", encoding="utf-8")
        log_func(f"  ✨ 최신 소스 파일 미러링 완료: {NAS_CODE_MIRROR}")
    except Exception as fe:
        log_func(f"  ❌ 파일 복제 오류: {fe}")

    # 3. 사내 GitHub / Git 원격 저장소가 등록되어 있다면 함께 푸시
    try:
        remotes_out = subprocess.run(["git", "remote"], capture_output=True, encoding="utf-8", errors="replace", cwd=str(LOCAL_SRC)).stdout.split()
        for r in ["origin", "github"]:
            if r in remotes_out:
                log_func(f"▶ 원격 Git({r})으로 푸시 중...")
                r_res = subprocess.run(["git", "push", r, "master"], capture_output=True, encoding="utf-8", errors="replace", cwd=str(LOCAL_SRC))
                if r_res.returncode == 0:
                    log_func(f"  ✨ 원격 Git({r}) 동기화 완료!")
                else:
                    err_remote = (r_res.stderr or r_res.stdout or "").strip()[:150]
                    log_func(f"  ⚠️ 원격 Git({r}) 응답: {err_remote}")
    except Exception as re:
        log_func(f"  ⚠️ 원격 Git 푸시 건너뜀: {re}")

    log_func("============================================================")
    log_func("✅ [개발 소스 코드 NAS 백업 완료]")
    log_func("============================================================")
    return True, "백업 성공"


if __name__ == "__main__":
    backup_source_to_nas(print)
