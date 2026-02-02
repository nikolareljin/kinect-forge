# Configuration

## Presets
Presets are loaded from `config/presets.json` at runtime. You can override the
path with `KINECT_FORGE_PRESETS=/path/to/presets.json`.

Groups:
- `capture`: capture defaults (fps, frames, depth range, masking).
- `reconstruction`: reconstruction defaults (TSDF + ICP parameters).

Capture fields can also include tilt sweep options:
- `tilt_sweep` (true/false)
- `tilt_min`, `tilt_max`, `tilt_step` (degrees)
- `tilt_hold_frames` (frames before next tilt)

Example:
```bash
export KINECT_FORGE_PRESETS=/home/nikos/my-presets.json
```
