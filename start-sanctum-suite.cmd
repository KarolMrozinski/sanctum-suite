@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_URL=%SANCTUM_APP_URL%"
if not defined APP_URL set "APP_URL=http://localhost:3000"

set "EXE_PATH=%~dp0SanctumSuiteLauncher.exe"
set "APP_DIR=%~dp0sanctum-dashboard"
set "LOCAL_TARGET=0"

call :normalize_app_url

echo "%APP_URL%" | findstr /I /C:"localhost" /C:"127.0.0.1" /C:"0.0.0.0" >nul
if not errorlevel 1 set "LOCAL_TARGET=1"

if exist "%EXE_PATH%" (
    echo [Sanctum Suite] Uruchamianie aplikacji desktopowej...
    echo [Sanctum Suite] Target URL: %APP_URL%
    start "" "%EXE_PATH%"
    exit /b 0
)

if not exist "%APP_DIR%\package.json" (
    echo [Sanctum Suite] Blad: brak folderu sanctum-dashboard.
    exit /b 1
)

if "%LOCAL_TARGET%"=="0" (
    echo [Sanctum Suite] Konfigurowany jest zewnętrzny adres aplikacji: %APP_URL%
    echo [Sanctum Suite] Pomijam lokalny start Node.js i sprawdzam tylko zdalny endpoint.
    for /l %%I in (1,1,60) do (
        powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri '%APP_URL%' -TimeoutSec 3; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } } catch { exit 1 }" >nul 2>&1
        if not errorlevel 1 goto app_ready
        ping -n 2 127.0.0.1 >nul
    )
    echo [Sanctum Suite] Nie udalo sie potwierdzic dostepnosci zdalnego adresu %APP_URL%.
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo [Sanctum Suite] Blad: Node.js nie jest zainstalowany lub nie jest dodany do PATH.
    exit /b 1
)

for /f "tokens=*" %%P in ('powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'next dev' -or $_.CommandLine -match 'npm run dev' } | Where-Object { $_.CommandLine -match 'sanctum-dashboard' -or $_.CommandLine -match '--hostname' -or $_.CommandLine -match '--port' } | Select-Object -First 1 -ExpandProperty ProcessId; if ($p) { $p }" 2^>nul') do (
    set "RUNNING_PID=%%P"
)
if defined RUNNING_PID (
    echo [Sanctum Suite] Aplikacja jest juz uruchomiona (PID %RUNNING_PID%).
    exit /b 0
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

echo [Sanctum Suite] Startowanie aplikacji pod %APP_URL%...
start "" /B powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Set-Location '%APP_DIR%'; npm run dev -- --hostname 0.0.0.0 --port 3000"

for /l %%I in (1,1,120) do (
    powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri '%APP_URL%' -TimeoutSec 2; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 goto app_ready
    ping -n 2 127.0.0.1 >nul
)

echo [Sanctum Suite] Nie udalo sie uruchomic aplikacji w czasie oczekiwania.
exit /b 1

:normalize_app_url
set "APP_URL=%APP_URL:0.0.0.0=localhost%"
exit /b 0

:app_ready
echo [Sanctum Suite] Aplikacja jest dostepna pod %APP_URL%
exit /b 0
