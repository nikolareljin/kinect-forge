#!/usr/bin/env bash
# SCRIPT: uninstall.sh
# DESCRIPTION: Uninstall kinect-forge system install created by install.sh.
# USAGE: scripts/uninstall.sh [--prefix <path>] [--bin-link <path>]
# ----------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$ROOT_DIR/scripts/include.sh" "$@"

INSTALL_ROOT="${INSTALL_ROOT:-/opt/kinect-forge}"
BIN_LINK="${BIN_LINK:-/usr/local/bin/kinect-forge}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help|-v|--verbose|-d|--debug) shift ;;
    --prefix) INSTALL_ROOT="$2"; shift 2 ;;
    --bin-link) BIN_LINK="$2"; shift 2 ;;
    *) log_error "Unknown argument: $1"; exit 2 ;;
  esac
done

if ! command -v sudo >/dev/null 2>&1; then
  log_error "sudo is required to uninstall."
  exit 1
fi

INSTALL_ROOT="$(readlink -f "$INSTALL_ROOT")"
if [[ -z "$INSTALL_ROOT" || "$INSTALL_ROOT" == "/" || "$INSTALL_ROOT" == "/opt" || "$INSTALL_ROOT" == "/usr" || "$INSTALL_ROOT" == "/usr/local" ]]; then
  log_error "Refusing to remove unsafe install root: $INSTALL_ROOT"
  exit 1
fi

if [[ -L "$BIN_LINK" ]]; then
  LINK_TARGET="$(readlink -f "$BIN_LINK" || true)"
  if [[ "$LINK_TARGET" == "$INSTALL_ROOT/venv/bin/kinect-forge" ]]; then
    sudo rm -f "$BIN_LINK"
  else
    log_warn "Skipping $BIN_LINK (points to $LINK_TARGET)"
  fi
fi

if [[ -d "$INSTALL_ROOT" ]]; then
  sudo rm -rf "$INSTALL_ROOT"
  log_info "Removed $INSTALL_ROOT"
else
  log_warn "Install root not found: $INSTALL_ROOT"
fi
