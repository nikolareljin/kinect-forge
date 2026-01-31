#!/usr/bin/env bash
# SCRIPT: include.sh
# DESCRIPTION: Common loader for repo scripts (helpers + standard args).
# USAGE: source ./scripts/include.sh "$@"
# ----------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRIPT_HELPERS_DIR="${SCRIPT_HELPERS_DIR:-$ROOT_DIR/scripts/script-helpers}"

if [ ! -f "$SCRIPT_HELPERS_DIR/helpers.sh" ]; then
  echo "script-helpers is missing. Run ./update to initialize submodules." >&2
  exit 1
fi

source "$SCRIPT_HELPERS_DIR/helpers.sh"
shlib_import help logging
parse_common_args "$@"
