@echo off
chcp 65001 > nul
setlocal
pushd "%~dp0"

echo ====================================================
echo 베베숲 VOC 대시보드 실데이터 추출기
echo ====================================================
echo.

python "%~dp0scripts\export_dashboard_data.py"

echo.
echo ====================================================
echo [완료] 대시보드 데이터(data.js) 갱신이 완료되었습니다.
echo 브라우저에서 index.html을 새로고침(F5) 해주세요.
echo ====================================================
popd
pause
endlocal
