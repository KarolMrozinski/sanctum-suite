[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$Preview
)

$matches = @(
    "sanctum-dashboard",
    "next dev",
    "npm run dev",
    "--hostname",
    "--port 3000",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "localhost:3000"
)

Write-Host "Szukam starych procesow Sanctum Suite..." -ForegroundColor Cyan

$processes = Get-CimInstance Win32_Process |
    Where-Object {
        $cmd = $_.CommandLine
        if ([string]::IsNullOrWhiteSpace($cmd)) { return $false }

        $normalized = $cmd.ToLowerInvariant()
        return ($normalized -like '*sanctum-dashboard*') -or
               ($normalized -like '*next dev*') -or
               ($normalized -like '*npm run dev*') -or
               ($normalized -like '*--hostname*') -or
               ($normalized -like '*--port 3000*') -or
               ($normalized -like '*127.0.0.1:3000*') -or
               ($normalized -like '*localhost:3000*')
    } |
    Sort-Object ProcessId

if (-not $processes) {
    Write-Host "Nie znaleziono starych procesow Sanctum." -ForegroundColor Green
    exit 0
}

foreach ($proc in $processes) {
    $cmd = if ($null -ne $proc.CommandLine) { $proc.CommandLine.Trim() } else { '' }
    $label = "PID $($proc.ProcessId) | $($proc.Name) | $cmd"

    if ($Preview) {
        Write-Host "[PREVIEW] zabiłbym: $label" -ForegroundColor Yellow
        continue
    }

    if ($PSCmdlet.ShouldProcess($label, "Zamknij proces")) {
        try {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
            Write-Host "Zamknieto: $label" -ForegroundColor Green
        }
        catch {
            Write-Host "Nie udalo sie zamknac PID $($proc.ProcessId): $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

if (-not $Preview) {
    Write-Host "Koniec czyszczenia starych wersji Sanctum." -ForegroundColor Green
}
