@echo off
cd /d "%~dp0"

REM 1. Wait 3 seconds
ping 127.0.0.1 -n 4 >nul

REM 2. Map X: drive to NAS if not present
if not exist "X:\" (
    net use X: \\192.168.0.12\data /persistent:yes >nul 2>&1
)

REM 3. Check if server port 8080 is already listening
netstat -ano | findstr ":8080" | findstr "LISTENING" >nul 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] Starting VOC Dashboard Server... >> autostart.log
    start "" /b "C:\Users\hshwa\AppData\Local\Programs\Python\Python314\python.exe" scripts\run_dashboard_server.py >> autostart.log 2>&1
) else (
    echo [%date% %time%] Port 8080 already running. >> autostart.log
)

REM 4. Check if ngrok is already running
tasklist /fi "imagename eq ngrok.exe" | findstr /i "ngrok.exe" >nul 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] Starting ngrok tunnel... >> autostart.log
    start "" /b "C:\Users\hshwa\AppData\Local\Microsoft\WindowsApps\ngrok.exe" http 8080 --url https://twirl-essence-slapstick.ngrok-free.dev >> ngrok.log 2>&1
) else (
    echo [%date% %time%] ngrok tunnel is already running. >> autostart.log
)