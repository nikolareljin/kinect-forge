#!/usr/bin/env bash
# SCRIPT: test.sh
# DESCRIPTION: Run local test suite.
# USAGE: ./test
# PARAMETERS: None
# EXAMPLE: ./test
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

pytest -q
