@echo off
setlocal EnableExtensions
cd /d "%~dp0"
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0sanctum-suite-gui-launcher.ps1"
exit /b %ERRORLEVEL%
