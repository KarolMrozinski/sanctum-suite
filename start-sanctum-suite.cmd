@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_DIR=%~dp0sanctum-dashboard"
set "PID_FILE=%~dp0.sanctum-suite.pid"
set "BROWSER_FLAG=%~dp0.sanctum-suite.browser-opened"
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

powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'next dev --hostname 0.0.0.0' -or $_.CommandLine -match 'npm run dev -- --hostname 0.0.0.0 --port 3000' -or $_.CommandLine -match 'sanctum-dashboard' }; foreach ($p in $procs) { try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop } catch {} }"
if exist "%PID_FILE%" del /f /q "%PID_FILE%" >nul 2>&1
if exist "%BROWSER_FLAG%" del /f /q "%BROWSER_FLAG%" >nul 2>&1

echo [Sanctum Suite] Startowanie aplikacji...

start "" /B powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Set-Location '%APP_DIR%'; npm run dev -- --hostname 0.0.0.0 --port 3000"

for /l %%I in (1,1,120) do (
    powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing -Uri '%APP_URL%' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 goto app_ready
    ping -n 2 127.0.0.1 >nul
)

echo [Sanctum Suite] Nie udalo sie uruchomic aplikacji w czasie oczekiwania.
exit /b 1

:app_ready
echo [Sanctum Suite] Aplikacja jest dostepna pod %APP_URL%

powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'npm run dev -- --hostname 0.0.0.0 --port 3000' -or $_.CommandLine -match 'next dev --hostname 0.0.0.0 --port 3000' } | Select-Object -First 1 -ExpandProperty ProcessId; if ($p) { $p | Set-Content -Path '%PID_FILE%' }"
if not exist "%BROWSER_FLAG%" (
    call :open_browser
    echo opened > "%BROWSER_FLAG%"
)

exit /b 0

:open_browser
start "" "%APP_URL%"
if errorlevel 1 (
    powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "Start-Process 'http://localhost:3000'"
)
exit /b 0
