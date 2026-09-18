#!/usr/bin/env bash
# SCRIPT: ci_system_deps.sh
# DESCRIPTION: Install the system libraries Open3D needs to import on a headless runner.
# USAGE: ./scripts/ci_system_deps.sh
# PARAMETERS: None
# EXAMPLE: ./scripts/ci_system_deps.sh
#
# Open3D links against EGL/GL at import time, not just when rendering, so
# `import open3d` raises ImportError: libEGL.so.1 on a bare GitHub runner. That
# is why the suite previously guarded itself with pytest.importorskip("open3d"):
# every Open3D test silently skipped, and the reconstruction tests had never
# actually run in CI. Installing the libraries is the fix; skipping only hid it.
#
# No-op off Debian/Ubuntu and on any machine that already has the libraries, so
# it is safe to call from a developer shell as well as from CI.
# ----------------------------------------------------
set -euo pipefail

if ! command -v apt-get >/dev/null 2>&1; then
  echo "ci_system_deps: not a Debian/Ubuntu host, nothing to do."
  exit 0
fi

PACKAGES=(libegl1 libgl1 libgomp1)

missing=()
for pkg in "${PACKAGES[@]}"; do
  if ! dpkg -s "$pkg" >/dev/null 2>&1; then
    missing+=("$pkg")
  fi
done

if [ ${#missing[@]} -eq 0 ]; then
  echo "ci_system_deps: all Open3D runtime libraries already present."
  exit 0
fi

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "ci_system_deps: need root to install ${missing[*]}, and sudo is unavailable." >&2
    exit 1
  fi
fi

echo "ci_system_deps: installing ${missing[*]}"
$SUDO apt-get update -qq
DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y --no-install-recommends "${missing[@]}"
