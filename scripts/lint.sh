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

# Bootstrap submodules when running in CI before the update step
SCRIPT_HELPERS_DIR="${SCRIPT_HELPERS_DIR:-$ROOT_DIR/scripts/script-helpers}"
if [ ! -f "$SCRIPT_HELPERS_DIR/helpers.sh" ]; then
  git -C "$ROOT_DIR" submodule update --init --recursive
fi

source "$ROOT_DIR/scripts/include.sh" "$@"
cd "$ROOT_DIR"

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
