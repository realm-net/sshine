#!/usr/bin/env bash
set -euo pipefail

REPO="realm-net/sshine"
INSTALL_DIR="${SSHINE_INSTALL_DIR:-/usr/local/bin}"
TMP_DIR="$(mktemp -d)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${BOLD}${GREEN}==>${RESET} ${BOLD}$*${RESET}"; }
warn()    { echo -e "${YELLOW}  ! $*${RESET}"; }
error()   { echo -e "${RED}  ✗ $*${RESET}" >&2; exit 1; }
success() { echo -e "${GREEN}  ✓ $*${RESET}"; }

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

detect_platform() {
    local os arch
    os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    arch="$(uname -m)"

    case "$os" in
        linux)  ;;
        darwin) ;;
        *) error "Unsupported OS: $os" ;;
    esac

    case "$arch" in
        x86_64|amd64)  arch="x86_64" ;;
        aarch64|arm64) arch="aarch64" ;;
        *) error "Unsupported architecture: $arch" ;;
    esac

    echo "${os}-${arch}"
}

require_cmd() {
    command -v "$1" &>/dev/null || error "Required command not found: $1"
}

require_cmd curl
require_cmd tar

echo ""
echo -e "${BOLD}  sshine installer${RESET}  (release build)"
echo "  https://github.com/${REPO}"
echo ""

PLATFORM="$(detect_platform)"
info "Platform: $PLATFORM"

BASE_URL="https://github.com/${REPO}/releases/latest/download"
ARCHIVE_NAME="sshine-${PLATFORM}.tar.gz"
ARCHIVE_URL="${BASE_URL}/${ARCHIVE_NAME}"
CHECKSUM_URL="${BASE_URL}/${ARCHIVE_NAME}.sha256"

info "Downloading..."
curl -fSL --progress-bar "$ARCHIVE_URL" -o "$TMP_DIR/$ARCHIVE_NAME" \
    || error "Download failed: $ARCHIVE_URL"

info "Verifying checksum..."
if curl -fsSL "$CHECKSUM_URL" -o "$TMP_DIR/${ARCHIVE_NAME}.sha256" 2>/dev/null; then
    EXPECTED="$(awk '{print $1}' "$TMP_DIR/${ARCHIVE_NAME}.sha256")"
    if command -v sha256sum &>/dev/null; then
        ACTUAL="$(sha256sum "$TMP_DIR/$ARCHIVE_NAME" | awk '{print $1}')"
    else
        ACTUAL="$(shasum -a 256 "$TMP_DIR/$ARCHIVE_NAME" | awk '{print $1}')"
    fi
    [[ "$EXPECTED" == "$ACTUAL" ]] || error "Checksum mismatch! Expected: $EXPECTED  Got: $ACTUAL"
    success "Checksum verified"
else
    warn "Checksum file not available — skipping verification"
fi

info "Extracting..."
tar -xzf "$TMP_DIR/$ARCHIVE_NAME" -C "$TMP_DIR"

BINARY="$TMP_DIR/sshine"
[[ -f "$BINARY" ]] || error "Binary not found in archive"
chmod +x "$BINARY"

info "Installing to $INSTALL_DIR..."
if [[ -w "$INSTALL_DIR" ]]; then
    cp "$BINARY" "$INSTALL_DIR/sshine"
else
    sudo cp "$BINARY" "$INSTALL_DIR/sshine"
fi

success "Installed: $(command -v sshine)"

echo ""
echo -e "${BOLD}Installed:${RESET}"
"$INSTALL_DIR/sshine" --version 2>/dev/null || true

echo ""
echo -e "  Run ${BOLD}sshine init${RESET} to get started."
echo -e "  Community: ${BOLD}https://t.me/sshine_talks${RESET}"
echo ""
