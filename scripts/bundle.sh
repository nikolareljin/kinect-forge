#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source "$ROOT_DIR/scripts/include.sh" "$@"
cd "$ROOT_DIR"

# PyInstaller needs installing, and needs the project importable: it builds from
# src/kinect_forge/__main__.py and collects open3d's submodules. Same venv layout
# as lint.sh and test.sh.
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install -e "$ROOT_DIR"[bundle]

python -m PyInstaller \
  --noconfirm \
  --windowed \
  --name kinect-forge \
  --add-data "docs:docs" \
  --collect-submodules open3d \
  --hidden-import tkinter \
  --hidden-import tkinter.ttk \
  src/kinect_forge/__main__.py

# The archive this produces is around 500 MB and is NOT published. open3d's own
# libOpen3D.so is 768 MB before anything else is added, so a frozen bundle of
# this application cannot be made small -- stripping the TensorFlow ops (45 MB),
# the PyTorch ops (35 MB), dash (35 MB) and jedi (32 MB), none of which this
# project uses, still leaves well over a gigabyte.
#
# Releases ship the wheel and sdist from scripts/package.sh instead, at ~33 KB
# each, and pip resolves open3d from PyPI where it is cached once per machine
# rather than copied into every release.
#
# This script stays for building a local run-anywhere bundle by hand. Nothing in
# CI calls it.
VERSION=$(python -c "import tomllib, pathlib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])")
PLATFORM="$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m)"
TARBALL="kinect-forge-${VERSION}-${PLATFORM}.tar.gz"

tar -czf "dist/${TARBALL}" -C dist kinect-forge

echo "Built package under dist/${TARBALL}"
