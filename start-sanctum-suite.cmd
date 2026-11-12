@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_DIR=%~dp0sanctum-dashboard"
set "LOG_FILE=%~dp0sanctum-suite-dev.log"
set "PID_FILE=%~dp0.sanctum-suite.pid"

if not exist "%APP_DIR%\package.json" (
    echo [Sanctum Suite] Blad: brak folderu sanctum-dashboard.
    echo [Sanctum Suite] Uruchom skrypt z glownego katalogu repozytorium.
    pause
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo [Sanctum Suite] Blad: Node.js nie jest zainstalowany lub nie jest dodany do PATH.
    echo [Sanctum Suite] Zainstaluj Node.js 18+ i uruchom skrypt ponownie.
    pause
    exit /b 1
)

if not exist "%APP_DIR%\node_modules" (
    echo [Sanctum Suite] Brak zaleznosci. Instalacja startuje...
    pushd "%APP_DIR%"
    call npm install --no-fund --no-audit
    if errorlevel 1 (
        echo [Sanctum Suite] Instalacja zakonczona bledem.
        popd
        pause
        exit /b 1
    )
    popd
)

if exist "%PID_FILE%" (
    for /f %%P in (%PID_FILE%) do (
        if not "%%P"=="" (
            taskkill /PID %%P /T /F >nul 2>&1
        )
    )
    del /f /q "%PID_FILE%" >nul 2>&1
)

pushd "%APP_DIR%"
start "Sanctum Suite" cmd /c "npm run dev -- --hostname 0.0.0.0 > \"%LOG_FILE%\" 2>&1"
popd

for /f %%P in ('powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "(Get-CimInstance Win32_Process -Filter \"Name='cmd.exe'\" | Where-Object { $_.CommandLine -match 'npm run dev -- --hostname 0.0.0.0' } | Sort-Object ProcessId | Select-Object -First 1 -ExpandProperty ProcessId)" 2^>nul') do (
    set "PID=%%P"
)

if not "%PID%"=="" (
    echo %PID%>"%PID_FILE%"
)

powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$success = $false; for ($i = 0; $i -lt 90; $i++) { try { Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:3000' -TimeoutSec 2 | Out-Null; $success = $true; break } catch { Start-Sleep -Seconds 1 } }; if ($success) { Start-Process 'http://localhost:3000' } else { Write-Host '[Sanctum Suite] Nie udalo sie potwierdzic uruchomienia strony. Sprawdz log: %LOG_FILE%' -ForegroundColor Yellow }"

echo.
echo [Sanctum Suite] Aplikacja wystartowala. Lokalizacja: http://localhost:3000
echo [Sanctum Suite] Uzyj stop-sanctum-suite.cmd, aby zatrzymac proces.
echo [Sanctum Suite] Wcisnij Ctrl+C w tym oknie, aby zamknac launcher.
echo.
exit /b 0
