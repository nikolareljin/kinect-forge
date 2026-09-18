#!/usr/bin/env bash
# SCRIPT: package.sh
# DESCRIPTION: Build the wheel and sdist published as release assets.
# USAGE: ./scripts/package.sh
# PARAMETERS: None
# EXAMPLE: ./scripts/package.sh
#
# This is what a release ships: two files of roughly 33 KB. `pip install` then
# resolves open3d, opencv and the rest from PyPI, where they are cached once per
# machine.
#
# It deliberately does not ship a frozen bundle. scripts/bundle.sh still builds
# one for local use, but open3d's libOpen3D.so alone is 768 MB, so the archive
# lands near 500 MB per release and cannot be trimmed to a sensible size.
# ----------------------------------------------------
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source "$ROOT_DIR/scripts/include.sh" "$@"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install -e "$ROOT_DIR"[packaging]

# A stale dist/ would be published alongside the new files, including a bundle
# left behind by scripts/bundle.sh.
rm -rf "$ROOT_DIR/dist"

python -m build --outdir "$ROOT_DIR/dist"

echo "Built distributables under dist/:"
ls -lh "$ROOT_DIR/dist"
