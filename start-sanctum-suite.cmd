@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_DIR=%~dp0sanctum-dashboard"
set "LOG_FILE=%~dp0sanctum-suite-dev.log"
set "PID_FILE=%~dp0.sanctum-suite.pid"
set "STDOUT_LOG=%~dp0sanctum-suite-stdout.log"
set "STDERR_LOG=%~dp0sanctum-suite-stderr.log"

if not exist "%APP_DIR%\package.json" (
    echo [Sanctum Suite] Blad: brak folderu sanctum-dashboard.
    echo [Sanctum Suite] Uruchom skrypt z glownego katalogu repozytorium.
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo [Sanctum Suite] Blad: Node.js nie jest zainstalowany lub nie jest dodany do PATH.
    echo [Sanctum Suite] Zainstaluj Node.js 18+ i uruchom skrypt ponownie.
    exit /b 1
)

if not exist "%APP_DIR%\node_modules" (
    echo [Sanctum Suite] Brak zaleznosci. Instalacja startuje...
    pushd "%APP_DIR%"
    call npm install --no-fund --no-audit
    if errorlevel 1 (
        echo [Sanctum Suite] Instalacja zakonczona bledem.
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

del /f /q "%STDOUT_LOG%" "%STDERR_LOG%" >nul 2>&1

powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$process = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','dev','--','--hostname','0.0.0.0' -WorkingDirectory '%APP_DIR%' -PassThru -WindowStyle Hidden -RedirectStandardOutput '%STDOUT_LOG%' -RedirectStandardError '%STDERR_LOG%'; $process.Id | Set-Content -Path '%PID_FILE%'"

powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$success = $false; for ($i = 0; $i -lt 120; $i++) { try { Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:3000' -TimeoutSec 2 | Out-Null; $success = $true; break } catch { Start-Sleep -Seconds 1 } }; if ($success) { try { Start-Process 'http://localhost:3000' } catch {} } else { Write-Host '[Sanctum Suite] Nie udalo sie potwierdzic uruchomienia strony. Sprawdz log: %LOG_FILE%' -ForegroundColor Yellow }"

echo [Sanctum Suite] Uruchomiono. Aplikacja jest dostepna pod http://localhost:3000
echo [Sanctum Suite] Do zatrzymania uzyj stop-sanctum-suite.cmd
exit /b 0
