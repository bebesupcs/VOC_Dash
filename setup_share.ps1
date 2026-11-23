net share VOC_SHARE="D:\VOC_SHARE" /grant:Everyone,FULL
icacls "D:\VOC_SHARE" /grant "Everyone:(OI)(CI)F" /T
Set-NetConnectionProfile -InterfaceAlias "Wi-Fi" -NetworkCategory Private -ErrorAction SilentlyContinue
netsh advfirewall firewall set rule group="File and Printer Sharing" new enable=Yes
netsh advfirewall firewall set rule group="파일 및 프린터 공유" new enable=Yes
Write-Host "==========================================" -ForegroundColor Green
Write-Host "[SUCCESS] VOC_SHARE Network Share Created!" -ForegroundColor Green
Write-Host "Path: \\192.168.0.22\VOC_SHARE" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Green
Start-Sleep -Seconds 3