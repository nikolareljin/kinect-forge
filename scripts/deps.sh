#!/usr/bin/env bash
# SCRIPT: deps.sh
# DESCRIPTION: Install every system package kinect-forge needs to build and run.
# USAGE: ./deps [--runtime-only]
# PARAMETERS:
#   --runtime-only   Skip the compilers and cmake needed to build native wheels.
# EXAMPLE: ./deps
#
# Step 1 of installing kinect-forge. Step 2 is ./install (system-wide) or
# ./setup (development checkout); both call this script unless told not to.
#
# It exists because the list lived in three places that disagreed: setup.sh and
# install.sh each carried their own apt line, and neither included the libraries
# Open3D links at import time. `import open3d` raises
# `ImportError: libEGL.so.1` without them, which is a runtime failure on any
# machine that does not already have a desktop stack, not just a CI runner.
#
# Idempotent: already-installed packages are skipped, and it no-ops off
# Debian/Ubuntu rather than failing.
# ----------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$ROOT_DIR/scripts/include.sh" "$@"

RUNTIME_ONLY=false
for arg in "$@"; do
  case "$arg" in
    --runtime-only) RUNTIME_ONLY=true ;;
  esac
done

# Needed to run the application at all.
PACKAGES=(
  python3-tk        # the GUI is Tk; it is not part of a stock python3
  libegl1           # Open3D links EGL and GL when the module is imported,
  libgl1            #   not when something is first rendered
  libgomp1          # OpenMP runtime Open3D is built against
  libusb-1.0-0      # libfreenect talks to the Kinect over USB
)

# Needed to build the freenect bindings and any native wheel without a match.
BUILD_PACKAGES=(
  libfreenect-dev
  build-essential
  pkg-config
  cmake
)

if ! $RUNTIME_ONLY; then
  PACKAGES+=("${BUILD_PACKAGES[@]}")
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "deps: not a Debian/Ubuntu host. Install these by hand: ${PACKAGES[*]}"
  exit 0
fi

missing=()
for pkg in "${PACKAGES[@]}"; do
  if ! dpkg -s "$pkg" >/dev/null 2>&1; then
    missing+=("$pkg")
  fi
done

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  elif [ ${#missing[@]} -gt 0 ]; then
    echo "deps: need root to install ${missing[*]}, and sudo is unavailable." >&2
    exit 1
  fi
fi

if [ ${#missing[@]} -eq 0 ]; then
  echo "deps: all system packages already present."
else
  echo "deps: installing ${missing[*]}"
  $SUDO apt-get update -qq
  DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y --no-install-recommends "${missing[@]}"
fi

# Optional: the distro may ship prebuilt freenect bindings. When it does not,
# setup.sh and install.sh fall back to the pip package, so this is not fatal.
if ! $RUNTIME_ONLY && ! dpkg -s python3-freenect >/dev/null 2>&1; then
  if ! DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y python3-freenect 2>/dev/null; then
    echo "deps: python3-freenect is not packaged here; the pip fallback will be used."
  fi
fi

echo "deps: system dependencies are ready."
