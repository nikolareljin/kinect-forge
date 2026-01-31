# Calibration

## Why calibrate?
Default Kinect intrinsics are a reasonable starting point, but calibration improves scale accuracy.

## Chessboard calibration
Capture 10–20 images of a printed chessboard at different angles and distances.

Run:
```bash
python -m kinect_forge calibrate --images calib/*.png --rows 7 --cols 9 --square-size 0.025 \
  --output intrinsics.json
```

Then use the output:
```bash
python -m kinect_forge capture --output scans/calibrated --frames 200 \
  --intrinsics-path intrinsics.json
```

## Notes
- `rows` and `cols` are the inner corners (not squares).
- `square-size` is in meters.
