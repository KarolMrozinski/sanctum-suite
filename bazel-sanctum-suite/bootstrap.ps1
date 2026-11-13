$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$msvcCandidates = @(
    "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat",
    "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat",
    "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat",
    "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
)

$msvcBat = $msvcCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $msvcBat) {
    throw "MSVC toolchain not found. Install Visual Studio 2022 Build Tools with C++ desktop workload."
}

$bazelExe = Join-Path $repoRoot ".bin\bazel.exe"
$bazelisk = Get-Command bazelisk -ErrorAction SilentlyContinue

if (-not $bazelisk -and -not (Test-Path $bazelExe)) {
    Write-Host "[sanctum] Bazel was not found; installing via bazelisk is recommended." -ForegroundColor Yellow
}

if (-not (Test-Path (Join-Path $repoRoot ".bin"))) {
    New-Item -ItemType Directory -Path (Join-Path $repoRoot ".bin") -Force | Out-Null
}

$env:BAZELISK_BASE_URL = "https://github.com/bazelbuild/bazelisk/releases/latest/download"
$env:USE_BAZEL_VERSION = "7.4.1"
$env:CC = "cl.exe"
$env:CXX = "cl.exe"
$env:BAZEL_VC = "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC"
$env:BAZEL_VC_FULL_VERSION = "14.3"

$cmd = @"
call ""$msvcBat"" >nul
cd /d "$repoRoot"
where cl
bazel test //... --test_output=errors
"@

Write-Host "[sanctum] Running MSVC/Bazel bootstrap for Windows-native validation..." -ForegroundColor Cyan
cmd.exe /c $cmd
