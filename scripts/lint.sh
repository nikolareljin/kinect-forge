#!/usr/bin/env bash
# SCRIPT: lint.sh
# DESCRIPTION: Run style and type checks locally.
# USAGE: ./lint
# PARAMETERS: None
# EXAMPLE: ./lint
# ----------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$ROOT_DIR/scripts/include.sh" "$@"

VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install -e "$ROOT_DIR"[dev]

ruff check "$ROOT_DIR"
mypy "$ROOT_DIR/src"
