#!/usr/bin/env bash
# SCRIPT: install.sh
# DESCRIPTION: Install kinect-forge into a system venv and expose the CLI.
# USAGE: scripts/install.sh [--dev] [--prefix <path>] [--bin-link <path>]
# ----------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$ROOT_DIR/scripts/include.sh" "$@"

INSTALL_ROOT="${INSTALL_ROOT:-/opt/kinect-forge}"
VENV_DIR="${VENV_DIR:-$INSTALL_ROOT/venv}"
BIN_LINK="${BIN_LINK:-/usr/local/bin/kinect-forge}"
DEV_EXTRAS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help|-v|--verbose|-d|--debug) shift ;;
    --dev) DEV_EXTRAS=true; shift ;;
    --prefix) INSTALL_ROOT="$2"; VENV_DIR="$INSTALL_ROOT/venv"; shift 2 ;;
    --bin-link) BIN_LINK="$2"; shift 2 ;;
    *) log_error "Unknown argument: $1"; exit 2 ;;
  esac
done

if ! command -v sudo >/dev/null 2>&1; then
  log_error "sudo is required to install system packages."
  exit 1
fi

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python)"
fi

if [[ -z "$PYTHON_BIN" ]]; then
  log_error "python3 is required to install kinect-forge."
  exit 1
fi

if ! "$PYTHON_BIN" - <<'PYEOF'
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PYEOF
then
  log_error "Python 3.10+ is required (found: $("$PYTHON_BIN" -V 2>&1))."
  exit 1
fi

sudo mkdir -p "$INSTALL_ROOT"
if [[ ! -d "$VENV_DIR" ]]; then
  sudo "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

sudo "$VENV_DIR/bin/python" -m pip install --upgrade pip
if $DEV_EXTRAS; then
  sudo "$VENV_DIR/bin/pip" install --upgrade "${ROOT_DIR}[dev]"
else
  sudo "$VENV_DIR/bin/pip" install --upgrade "$ROOT_DIR"
fi

sudo ln -sf "$VENV_DIR/bin/kinect-forge" "$BIN_LINK"

log_info "Installed to $INSTALL_ROOT"
log_info "CLI available at: $BIN_LINK"
