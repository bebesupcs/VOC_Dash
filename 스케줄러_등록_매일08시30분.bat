@echo off
chcp 65001 > nul
setlocal

echo ================================================================
echo    [작업 스케줄러 등록] 베베숲 VOC 매일 아침 08:30 자동 동기화
echo ================================================================
echo.

schtasks /create /tn "Bebesup_VOC_Daily_Sync" /tr "%~dp0통합_데이터_자동동기화.bat" /sc daily /st 08:30 /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [성공] 윈도우 작업 스케줄러에 'Bebesup_VOC_Daily_Sync' 작업이 등록되었습니다!
    echo 매일 아침 08:30에 자동으로 채널톡 API, 배송, 게시판 데이터가 동기화됩니다.
) else (
    echo.
    echo [오류] 작업 등록에 실패했습니다. 관리자 권한으로 다시 실행해 주세요.
)

echo.
echo ================================================================
pause
endlocal
