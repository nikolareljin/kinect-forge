# User Guide

## Recommended workflow (small objects)
1) Place the object on a turntable or rotate it slowly by hand.
2) Capture with turntable mode to reduce redundant frames.
3) Reconstruct using the `small` preset.
4) Inspect the mesh and measure dimensions.
5) Export to your modeling or printing tool.

## CLI quick start
```bash
python -m kinect_forge capture --output scans/part --frames 240 --mode turntable --fps 5 \
  --depth-min 0.4 --depth-max 1.2 --auto-stop --turntable-preset vxb-8
python -m kinect_forge reconstruct --input-dir scans/part --output-mesh scans/part/model.glb \
  --preset small --icp
python -m kinect_forge measure --mesh scans/part/model.glb
```

## GUI quick start
```bash
python -m kinect_forge gui
```

Use the tabs to configure capture, reconstruction, and preview without the CLI.

## Cross-platform note
The GUI is built with Tkinter, which runs on Linux, Windows, and macOS. Kinect v1 support is primarily on Linux via libfreenect. For non-Linux systems, you can still use the GUI for dataset reconstruction and measurement if you already have captured data.

## Presets
- `small`: tight voxel size, tuned for tabletop objects
- `medium`: balanced quality/speed
- `large`: looser settings for bigger scenes

You can start with a preset and override any value.

## Files produced by a scan
```
scans/<name>/
  metadata.json
  color/color_000000.png
  depth/depth_000000.png
  ...
```

## Model outputs
- `.ply`, `.obj`, `.stl`, `.glb`
- Use `.glb` when you want a compact, portable file
