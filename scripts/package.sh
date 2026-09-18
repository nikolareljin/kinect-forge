#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source "$ROOT_DIR/scripts/include.sh" "$@"
cd "$ROOT_DIR"

# PyInstaller was invoked without ever being installed, so this script could only
# work on a machine where someone had installed it by hand. It also needs the
# project importable: it builds from src/kinect_forge/__main__.py and collects
# open3d's submodules. The `packaging` extra in pyproject.toml exists for exactly
# this and nothing had ever installed it.
#
# Same venv layout as lint.sh and test.sh, so all three behave identically here
# and in CI.
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install -e "$ROOT_DIR"[packaging]

python -m PyInstaller \
  --noconfirm \
  --windowed \
  --name kinect-forge \
  --add-data "docs:docs" \
  --collect-submodules open3d \
  --hidden-import tkinter \
  --hidden-import tkinter.ttk \
  src/kinect_forge/__main__.py

# PyInstaller's COLLECT build is a directory tree -- 6424 files and 1.3 GB for
# this project, because --collect-submodules open3d pulls in the whole library.
# package.yml uploads `artifact_paths` as GitHub release assets, so publishing
# the tree directly would attach every one of those files individually. Ship one
# archive instead.
VERSION=$(python -c "import tomllib, pathlib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])")
PLATFORM="$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m)"
TARBALL="kinect-forge-${VERSION}-${PLATFORM}.tar.gz"

tar -czf "dist/${TARBALL}" -C dist kinect-forge

echo "Built package under dist/${TARBALL}"
