$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$appDir = Join-Path $root 'sanctum-dashboard'
$pidFile = Join-Path $root '.sanctum-suite.pid'
$stdoutLog = Join-Path $root 'sanctum-suite-stdout.log'
$stderrLog = Join-Path $root 'sanctum-suite-stderr.log'
$browserFlag = Join-Path $root '.sanctum-suite.browser-opened'
$iconPath = Join-Path $root 'sanctum-suite-icon.ico'

function Ensure-Dependencies {
    if (-not (Test-Path (Join-Path $appDir 'package.json'))) {
        throw 'Brak katalogu sanctum-dashboard.'
    }

    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        throw 'Node.js nie jest zainstalowany lub nie jest w PATH.'
    }

    if (-not (Test-Path (Join-Path $appDir 'node_modules'))) {
        Write-Host '[Sanctum Suite] Instalacja zaleznosci...'
        Push-Location $appDir
        npm install --no-fund --no-audit
        Pop-Location
    }
}

function Stop-ManagedProcess {
    if (Test-Path $pidFile) {
        $pid = (Get-Content $pidFile -Raw).Trim()
        if ($pid -and $pid -match '^\d+$') {
            try {
                Stop-Process -Id ([int]$pid) -Force -ErrorAction SilentlyContinue
            } catch {}
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
}

function Is-AppRunning {
    if (Test-Path $pidFile) {
        $pid = (Get-Content $pidFile -Raw).Trim()
        if ($pid -and $pid -match '^\d+$') {
            try {
                $process = Get-Process -Id ([int]$pid) -ErrorAction Stop
                if ($process) { return $true }
            } catch {}
        }
    }

    try {
        $processes = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'node|cmd' -and $_.CommandLine -match 'next dev --hostname 0.0.0.0' }
        if ($processes) { return $true }
    } catch {}

    return $false
}

function Start-App {
    if (Is-AppRunning) {
        return $true
    }

    Stop-ManagedProcess
    Remove-Item $stdoutLog, $stderrLog, $browserFlag -Force -ErrorAction SilentlyContinue

    $process = Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-Command', "Set-Location '$appDir'; npm run dev -- --hostname 0.0.0.0 --port 3000" -PassThru
    $process.Id | Set-Content -Path $pidFile

    $deadline = (Get-Date).AddSeconds(90)
    $openedBrowser = $false
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri 'http://localhost:3000' -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                if (-not $openedBrowser) {
                    Start-Process 'http://localhost:3000'
                    $openedBrowser = $true
                    Set-Content -Path $browserFlag -Value 'opened'
                }
                return $true
            }
        } catch {}
        Start-Sleep -Seconds 1
    }

    return $false
}

function Stop-App {
    Stop-ManagedProcess
    Remove-Item $browserFlag -Force -ErrorAction SilentlyContinue
    try {
        $processes = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'node|cmd' -and $_.CommandLine -match 'next dev --hostname 0.0.0.0' }
        foreach ($proc in $processes) {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        }
    } catch {}
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = 'Sanctum Suite'
$form.Size = New-Object System.Drawing.Size(380, 210)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedSingle'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon($iconPath)
$form.BackColor = [System.Drawing.Color]::FromArgb(10, 17, 25)
$form.ForeColor = [System.Drawing.Color]::FromArgb(225, 231, 239)

$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Text = 'Sanctum Suite'
$titleLabel.Font = New-Object System.Drawing.Font('Segoe UI', 18, [System.Drawing.FontStyle]::Bold)
$titleLabel.Location = New-Object System.Drawing.Point(24, 18)
$titleLabel.Size = New-Object System.Drawing.Size(220, 36)
$titleLabel.ForeColor = [System.Drawing.Color]::FromArgb(131, 224, 196)
$form.Controls.Add($titleLabel)

$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Text = 'Status: stopped'
$statusLabel.Font = New-Object System.Drawing.Font('Segoe UI', 11, [System.Drawing.FontStyle]::Regular)
$statusLabel.Location = New-Object System.Drawing.Point(24, 62)
$statusLabel.Size = New-Object System.Drawing.Size(260, 24)
$statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(226, 232, 240)
$form.Controls.Add($statusLabel)

$startButton = New-Object System.Windows.Forms.Button
$startButton.Text = 'Start'
$startButton.Size = New-Object System.Drawing.Size(120, 38)
$startButton.Location = New-Object System.Drawing.Point(24, 110)
$startButton.BackColor = [System.Drawing.Color]::FromArgb(14, 116, 144)
$startButton.ForeColor = [System.Drawing.Color]::White
$startButton.FlatStyle = 'Flat'
$startButton.Add_Click({
    try {
        Ensure-Dependencies
        $launched = Start-App
        if ($launched) {
            $statusLabel.Text = 'Status: running'
            $statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(127, 247, 211)
        } else {
            $statusLabel.Text = 'Status: startup failed'
            $statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(248, 113, 113)
        }
    } catch {
        $statusLabel.Text = 'Status: error'
        $statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(248, 113, 113)
        [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'Sanctum Suite', 'OK', 'Error') | Out-Null
    }
})
$form.Controls.Add($startButton)

$stopButton = New-Object System.Windows.Forms.Button
$stopButton.Text = 'Stop'
$stopButton.Size = New-Object System.Drawing.Size(120, 38)
$stopButton.Location = New-Object System.Drawing.Point(160, 110)
$stopButton.BackColor = [System.Drawing.Color]::FromArgb(51, 65, 85)
$stopButton.ForeColor = [System.Drawing.Color]::White
$stopButton.FlatStyle = 'Flat'
$stopButton.Add_Click({
    try {
        Stop-App
        $statusLabel.Text = 'Status: stopped'
        $statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(226, 232, 240)
    } catch {
        $statusLabel.Text = 'Status: error'
        $statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(248, 113, 113)
    }
})
$form.Controls.Add($stopButton)

$openButton = New-Object System.Windows.Forms.Button
$openButton.Text = 'Open app'
$openButton.Size = New-Object System.Drawing.Size(110, 38)
$openButton.Location = New-Object System.Drawing.Point(292, 110)
$openButton.BackColor = [System.Drawing.Color]::FromArgb(24, 24, 27)
$openButton.ForeColor = [System.Drawing.Color]::White
$openButton.FlatStyle = 'Flat'
$openButton.Add_Click({
    if (Test-Path $browserFlag) {
        Start-Process 'http://localhost:3000'
    } else {
        Start-Process 'http://localhost:3000'
        Set-Content -Path $browserFlag -Value 'opened'
    }
})
$form.Controls.Add($openButton)

$form.ShowIcon = $true
$form.ShowInTaskbar = $true

$form.Add_Shown({ $form.Activate() })
$form.ShowDialog() | Out-Null
