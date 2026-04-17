#!/usr/bin/env bash
# SCRIPT: setup.sh
# DESCRIPTION: Install system deps and bootstrap local dev environment.
# USAGE: ./setup
# PARAMETERS: None
# EXAMPLE: ./setup
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
  echo "Installing freenect Python bindings via pip package $FREENECT_PIP_SPEC..."
  "$python_bin" -m pip install --upgrade "$FREENECT_PIP_SPEC"
}

if ! command -v sudo >/dev/null 2>&1; then
  echo "sudo is required to install system packages." >&2
  exit 1
fi

PYTHON_BIN="$(choose_python_bin || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "python3 is required to create virtual environment." >&2
  exit 1
fi

sudo apt update
sudo apt install -y libfreenect-dev python3-tk \
  build-essential pkg-config cmake
if ! sudo apt install -y python3-freenect; then
  echo "INFO: python3-freenect package not available via apt. Will use pip package fallback." >&2
fi

VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install -e "${ROOT_DIR}[dev]"

if ! has_freenect_module python; then
  if ! install_freenect_bindings python; then
    echo "WARN: freenect pip install failed. See docs/SETUP.md for manual steps." >&2
  fi
fi

echo "Setup complete. Activate with: source $VENV_DIR/bin/activate"
