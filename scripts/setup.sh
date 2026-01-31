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
sudo apt install -y libfreenect-dev python3-freenect python3-tk \
  build-essential pkg-config cmake

VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install -e "$ROOT_DIR".[dev]

echo "Setup complete. Activate with: source $VENV_DIR/bin/activate"
