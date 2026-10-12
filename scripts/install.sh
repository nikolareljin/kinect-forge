#!/usr/bin/env bash
# SCRIPT: install.sh
# DESCRIPTION: Install kinect-forge into a system venv and expose the CLI.
# USAGE: scripts/install.sh [--dev] [--prefix <path>] [--bin-link <path>] [--no-system-deps] [--no-udev]
# ----------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$ROOT_DIR/scripts/include.sh" "$@"
FREENECT_PIP_SPEC="${FREENECT_PIP_SPEC:-freenect==0.1.0}"

choose_python_bin() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi

  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi

  return 1
}

has_freenect_module() {
  local python_bin="$1"
  "$python_bin" - <<'PYEOF'
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("freenect") else 1)
PYEOF
}

install_freenect_bindings() {
  local python_bin="$1"
  log_info "Installing freenect Python bindings via pip package $FREENECT_PIP_SPEC..."
  sudo "$VENV_DIR/bin/pip" install --upgrade "$FREENECT_PIP_SPEC"
}

INSTALL_ROOT="${INSTALL_ROOT:-/opt/kinect-forge}"
VENV_DIR="${VENV_DIR:-$INSTALL_ROOT/venv}"
BIN_LINK="${BIN_LINK:-/usr/local/bin/kinect-forge}"
DEV_EXTRAS=false
INSTALL_SYSTEM_DEPS=true
INSTALL_UDEV=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help|-v|--verbose|-d|--debug) shift ;;
    --dev) DEV_EXTRAS=true; shift ;;
    --prefix) INSTALL_ROOT="$2"; VENV_DIR="$INSTALL_ROOT/venv"; shift 2 ;;
    --bin-link) BIN_LINK="$2"; shift 2 ;;
    --no-system-deps) INSTALL_SYSTEM_DEPS=false; shift ;;
    --no-udev) INSTALL_UDEV=false; shift ;;
    *) log_error "Unknown argument: $1"; exit 2 ;;
  esac
done

if ! command -v sudo >/dev/null 2>&1; then
  log_error "sudo is required to install system packages."
  exit 1
fi

if $INSTALL_SYSTEM_DEPS; then
  # Step 1: system packages, from the single list in scripts/deps.sh. Pass
  # --no-system-deps to skip when ./deps has already been run.
  log_info "Installing system dependencies..."
  "$ROOT_DIR/scripts/deps.sh"
fi

if $INSTALL_UDEV; then
  if [[ -x "$ROOT_DIR/scripts/install_udev_rules.sh" ]]; then
    log_info "Installing udev rules for Kinect v1..."
    sudo "$ROOT_DIR/scripts/install_udev_rules.sh"
  else
    log_warn "Missing install_udev_rules.sh; skipping udev rules."
  fi
fi

PYTHON_BIN="$(choose_python_bin || true)"

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

# Build the wheel as the invoking user, then install that file as root. Running
# `sudo pip install <checkout>` builds in the checkout and leaves a root-owned
# build/ and *.egg-info there, which later non-root builds cannot overwrite.
# Under `sudo ./install` that means building as $SUDO_USER, not root.
BUILD_AS=()
BUILD_USER="$(id -un)"
if [[ $EUID -eq 0 && -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
  BUILD_AS=(sudo -u "$SUDO_USER")
  BUILD_USER="$SUDO_USER"
fi
for leftover in "$ROOT_DIR/build" "$ROOT_DIR"/src/*.egg-info; do
  if [[ -e "$leftover" ]] && ! "${BUILD_AS[@]}" test -w "$leftover"; then
    log_error "$leftover is not writable by $BUILD_USER (left by an earlier root build)."
    log_error "Remove it with: sudo rm -rf \"$leftover\""
    exit 1
  fi
done
WHEEL_DIR="$(mktemp -d)"
trap 'rm -rf "$WHEEL_DIR"' EXIT
if [[ ${#BUILD_AS[@]} -gt 0 ]]; then
  chown "$SUDO_USER" "$WHEEL_DIR"
fi
"${BUILD_AS[@]}" "$VENV_DIR/bin/pip" wheel --no-deps --wheel-dir "$WHEEL_DIR" "$ROOT_DIR"
WHEEL_FILES=("$WHEEL_DIR"/kinect_forge-*.whl)
if [[ ! -f "${WHEEL_FILES[0]}" ]]; then
  log_error "Wheel build produced no kinect_forge wheel in $WHEEL_DIR."
  exit 1
fi
WHEEL="${WHEEL_FILES[0]}"
WHEEL_SPEC="$WHEEL"
if $DEV_EXTRAS; then
  WHEEL_SPEC="${WHEEL}[dev]"
fi
# A wheel with an unchanged version number counts as already installed, so force
# the package itself, then let pip resolve its dependencies as usual.
sudo "$VENV_DIR/bin/pip" install --force-reinstall --no-deps "$WHEEL"
sudo "$VENV_DIR/bin/pip" install --upgrade "$WHEEL_SPEC"

if ! has_freenect_module "$VENV_DIR/bin/python"; then
  if ! install_freenect_bindings "$VENV_DIR/bin/python"; then
    log_warn "freenect pip install failed. See docs/SETUP.md for manual steps."
  fi
fi

sudo ln -sf "$VENV_DIR/bin/kinect-forge" "$BIN_LINK"

log_info "Installed to $INSTALL_ROOT"
log_info "CLI available at: $BIN_LINK"
