@echo off
setlocal EnableExtensions
cd /d "%~dp0"
wscript.exe "%~dp0sanctum-suite-gui-launcher.vbs"
exit /b 0
