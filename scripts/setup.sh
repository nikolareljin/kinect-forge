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

if ! command -v sudo >/dev/null 2>&1; then
  echo "sudo is required to install system packages." >&2
  exit 1
fi

sudo apt update
sudo apt install -y libfreenect-dev python3-tk \
  build-essential pkg-config cmake
if ! sudo apt install -y python3-freenect; then
  echo "WARN: python3-freenect package not found. Kinect v1 capture will be unavailable unless you install freenect bindings manually." >&2
fi

VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install -e "${ROOT_DIR}[dev]"

if ! python - <<'PYEOF'
import importlib
raise SystemExit(0 if importlib.util.find_spec("freenect") else 1)
PYEOF
then
  echo "Attempting to install freenect bindings into local venv..."
  if ! python -m pip install freenect; then
    echo "WARN: pip install freenect failed. See docs/SETUP.md for manual steps." >&2
  fi
fi

echo "Setup complete. Activate with: source $VENV_DIR/bin/activate"
