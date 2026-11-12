@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if exist "%~dp0SanctumSuiteLauncher.exe" (
    start "" "%~dp0SanctumSuiteLauncher.exe"
    exit /b 0
)
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', '""%~dp0start-sanctum-suite.cmd""' -WindowStyle Hidden -WorkingDirectory '%~dp0'" 
exit /b 0
