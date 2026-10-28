@echo off
setlocal
pushd "%~dp0"
python "%~dp0scripts\run_dashboard_server.py"
popd
endlocal
