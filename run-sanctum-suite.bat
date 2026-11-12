@echo off
setlocal EnableExtensions
cd /d "%~dp0"
call "%~dp0start-sanctum-suite.cmd"
exit /b %errorlevel%
