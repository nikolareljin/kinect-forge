# Kinect Forge

Kinect Forge is a modular 3D scanning toolkit for Ubuntu that uses Kinect depth cameras to build clean 3D models
from small objects first, then scales to larger scenes later.

## Why resurrect a Kinect?
You already own a solid depth camera. Instead of letting it gather dust, turn it into a practical 3D scanner for:
- Rebuilding broken parts by capturing exact dimensions.
- Rapid prototyping and fit checks without expensive scanners.
- Learning 3D scanning workflows (capture → reconstruction → measurement) on a budget.
- Expanding later to larger objects once your pipeline is tuned.

Kinect Forge makes this smooth with turntable capture, auto-stop, cleanup, and export to common formats like GLB/OBJ.

## Why this stack
- **Python** for rapid iteration and maintainability.
- **Open3D** for RGB-D integration and mesh extraction.
- **OpenCV** for image handling and calibration utilities.
- **Optional sensor backends** (libfreenect or libfreenect2) to keep hardware support pluggable.

## Goals
- Capture depth + RGB frames reliably.
- Estimate dimensions and volume for small objects.
- Reconstruct a watertight or near-watertight mesh.
- Keep a clean, extensible architecture for future sensors and larger scenes.

## Quick start
```bash
./update
./setup
source .venv/bin/activate
python -m kinect_forge --help
```

## Kinect v1 setup (Ubuntu)
```bash
sudo apt install libfreenect-dev python3-freenect
```

GUI dependencies:
```bash
sudo apt install python3-tk
```

Plug in the Kinect v1 and verify:
```bash
./update
./setup
source .venv/bin/activate
python -m kinect_forge status
```

Capture + reconstruct:
```bash
python -m kinect_forge capture --output scans/teapot --frames 300
python -m kinect_forge reconstruct --input-dir scans/teapot --output-mesh scans/teapot/model.ply
python -m kinect_forge measure --mesh scans/teapot/model.ply
```

Recommended turntable (budget):
- VXB 8-inch motorized display stand (USB or battery, 200mm diameter, ~16s per rotation, 7 lb load capacity).

Turntable preset + keyframe selection + ICP:
```bash
python -m kinect_forge capture --output scans/gear --frames 180 --mode turntable --fps 5 \\
  --turntable-preset vxb-8
python -m kinect_forge reconstruct --input-dir scans/gear --output-mesh scans/gear/model.obj \\
  --preset small --icp --smooth 10
```

Export formats: use `.ply`, `.obj`, `.stl`, or `.glb` in `--output-mesh`.
Presets: `small`, `medium`, `large`.

Launch GUI:
```bash
python -m kinect_forge gui
```

Cross-platform GUI: Tkinter works on Linux/Windows/macOS, but Kinect v1 capture is primarily supported on Linux via libfreenect.

## Scripts
```bash
./update   # init/update submodules
./setup    # install system deps + create venv + install python deps
./lint     # ruff + mypy
./test     # pytest
./scripts/package.sh   # build PyInstaller package (Linux/macOS)
./scripts/package.ps1  # build PyInstaller package (Windows)
```

## Documentation
- `CHANGELOG.md`
- `docs/SETUP.md`
- `docs/USER_GUIDE.md`
- `docs/GUI.md`
- `docs/CAPTURE_WORKFLOW.md`
- `docs/RECONSTRUCTION.md`
- `docs/CALIBRATION.md`
- `docs/TROUBLESHOOTING.md`
- `docs/PACKAGING.md`

## CI
- `.github/workflows/ci.yml` (tests + lint via ci-helpers)
- `.github/workflows/package.yml` (package builds via ci-helpers)

Background masking (small objects):
```bash
python -m kinect_forge capture --output scans/part --frames 240 --depth-min 0.4 --depth-max 1.2
```

Auto-stop + ROI + color mask example:
```bash
python -m kinect_forge capture --output scans/part --frames 240 --mode turntable --auto-stop \
  --roi 120,80,320,320 --color-mask --hsv-lower 10,100,100 --hsv-upper 25,255,255
```

Preview scans:
```bash
python -m kinect_forge view --dataset scans/part --every 10
python -m kinect_forge view --mesh scans/part/model.glb
```

Local checks:
```bash
./lint
./test
```

Calibration (chessboard):
```bash
python -m kinect_forge calibrate --images calib/*.png --rows 7 --cols 9 --square-size 0.025 \\
  --output intrinsics.json
python -m kinect_forge capture --output scans/calibrated --frames 200 --intrinsics-path intrinsics.json
```

## High-level architecture
- **Sensor backends**: Kinect v1 (libfreenect) or v2 (libfreenect2), later RealSense or others.
- **Capture pipeline**: frame sync, filtering, calibration, registration.
- **Reconstruction**: TSDF integration + mesh extraction.
- **Measurements**: bounding box, volume, scale.

## Roadmap
See `docs/ROADMAP.md`.
