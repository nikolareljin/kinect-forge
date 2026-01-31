# AGENTS.md

## Project Overview
Kinect Forge is a Python-based 3D scanning toolkit for Kinect depth cameras on Ubuntu. It targets small-object scanning first, with a roadmap to larger scenes.

## Conventions
- Python 3.10+
- 4-space indent, type hints
- Keep modules small and composable
- Prefer CLI-first workflows; GUI is available for end-to-end scans

## Common Commands
```bash
./update
python -m venv venv && source venv/bin/activate
pip install -e .[dev]
python -m kinect_forge --help
pytest -q
./lint
./test
```

## Structure
- `src/kinect_forge/` library code
- `src/kinect_forge/cli.py` CLI entry
- `docs/` design and technical notes
- `scripts/` helper scripts

## Notes
- Do not commit device firmware or proprietary SDK binaries.
- Hardware integration lives behind clear interfaces so alternative sensors can be added later.
- `scripts/script-helpers/` is a vendored git submodule; do not edit files inside it.
