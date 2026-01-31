# Kinect Forge

Kinect Forge is a modular 3D scanning toolkit for Ubuntu that uses Kinect depth cameras to build clean 3D models
from small objects first, then scales to larger scenes later.

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
python -m venv venv && source venv/bin/activate
pip install -e .[dev]
python -m kinect_forge --help
```

## Kinect v1 setup (Ubuntu)
```bash
sudo apt install libfreenect-dev python3-freenect
```

Plug in the Kinect v1 and verify:
```bash
python -m kinect_forge status
```

Capture + reconstruct:
```bash
python -m kinect_forge capture --output scans/teapot --frames 300
python -m kinect_forge reconstruct --input-dir scans/teapot --output-mesh scans/teapot/model.ply
python -m kinect_forge measure --mesh scans/teapot/model.ply
```

Turntable preset + keyframe selection + ICP:
```bash
python -m kinect_forge capture --output scans/gear --frames 180 --mode turntable --fps 5
python -m kinect_forge reconstruct --input-dir scans/gear --output-mesh scans/gear/model.obj \\
  --preset small --icp --smooth 10
```

Export formats: use `.ply`, `.obj`, `.stl`, or `.glb` in `--output-mesh`.
Presets: `small`, `medium`, `large`.

Background masking (small objects):
```bash
python -m kinect_forge capture --output scans/part --frames 240 --depth-min 0.4 --depth-max 1.2
```

Preview scans:
```bash
python -m kinect_forge view --dataset scans/part --every 10
python -m kinect_forge view --mesh scans/part/model.glb
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
