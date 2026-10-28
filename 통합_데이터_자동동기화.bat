@echo off
setlocal
pushd "%~dp0"
python "%~dp0scripts\run_unified_sync.py" %*
popd
if "%~1"=="" timeout /t 15
endlocal
