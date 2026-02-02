# Setup

## System requirements
- Ubuntu 20.04+ (tested target)
- Kinect for Windows v1 + USB power adapter
- Python 3.10+
- Enough disk space for RGB-D captures (hundreds of MB per session)

## Cross-platform note
The GUI runs on Linux, Windows, and macOS via Tkinter. Kinect v1 capture is primarily supported on Linux through libfreenect. On other systems you can still use reconstruction and measurement if you already have datasets.

## Packaging note
See `docs/PACKAGING.md` for creating desktop bundles on Linux/Windows/macOS.

## Recommended turntable (budget)
- VXB 8-inch motorized display stand (USB or battery powered, ~16s per rotation, 7 lb capacity).

## System packages
Install libfreenect and the Python bindings:
```bash
sudo apt install libfreenect-dev
# Optional (bindings may be unavailable on some Ubuntu versions):
sudo apt install python3-freenect || true
```

GUI package (optional):
```bash
sudo apt install python3-tk
```

Recommended full install (Ubuntu):
```bash
sudo apt update
sudo apt install -y libfreenect-dev python3-tk \
  build-essential pkg-config cmake
# Optional (bindings may be unavailable on some Ubuntu versions):
sudo apt install -y python3-freenect || true
```

`./install` on Ubuntu performs the same dependency install by default. If
`python3-freenect` is unavailable (Ubuntu 24.04+), it will attempt
`pip install freenect` into the system venv. Use `./install --no-system-deps`
if you want to skip apt installs.

If you want to access the Kinect without sudo, you may need udev rules for the device.
Refer to your distro's libfreenect package documentation for recommended rules.

## Python environment
```bash
./update
./setup
python -m venv venv && source venv/bin/activate
pip install -e .[dev]
```

## Verify hardware
```bash
python -m kinect_forge status
```

Kinect live feed test (dev tool):
```bash
./scripts/test_kinect.sh --list
./scripts/test_kinect.sh --index 0
./scripts/test_kinect.sh --index 0 --depth
```

## End-to-end test (CLI)
Capture → preview → reconstruct → measure.
```bash
python -m kinect_forge capture --output scans/test --frames 180 --mode turntable --fps 5 \
  --auto-stop --depth-min 0.4 --depth-max 1.2 --turntable-preset vxb-8

python -m kinect_forge view --dataset scans/test --every 10

python -m kinect_forge reconstruct --input-dir scans/test --output-mesh scans/test/model.glb \
  --preset small --icp --smooth 8 --fill-hole-radius 0.01

python -m kinect_forge measure --mesh scans/test/model.glb
```

## End-to-end test (GUI)
```bash
python -m kinect_forge gui
```
Steps:
1) Status tab → Check Status.
2) Capture tab → Start Capture.
3) View tab → Open Viewer.
4) Reconstruct tab → Reconstruct.
5) Measure tab → Measure.

## Optional calibration (better scale accuracy)
```bash
python -m kinect_forge calibrate --images calib/*.png --rows 7 --cols 9 --square-size 0.025 \
  --output intrinsics.json

python -m kinect_forge capture --output scans/calibrated --frames 200 --intrinsics-path intrinsics.json
```

## Local checks
```bash
./lint
./test
```
