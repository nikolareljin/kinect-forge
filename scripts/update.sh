#!/usr/bin/env bash
# SCRIPT: update
# DESCRIPTION: Sync and update git submodules, even if the repo was cloned without them.
# USAGE: ./update
# PARAMETERS: None
# EXAMPLE: ./update
# ----------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "scripts" ]; then
  ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  ROOT_DIR="$SCRIPT_DIR"
fi
SCRIPT_HELPERS_DIR="${SCRIPT_HELPERS_DIR:-$ROOT_DIR/scripts/script-helpers}"
if [ -f "$SCRIPT_HELPERS_DIR/helpers.sh" ]; then
  source "$SCRIPT_HELPERS_DIR/helpers.sh"
  shlib_import help logging
  parse_common_args "$@"
else
  if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    echo "Usage: $0"
    echo
    echo "Sync and update git submodules, even if the repo was cloned without them."
    exit 0
  fi
fi

if ! command -v git >/dev/null 2>&1; then
  echo "Git is required to update submodules." >&2
  exit 1
fi

cd "$ROOT_DIR"

git submodule sync --recursive
git submodule update --init --recursive

echo "Submodules are up to date."
