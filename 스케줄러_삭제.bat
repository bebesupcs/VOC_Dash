@echo off
chcp 65001 > nul
setlocal

echo ================================================================
echo    [작업 스케줄러 삭제] 베베숲 VOC 매일 아침 08:30 자동 동기화 해제
echo ================================================================
echo.

schtasks /delete /tn "Bebesup_VOC_Daily_Sync" /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [성공] 'Bebesup_VOC_Daily_Sync' 스케줄러 작업이 정상적으로 삭제되었습니다.
) else (
    echo.
    echo [알림] 등록된 작업이 없거나 삭제에 실패했습니다.
)

echo.
echo ================================================================
pause
endlocal
