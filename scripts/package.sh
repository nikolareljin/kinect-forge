#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source "$ROOT_DIR/scripts/include.sh" "$@"
cd "$ROOT_DIR"

python -m PyInstaller \
  --noconfirm \
  --windowed \
  --name kinect-forge \
  --add-data "docs:docs" \
  --collect-submodules open3d \
  --hidden-import tkinter \
  --hidden-import tkinter.ttk \
  src/kinect_forge/__main__.py

echo "Built package under dist/"
