#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$InstallDir = "$env:LOCALAPPDATA\sshine\bin",
    [switch]$NoPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step { param($msg) Write-Host "==> " -ForegroundColor Green -NoNewline; Write-Host $msg -ForegroundColor White }
function Write-Ok   { param($msg) Write-Host "  v $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "  ! $msg" -ForegroundColor Yellow }
function Write-Fail { param($msg) Write-Host "  x $msg" -ForegroundColor Red; exit 1 }

$arch = if ([System.Environment]::Is64BitOperatingSystem) {
    if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "aarch64" } else { "x86_64" }
} else {
    Write-Fail "32-bit Windows is not supported."
}

$repo        = "realm-net/sshine"
$platform    = "windows-$arch"
$archiveName = "sshine-${platform}.zip"
$baseUrl     = "https://github.com/${repo}/releases/latest/download"
$archiveUrl  = "$baseUrl/$archiveName"
$checksumUrl = "$baseUrl/$archiveName.sha256"

Write-Host ""
Write-Host "  sshine installer  (release build)" -ForegroundColor Cyan
Write-Host "  https://github.com/$repo"
Write-Host ""
Write-Step "Platform: $platform"

$tmpDir      = Join-Path $env:TEMP "sshine-install-$(Get-Random)"
New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
$archivePath = Join-Path $tmpDir $archiveName

Write-Step "Downloading..."
try {
    $ProgressPreference = "SilentlyContinue"
    Invoke-WebRequest -Uri $archiveUrl -OutFile $archivePath -UseBasicParsing
    Write-Ok "Downloaded $archiveName"
} catch {
    Write-Fail "Download failed: $archiveUrl`n$_"
}

Write-Step "Verifying checksum..."
$checksumPath = Join-Path $tmpDir "$archiveName.sha256"
try {
    Invoke-WebRequest -Uri $checksumUrl -OutFile $checksumPath -UseBasicParsing
    $expected = (Get-Content $checksumPath).Trim().Split(" ")[0]
    $actual   = (Get-FileHash -Algorithm SHA256 -Path $archivePath).Hash.ToLower()
    if ($expected -ne $actual) {
        Write-Fail "Checksum mismatch!`n  Expected: $expected`n  Got:      $actual"
    }
    Write-Ok "Checksum verified"
} catch {
    Write-Warn "Checksum not available — skipping verification"
}

Write-Step "Extracting..."
$extractDir = Join-Path $tmpDir "extract"
Expand-Archive -Path $archivePath -DestinationPath $extractDir -Force

$binary = Join-Path $extractDir "sshine.exe"
if (-not (Test-Path $binary)) {
    $binary = Get-ChildItem -Path $extractDir -Recurse -Filter "sshine.exe" |
              Select-Object -First 1 -ExpandProperty FullName
}
if (-not $binary) { Write-Fail "sshine.exe not found in archive." }

Write-Step "Installing to $InstallDir..."
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Copy-Item -Path $binary -Destination (Join-Path $InstallDir "sshine.exe") -Force
Write-Ok "Installed: $InstallDir\sshine.exe"

if (-not $NoPath) {
    $userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
    if ($userPath -notlike "*$InstallDir*") {
        Write-Step "Adding $InstallDir to user PATH..."
        [System.Environment]::SetEnvironmentVariable("PATH", "$userPath;$InstallDir", "User")
        $env:PATH = "$env:PATH;$InstallDir"
        Write-Ok "PATH updated — restart your terminal to apply"
    } else {
        Write-Ok "Already in PATH"
    }
}

Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "  Installed:" -ForegroundColor Cyan
try { & "$InstallDir\sshine.exe" --version } catch {}
Write-Host ""
Write-Host "  Run " -NoNewline
Write-Host "sshine init" -ForegroundColor Cyan -NoNewline
Write-Host " to get started."
Write-Host "  Community: " -NoNewline
Write-Host "https://t.me/sshine_talks" -ForegroundColor Cyan
Write-Host ""
