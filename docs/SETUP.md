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

## System packages
Install libfreenect and the Python bindings:
```bash
sudo apt install libfreenect-dev python3-freenect
```

GUI package (optional):
```bash
sudo apt install python3-tk
```

If you want to access the Kinect without sudo, you may need udev rules for the device.
Refer to your distro's libfreenect package documentation for recommended rules.

## Python environment
```bash
./update
python -m venv venv && source venv/bin/activate
pip install -e .[dev]
```

## Verify hardware
```bash
python -m kinect_forge status
```

## Local checks
```bash
./lint
./test
```
