@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_DIR=%~dp0sanctum-dashboard"
set "PID_FILE=%~dp0.sanctum-suite.pid"
set "STDOUT_LOG=%~dp0sanctum-suite-stdout.log"
set "STDERR_LOG=%~dp0sanctum-suite-stderr.log"
set "APP_URL=http://localhost:3000"

if not exist "%APP_DIR%\package.json" (
    echo [Sanctum Suite] Blad: brak folderu sanctum-dashboard.
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo [Sanctum Suite] Blad: Node.js nie jest zainstalowany lub nie jest dodany do PATH.
    exit /b 1
)

if not exist "%APP_DIR%\node_modules" (
    echo [Sanctum Suite] Brak zaleznosci. Instalacja startuje...
    pushd "%APP_DIR%"
    call npm install --no-fund --no-audit
    if errorlevel 1 (
        echo [Sanctum Suite] Instalacja zakonczyla sie bledem.
        popd
        exit /b 1
    )
    popd
)

if exist "%PID_FILE%" (
    for /f "delims=" %%P in (%PID_FILE%) do (
        if not "%%P"=="" (
            taskkill /PID %%P /T /F >nul 2>&1
        )
    )
    del /f /q "%PID_FILE%" >nul 2>&1
)

for /f "skip=1" %%P in ('wmic process where "CommandLine like '%%next dev --hostname 0.0.0.0%%'" get ProcessId 2^>nul') do (
    taskkill /PID %%P /T /F >nul 2>&1
)

del /f /q "%STDOUT_LOG%" "%STDERR_LOG%" >nul 2>&1

echo [Sanctum Suite] Startowanie aplikacji...

pushd "%APP_DIR%"
start "Sanctum Suite" /D "%APP_DIR%" /B cmd /c "npm run dev -- --hostname 0.0.0.0 --port 3000 > "%STDOUT_LOG%" 2> "%STDERR_LOG%""
popd

for /l %%I in (1,1,120) do (
    powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing -Uri '%APP_URL%' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 goto app_ready
    ping -n 2 127.0.0.1 >nul
)

:app_ready
echo [Sanctum Suite] Aplikacja jest dostepna pod %APP_URL%
start "" %APP_URL%

powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$p = Get-CimInstance Win32_Process -Filter \"CommandLine LIKE '%next dev --hostname 0.0.0.0 --port 3000%'\" | Select-Object -First 1 -ExpandProperty ProcessId; if ($p) { $p | Set-Content -Path '%PID_FILE%' }"

exit /b 0
