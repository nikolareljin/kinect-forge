# GUI Guide

Launch:
```bash
python -m kinect_forge gui
```

## Tabs

### Status
Checks whether the Kinect v1 backend is reachable.

### Capture
- Output directory and frame count
- Turntable mode to reduce redundant frames
- Depth min/max for background masking
- Auto-stop for turntable scans
- ROI and HSV color masking
- Turntable preset and metadata fields
- Optional intrinsics JSON

### Reconstruct
- Choose a preset and apply it
- Adjust TSDF, ICP, smoothing, and hole filling
- Export via output filename extension (.ply, .obj, .stl, .glb)

### Measure
Compute axis-aligned and oriented dimensions plus volume (if watertight).

### View
Preview a dataset (point cloud) or view a mesh.

### Calibrate
Use chessboard images to estimate intrinsics and save to JSON.

## Tips
- Use the **Apply Preset** button after changing preset names.
- For small objects, start with `small` + ICP enabled.
- For larger scenes, switch to `medium` or `large`.
- Use ROI or color masking if the background is noisy.
- For cross-platform distribution, see `docs/PACKAGING.md`.
 - Use turntable preset `vxb-8` for the budget recommendation.
