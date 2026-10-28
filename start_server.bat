@echo off
chcp 65001 > nul
title 베베숲 VOC 대시보드 서버 실행기

echo ========================================================
echo         베베숲 VOC 대시보드 상시 서버 구동기
echo ========================================================
echo.
echo [1] 서버 및 보안 터널을 시작합니다...
echo.

cd /d "%~dp0"
python scripts\run_dashboard_server.py

pause
