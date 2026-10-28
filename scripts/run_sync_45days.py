# -*- coding: utf-8 -*-
import sys
import os
from pathlib import Path

# 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.append(r"D:\dev\VOC리포트\scripts")
from sync_channeltalk_api import run_sync

print("🚀 채널톡 API 45일치 전체 수집(Closed + Opened) 가동...")
run_sync(days=45)
print("✨ 수집 및 대시보드 갱신 완료!")
