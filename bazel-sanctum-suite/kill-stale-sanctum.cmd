@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0kill-stale-sanctum.ps1" %*
if errorlevel 1 (
    echo.
    echo Wystapil blad podczas zamykania starych procesow Sanctum.
    echo Nacisnij dowolny klawisz, aby zamknac okno...
    pause >nul
)
