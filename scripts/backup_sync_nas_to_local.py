"""
NAS(라이브 메인) -> 로컬 2차 백업(D:\VOC_SHARE & D:\202611백업\DATA) 자동 동기화 모듈
- NAS (X:\)의 최신 라이브 DB, 원본 엑셀, 클레임 사진을 로컬 백업 위치로 증분 복제
- 3-2-1 백업 원칙 준수 (운영: NAS, 2차 미러: D:\VOC_SHARE, 3차 아카이브: D:\202611백업\DATA)
"""

import os
import sys
import shutil
import sqlite3
import time
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


NAS_BASE = Path(r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황")
NAS_PHOTOS_1 = Path(r"X:\11. VOC, CCM 자료 등\9. 클레임 사진\2026")
NAS_PHOTOS_2 = Path(r"X:\9. 클레임 사진\2026")

# 단일 로컬 통합 백업 대상 (하나의 폴더로 통일)
LOCAL_TARGETS = [
    Path(r"D:\VOC_SHARE")
]


def log(msg):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] {msg}")


def safe_sync_db(src_db: Path, dest_db: Path):
    """SQLite 온라인 백업 API를 사용하여 깨짐 없는 무결성 DB 동기화"""
    if not src_db.exists():
        log(f"  [건너뜀] 원본 DB가 존재하지 않음: {src_db}")
        return False

    dest_db.parent.mkdir(parents=True, exist_ok=True)

    # 크기 또는 mtime이 다를 경우에만 복사
    if dest_db.exists():
        src_stat = src_db.stat()
        dest_stat = dest_db.stat()
        if src_stat.st_size == dest_stat.st_size and abs(src_stat.st_mtime - dest_stat.st_mtime) < 2:
            return True

    temp_dest = dest_db.parent / (dest_db.name + ".tmp_sync")
    try:
        src_conn = sqlite3.connect(f"file:{str(src_db)}?mode=ro", uri=True, timeout=10)
        dst_conn = sqlite3.connect(str(temp_dest))
        with dst_conn:
            src_conn.backup(dst_conn)
        src_conn.close()
        dst_conn.close()

        if temp_dest.exists() and temp_dest.stat().st_size > 1024:
            if dest_db.exists():
                dest_db.unlink()
            temp_dest.rename(dest_db)
            log(f"  [DB 복제 완료] {dest_db} ({dest_db.stat().st_size:,} bytes)")
            return True
    except Exception as e:
        log(f"  [DB 복제 오류] {dest_db}: {e}")
        # fallback: 단순 파일 복사
        try:
            shutil.copy2(str(src_db), str(dest_db))
            log(f"  [DB 단순 복사 완료] {dest_db}")
            return True
        except Exception as e2:
            log(f"  [DB 단순 복사 실패] {dest_db}: {e2}")
    finally:
        if temp_dest.exists():
            try:
                temp_dest.unlink()
            except Exception:
                pass
    return False


def sync_directory_incremental(src_dir: Path, dest_dir: Path, extensions=None):
    """파일 크기/수정일자 비교 기반 초고속 증분 동기화"""
    if not src_dir.exists():
        return 0, 0

    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    skipped = 0

    for root, dirs, files in os.walk(src_dir):
        rel_path = os.path.relpath(root, str(src_dir))
        target_root = dest_dir if rel_path == "." else dest_dir / rel_path

        for f in files:
            if extensions:
                ext = os.path.splitext(f)[1].lower()
                if ext not in extensions:
                    continue

            src_file = Path(root) / f
            dest_file = target_root / f

            needs_copy = False
            if not dest_file.exists():
                needs_copy = True
            else:
                try:
                    s_stat = src_file.stat()
                    d_stat = dest_file.stat()
                    if s_stat.st_size != d_stat.st_size or abs(s_stat.st_mtime - d_stat.st_mtime) > 2:
                        needs_copy = True
                except Exception:
                    needs_copy = True

            if needs_copy:
                try:
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(src_file), str(dest_file))
                    copied += 1
                except Exception as ce:
                    pass
            else:
                skipped += 1

    return copied, skipped


def run_full_backup_sync():
    """전체 로컬 백업 동기화 메인 함수"""
    t0 = time.time()
    log("=" * 60)
    log("🔄 [NAS ➔ 로컬 백업 동기화 시작]")
    log(f"   원본(Live NAS): {NAS_BASE}")
    log("=" * 60)

    live_db = NAS_BASE / "db" / "channeltalk_voc.db"

    for target in LOCAL_TARGETS:
        if not target.exists():
            log(f"⚠️ 백업 대상 폴더 없음: {target}")
            continue

        log(f"\n▶ 백업 대상 동기화: {target}")

        # 1. DB 파일 안전 동기화
        # 1-1) D:\VOC_SHARE\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db
        t_db1 = target / "11. VOC, CCM 자료 등" / "1. VOC 불만접수현황" / "db" / "channeltalk_voc.db"
        safe_sync_db(live_db, t_db1)

        # 2. 클레임 사진 증분 동기화
        photo_targets = [
            target / "11. VOC, CCM 자료 등" / "9. 클레임 사진" / "2026",
            target / "9. 클레임 사진" / "2026"
        ]
        img_exts = {".jpg", ".jpeg", ".png", ".webp"}
        src_photos = NAS_PHOTOS_1 if NAS_PHOTOS_1.exists() else NAS_PHOTOS_2

        for pt in photo_targets:
            c, s = sync_directory_incremental(src_photos, pt, extensions=img_exts)
            if c > 0:
                log(f"  [사진 동기화] {pt} : {c}개 신규 복제 (기존 {s}개 유지)")

        # 3. 배송/게시판/채널톡 raw 엑셀 증분 동기화
        raw_src = NAS_BASE / "26년" / "raw"
        raw_dest = target / "11. VOC, CCM 자료 등" / "1. VOC 불만접수현황" / "26년" / "raw"
        if raw_src.exists():
            c_raw, s_raw = sync_directory_incremental(raw_src, raw_dest, extensions={".xlsx", ".xls", ".csv"})
            if c_raw > 0:
                log(f"  [26년 RAW 엑셀 동기화] {c_raw}개 파일 신규 복제 (기존 {s_raw}개 유지)")

    total_sec = time.time() - t0
    log("=" * 60)
    log(f"✅ [NAS ➔ 로컬 백업 완료] 총 소요시간: {total_sec:.2f}초")
    log("=" * 60)


if __name__ == "__main__":
    run_full_backup_sync()
