@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PID_FILE=%~dp0.sanctum-suite.pid"

if exist "%PID_FILE%" (
    for /f %%P in (%PID_FILE%) do (
        if not "%%P"=="" (
            taskkill /PID %%P /T /F >nul 2>&1
            echo [Sanctum Suite] Zatrzymano proces PID %%P.
        )
    )
    del /f /q "%PID_FILE%" >nul 2>&1
) else (
    echo [Sanctum Suite] Brak aktywnego procesu Sanctum Suite.
)

echo [Sanctum Suite] Stan procesu zakonczony.
exit /b 0
