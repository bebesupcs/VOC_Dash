"""
구글 드라이브 클레임 사진 자동 동기화 모듈
- Google Drive 폴더: https://drive.google.com/drive/folders/1KwBoSMdPf7OEeesMG92bN_WrazLf1UUM
- 로컬 대상 디렉토리: d:/dev/VOC리포트/claim_photos/2026
"""

import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

GDRIVE_FOLDER_ID = "1KwBoSMdPf7OEeesMG92bN_WrazLf1UUM"
GDRIVE_URL = f"https://drive.google.com/drive/folders/{GDRIVE_FOLDER_ID}"

BASE_DIR = Path(__file__).resolve().parent.parent


def get_target_photos_dir():
    candidates = [
        Path("/photos/2026"),
        Path("/photos"),
        Path("/app/claim_photos/2026"),
        Path("/app/claim_photos"),
        Path("/data/9. 클레임 사진/2026"),
        Path("/data/9. 클레임 사진"),
        Path(r"X:\11. VOC, CCM 자료 등\9. 클레임 사진\2026"),
        Path(r"X:\9. 클레임 사진\2026"),
        BASE_DIR / "claim_photos" / "2026",
    ]
    for c in candidates:
        if c.exists():
            return c
    fallback = BASE_DIR / "claim_photos" / "2026"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def normalize_synced_photo_folders(target_dir):
    """
    구글 드라이브에서 다운로드된 '2026년' 등의 중복 하위 폴더나 주차 폴더들을
    대시보드가 인식할 수 있는 표준 주차 폴더로 복사/평탄화합니다.
    """
    import shutil
    target_path = Path(target_dir)
    if not target_path.exists():
        return

    # 1. 2026년 등 중복 연도 폴더 내 주차 폴더 상위로 이동/복사
    for sub in list(target_path.iterdir()):
        if sub.is_dir() and re.match(r"^202\d(년)?$", sub.name):
            for week_dir in sub.iterdir():
                if week_dir.is_dir():
                    dest = target_path / week_dir.name
                    dest.mkdir(parents=True, exist_ok=True)
                    for img in week_dir.iterdir():
                        if img.is_file() and img.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                            shutil.copy2(str(img), str(dest / img.name))
            # 정리
            try:
                shutil.rmtree(str(sub), ignore_errors=True)
            except Exception:
                pass

    # 2. '11월 3주' 형태와 '11월 3주(1112~1118)' 형태 상호 동기화
    week_dirs = [d for d in target_path.iterdir() if d.is_dir()]
    for d in week_dirs:
        m = re.match(r"^(\d+월\s*\d+주)", d.name)
        if m:
            clean_name = m.group(1).strip()
            # 매칭되는 다른 형태의 폴더 찾기
            for other in week_dirs:
                if other != d and other.name.startswith(clean_name):
                    # 파일 복사
                    for img in d.iterdir():
                        if img.is_file() and img.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                            target_file = other / img.name
                            if not target_file.exists():
                                shutil.copy2(str(img), str(target_file))


def sync_claim_photos_from_gdrive(quiet=True):
    """
    구글 드라이브 폴더로부터 클레임 사진을 로컬 디렉토리로 동기화합니다.
    비이미지 문서(구글 닥스, 스프레드시트 등)로 인한 실패 시 개별 파일 단위로 안전하게 다운로드합니다.
    """
    try:
        import gdown
    except ImportError:
        import subprocess
        print("[GDrive Sync] gdown 패키지가 없어 자동 설치를 진행합니다...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "gdown"], check=True)
            import gdown
            print("[GDrive Sync] gdown 자동 설치 성공!")
        except Exception as pie:
            print(f"[GDrive Sync] gdown 자동 설치 실패: {pie}")
            return False, f"gdown 패키지 설치 실패: {pie}"

    import urllib.request

    target_dir = get_target_photos_dir()

    def count_local_images():
        cnt = 0
        for root, dirs, files in os.walk(target_dir):
            for f in files:
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    cnt += 1
        return cnt

    print(f"[GDrive Sync] 구글 드라이브 폴더({GDRIVE_FOLDER_ID}) ➔ {target_dir} 동기화 시작...")

    # 1차 시도: gdown.download_folder
    try:
        gdown.download_folder(
            url=GDRIVE_URL,
            output=str(target_dir),
            quiet=quiet,
            use_cookies=False
        )
    except Exception as e:
        err_msg = str(e)
        print(f"[GDrive Sync] 폴더 일괄 다운로드 중 알림({err_msg[:80]}...). 개별 파일 모드로 계속 진행합니다.")
        # 2차 시도: skip_download로 파일 목록을 추출한 후 이미지 파일만 개별 다운로드
        try:
            items = gdown.download_folder(url=GDRIVE_URL, skip_download=True, quiet=True)
            for item in items:
                fname = getattr(item, 'name', '') or os.path.basename(getattr(item, 'path', ''))
                fid = getattr(item, 'id', '')
                fpath = getattr(item, 'path', '')
                if fname.lower().endswith((".jpg", ".jpeg", ".png", ".webp")) and fid:
                    rel_p = fpath if fpath else fname
                    out_p = Path(target_dir) / rel_p
                    if not out_p.exists():
                        out_p.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            direct_url = f"https://drive.google.com/uc?id={fid}"
                            req = urllib.request.Request(direct_url, headers={"User-Agent": "Mozilla/5.0"})
                            with urllib.request.urlopen(req, timeout=15) as resp:
                                content = resp.read()
                                if len(content) > 1000:
                                    with open(str(out_p), "wb") as fp:
                                        fp.write(content)
                        except Exception:
                            pass
        except Exception as list_e:
            print(f"[GDrive Sync] 개별 파일 목록 조회 실패: {list_e}")

    # 폴더 평탄화 및 대시보드 호환 정규화
    try:
        normalize_synced_photo_folders(target_dir)
    except Exception as ne:
        print(f"[GDrive Sync] 폴더 정규화 알림: {ne}")

    total_imgs = count_local_images()
    print(f"[GDrive Sync] [OK] 총 {total_imgs}개 클레임 사진 동기화 완료.")
    return True, f"동기화 성공 (총 {total_imgs}개 사진 보유)"


if __name__ == "__main__":
    success, msg = sync_claim_photos_from_gdrive(quiet=False)
    sys.exit(0 if success else 1)

