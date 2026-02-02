#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$ROOT_DIR/scripts/include.sh" "$@"

PYTHON_BIN="${PYTHON_BIN:-}"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
SYSTEM_VENV="${SYSTEM_VENV:-/opt/kinect-forge/venv}"

if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$SYSTEM_VENV/bin/python" ]]; then
    PYTHON_BIN="$SYSTEM_VENV/bin/python"
  elif [[ -x "$VENV_DIR/bin/python" ]]; then
    PYTHON_BIN="$VENV_DIR/bin/python"
  elif [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
    PYTHON_BIN="$VIRTUAL_ENV/bin/python"
  else
    PYTHON_BIN="python3"
  fi
fi

exec "$PYTHON_BIN" -m kinect_forge gui
