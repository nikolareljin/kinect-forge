# Packaging

Kinect Forge can be packaged as a standalone desktop app using PyInstaller.

## Linux (App folder)
```bash
python -m venv venv && source venv/bin/activate
pip install -e .[dev,packaging]
./scripts/package.sh
```

Artifacts are placed in `dist/`.

## Windows (PowerShell)
```powershell
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e .[dev,packaging]
.\scripts\package.ps1
```

## macOS (zsh)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .[dev,packaging]
./scripts/package.sh
```

## Notes
- Packaging only bundles the GUI and offline tools. Kinect v1 capture is primarily supported on Linux.
- If PyInstaller cannot find Tkinter, install your system's Tk packages.
- For Open3D, PyInstaller may require extra hidden imports; see `scripts/pyinstaller.spec`.
- CI packaging uses `ci-helpers` reusable workflows and builds Linux artifacts via `./scripts/package.sh`.
