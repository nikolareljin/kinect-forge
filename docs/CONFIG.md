# Configuration

## Presets
Presets are loaded at runtime from `presets.json`, which ships inside the
`kinect_forge` package (`src/kinect_forge/presets.json` in a checkout). You can
override the path with `KINECT_FORGE_PRESETS=/path/to/presets.json`.

Groups:
- `capture`: capture defaults (fps, frames, depth range, masking).
- `reconstruction`: reconstruction defaults (TSDF + ICP parameters).

Capture fields can also include tilt sweep options:
- `tilt_sweep` (true/false)
- `tilt_min`, `tilt_max`, `tilt_step` (degrees)
- `tilt_hold_frames` (frames before next tilt)

Example:
```bash
export KINECT_FORGE_PRESETS="$HOME/my-presets.json"
```
