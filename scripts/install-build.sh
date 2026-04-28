#!/usr/bin/env bash
# install-build.sh — сборка и установка sshine из исходников
# Использование: curl -fsSL https://raw.githubusercontent.com/realm-net/sshine/main/scripts/install-build.sh | bash
#
# Требования: git, python3.14+, uv (или pip), pyarmor, pyinstaller

set -euo pipefail

REPO_URL="https://github.com/realm-net/sshine"
INSTALL_DIR="${SSHINE_INSTALL_DIR:-/usr/local/bin}"
BUILD_DIR="${SSHINE_BUILD_DIR:-$(mktemp -d)}"
KEEP_BUILD="${SSHINE_KEEP_BUILD:-0}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${BOLD}${GREEN}==>${RESET} ${BOLD}$*${RESET}"; }
warn()    { echo -e "${YELLOW}  ! $*${RESET}"; }
error()   { echo -e "${RED}  ✗ $*${RESET}" >&2; exit 1; }
success() { echo -e "${GREEN}  ✓ $*${RESET}"; }

cleanup() {
    [[ "$KEEP_BUILD" == "1" ]] || rm -rf "$BUILD_DIR"
}
trap cleanup EXIT

echo ""
echo -e "${BOLD}  sshine installer${RESET}  (build from source)"
echo "  https://github.com/realm-net/sshine"
echo ""

# ── Зависимости ─────────────────────────────────────────────────────────────
require_cmd() {
    command -v "$1" &>/dev/null || error "Required command not found: $1. Install it and re-run."
}

require_cmd git

# Python: ищем 3.14+
PYTHON=""
for candidate in python3.14 python3 python; do
    if command -v "$candidate" &>/dev/null; then
        VER="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'  2>/dev/null || echo "0.0")"
        MAJOR="${VER%%.*}"; MINOR="${VER##*.}"
        if [[ "$MAJOR" -ge 3 && "$MINOR" -ge 14 ]]; then
            PYTHON="$candidate"
            break
        fi
    fi
done
[[ -n "$PYTHON" ]] || error "Python 3.14+ is required. Install it from https://python.org"
success "Python: $PYTHON ($VER)"

# uv
if command -v uv &>/dev/null; then
    success "uv: $(uv --version)"
else
    info "Installing uv..."
    curl -fsSL https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    command -v uv &>/dev/null || error "uv installation failed"
    success "uv installed"
fi

# pyarmor
if ! command -v pyarmor &>/dev/null; then
    info "Installing pyarmor..."
    uv tool install pyarmor || pip install pyarmor
fi
success "pyarmor: $(pyarmor --version 2>&1 | head -1)"

# pyinstaller
if ! command -v pyinstaller &>/dev/null; then
    info "Installing pyinstaller..."
    uv tool install pyinstaller || pip install pyinstaller
fi
success "pyinstaller: $(pyinstaller --version)"

# ── Клонирование ─────────────────────────────────────────────────────────────
info "Cloning $REPO_URL..."
git clone --depth=1 "$REPO_URL" "$BUILD_DIR/sshine"
cd "$BUILD_DIR/sshine"
success "Cloned to $BUILD_DIR/sshine"

# ── Зависимости проекта ──────────────────────────────────────────────────────
info "Installing project dependencies..."
uv sync
success "Dependencies installed"

# ── Обфускация pyarmor ───────────────────────────────────────────────────────
info "Obfuscating with pyarmor..."
VENV_PYTHON="$BUILD_DIR/sshine/.venv/bin/python"
[[ -f "$VENV_PYTHON" ]] || VENV_PYTHON="$BUILD_DIR/sshine/.venv/bin/python3"

pyarmor gen \
    --output dist/obfuscated \
    --recursive \
    src/sshine

success "Obfuscation complete → dist/obfuscated/"

# ── Сборка PyInstaller ───────────────────────────────────────────────────────
info "Building binary with PyInstaller..."

PLATFORM="$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m)"
DIST_NAME="sshine-${PLATFORM}"

pyinstaller \
    --onefile \
    --name sshine \
    --paths dist/obfuscated \
    --paths src \
    --collect-all sshine \
    --hidden-import sshine \
    --hidden-import asyncssh \
    --hidden-import aiosqlite \
    --hidden-import anyio \
    --hidden-import cryptography \
    --hidden-import keyring \
    --hidden-import "ruamel.yaml" \
    --strip \
    --clean \
    src/sshine/__main__.py

success "Binary built: dist/sshine"

# ── Упаковка в архив ─────────────────────────────────────────────────────────
info "Creating archive: ${DIST_NAME}.tar.gz"
mkdir -p dist/release
cp dist/sshine "dist/release/sshine"
cd dist/release
tar -czf "${DIST_NAME}.tar.gz" sshine
sha256sum "${DIST_NAME}.tar.gz" > "${DIST_NAME}.tar.gz.sha256"
cd "$BUILD_DIR/sshine"
success "Archive: dist/release/${DIST_NAME}.tar.gz"

# ── Установка ────────────────────────────────────────────────────────────────
info "Installing to $INSTALL_DIR..."
if [[ -w "$INSTALL_DIR" ]]; then
    cp dist/sshine "$INSTALL_DIR/sshine"
else
    sudo cp dist/sshine "$INSTALL_DIR/sshine"
fi
chmod +x "$INSTALL_DIR/sshine"

success "sshine installed: $(command -v sshine)"
echo ""
echo -e "${BOLD}Installed:${RESET}"
"$INSTALL_DIR/sshine" --version 2>/dev/null || true
echo ""
echo -e "  Run ${BOLD}sshine init${RESET} to get started."
echo -e "  Community: ${BOLD}https://t.me/sshine_talks${RESET}"
echo ""
