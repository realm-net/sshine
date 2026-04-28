# install-build.ps1 — сборка и установка sshine из исходников (Windows)
# Использование: irm https://raw.githubusercontent.com/realm-net/sshine/main/scripts/install-build.ps1 | iex
#
# Требования: git, Python 3.14+, uv, pyarmor, pyinstaller

#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$InstallDir  = "$env:LOCALAPPDATA\sshine\bin",
    [string]$BuildDir    = (Join-Path $env:TEMP "sshine-build-$(Get-Random)"),
    [string]$RepoUrl     = "https://github.com/realm-net/sshine",
    [switch]$KeepBuild,
    [switch]$NoPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference    = "SilentlyContinue"

function Write-Step  { param($msg) Write-Host "==> " -ForegroundColor Green -NoNewline; Write-Host $msg -ForegroundColor White }
function Write-Ok    { param($msg) Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "  ! $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "  ✗ $msg" -ForegroundColor Red; exit 1 }

function Require-Command {
    param($name, $hint = "")
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        $msg = "Required command not found: $name"
        if ($hint) { $msg += "`n  $hint" }
        Write-Fail $msg
    }
}

Write-Host ""
Write-Host "  sshine installer  (build from source)" -ForegroundColor Cyan
Write-Host "  https://github.com/realm-net/sshine"
Write-Host ""

# ── Git ──────────────────────────────────────────────────────────────────────
Require-Command "git" "Install Git from https://git-scm.com"

# ── Python 3.14+ ─────────────────────────────────────────────────────────────
Write-Step "Checking Python..."
$pythonExe = $null
foreach ($candidate in @("python3.14", "python3", "python")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $ver = & $candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($ver) {
            $parts = $ver.Split(".")
            if ([int]$parts[0] -ge 3 -and [int]$parts[1] -ge 14) {
                $pythonExe = $candidate
                break
            }
        }
    }
}
if (-not $pythonExe) {
    Write-Fail "Python 3.14+ is required.`n  Download from https://python.org or use pyenv-win."
}
Write-Ok "Python: $pythonExe ($ver)"

# ── uv ───────────────────────────────────────────────────────────────────────
Write-Step "Checking uv..."
if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
    Write-Step "Installing uv..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:PATH = "$env:LOCALAPPDATA\Programs\uv;$env:PATH"
    if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
        Write-Fail "uv installation failed. Install manually: https://docs.astral.sh/uv/"
    }
}
Write-Ok "uv: $(uv --version)"

# ── pyarmor ──────────────────────────────────────────────────────────────────
Write-Step "Checking pyarmor..."
if (-not (Get-Command "pyarmor" -ErrorAction SilentlyContinue)) {
    Write-Step "Installing pyarmor..."
    uv tool install pyarmor
}
$pyarmorVer = pyarmor --version 2>&1 | Select-Object -First 1
Write-Ok "pyarmor: $pyarmorVer"

# ── pyinstaller ──────────────────────────────────────────────────────────────
Write-Step "Checking pyinstaller..."
if (-not (Get-Command "pyinstaller" -ErrorAction SilentlyContinue)) {
    Write-Step "Installing pyinstaller..."
    uv tool install pyinstaller
}
Write-Ok "pyinstaller: $(pyinstaller --version)"

# ── Клонирование ─────────────────────────────────────────────────────────────
Write-Step "Cloning $RepoUrl..."
New-Item -ItemType Directory -Path $BuildDir -Force | Out-Null
$srcDir = Join-Path $BuildDir "sshine"
git clone --depth=1 $RepoUrl $srcDir
Set-Location $srcDir
Write-Ok "Cloned to $srcDir"

# ── Зависимости ──────────────────────────────────────────────────────────────
Write-Step "Installing project dependencies..."
uv sync
Write-Ok "Dependencies installed"

# ── Обфускация pyarmor ───────────────────────────────────────────────────────
Write-Step "Obfuscating with pyarmor..."
pyarmor gen `
    --output dist\obfuscated `
    --recursive `
    src\sshine
Write-Ok "Obfuscation complete → dist\obfuscated\"

# ── Сборка PyInstaller ───────────────────────────────────────────────────────
Write-Step "Building binary with PyInstaller..."

$arch     = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "aarch64" } else { "x86_64" }
$distName = "sshine-windows-$arch"

pyinstaller `
    --onefile `
    --name sshine `
    --paths dist\obfuscated `
    --paths src `
    --collect-all sshine `
    --hidden-import sshine `
    --hidden-import asyncssh `
    --hidden-import aiosqlite `
    --hidden-import anyio `
    --hidden-import cryptography `
    --hidden-import keyring `
    --hidden-import "ruamel.yaml" `
    --clean `
    src\sshine\__main__.py

Write-Ok "Binary built: dist\sshine.exe"

# ── Упаковка в архив ─────────────────────────────────────────────────────────
Write-Step "Creating archive: $distName.zip"
New-Item -ItemType Directory -Path "dist\release" -Force | Out-Null
Copy-Item "dist\sshine.exe" "dist\release\sshine.exe" -Force
Compress-Archive -Path "dist\release\sshine.exe" -DestinationPath "dist\release\$distName.zip" -Force

$hash = (Get-FileHash -Algorithm SHA256 "dist\release\$distName.zip").Hash.ToLower()
"$hash  $distName.zip" | Out-File -Encoding ASCII "dist\release\$distName.zip.sha256"
Write-Ok "Archive: dist\release\$distName.zip"

# ── Установка ────────────────────────────────────────────────────────────────
Write-Step "Installing to $InstallDir..."
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Copy-Item "dist\sshine.exe" (Join-Path $InstallDir "sshine.exe") -Force
Write-Ok "Installed: $InstallDir\sshine.exe"

# ── PATH ─────────────────────────────────────────────────────────────────────
if (-not $NoPath) {
    $userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
    if ($userPath -notlike "*$InstallDir*") {
        Write-Step "Adding $InstallDir to user PATH..."
        [System.Environment]::SetEnvironmentVariable("PATH", "$userPath;$InstallDir", "User")
        $env:PATH = "$env:PATH;$InstallDir"
        Write-Ok "PATH updated — restart your terminal to apply"
    }
}

# ── Очистка ──────────────────────────────────────────────────────────────────
Set-Location $env:USERPROFILE
if (-not $KeepBuild) {
    Remove-Item -Recurse -Force $BuildDir -ErrorAction SilentlyContinue
}

# ── Готово ───────────────────────────────────────────────────────────────────
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
