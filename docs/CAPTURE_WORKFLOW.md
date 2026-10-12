# Capture Workflow

## Capture modes

### Standard
Captures every frame at the requested FPS.
Use this when moving the camera steadily around a static object.

### Turntable
Captures a frame only when depth changes enough.
Use this when the object rotates in front of a mostly static camera.

Recommended budget turntable:
- VXB 8-inch motorized display stand.

Parameters to tune:
- `--change-threshold` (meters): larger threshold means fewer frames
- `--max-frames-total`: hard cap for data collection
- `--auto-stop`: stop when motion stalls
- `--auto-stop-patience`: number of stagnant frames before stopping
- `--auto-stop-delta`: how small change must be to count as stagnant

## Depth-to-colour registration

The Kinect v1 depth and RGB cameras sit about 25 mm apart, so raw depth does not
line up with the colour image and the colours land beside the geometry. Capture
asks libfreenect for `DEPTH_REGISTERED`, which aligns depth to the RGB image with
the device's factory calibration. `metadata.json` records `depth_registered`.

- `--no-depth-registration`: keep raw depth (for example, to compare)
- 11-bit depth (`depth_format = "11bit"`) is never registered
- if the freenect bindings lack `DEPTH_REGISTERED`, capture warns and saves raw depth

Calibrate intrinsics on the RGB camera (`kinect-forge calibrate`), since
registered depth is in the RGB camera's frame.

## Background masking
Set depth min/max to reduce background clutter and isolate the object.

Example:
```bash
python -m kinect_forge capture --output scans/part --frames 240 --mode turntable \
  --depth-min 0.4 --depth-max 1.2
```

Example with a turntable preset:
```bash
python -m kinect_forge capture --output scans/part --frames 180 --mode turntable --fps 5 \\
  --turntable-preset vxb-8 --auto-stop
```

## Color masking
Use HSV bounds to keep only the target color. This can help isolate an object from a cluttered scene.

Example:
```bash
python -m kinect_forge capture --output scans/part --frames 200 --color-mask \
  --hsv-lower 10,100,100 --hsv-upper 25,255,255
```

## ROI (Region of Interest)
Restrict capture to a rectangle to ignore background.

Example:
```bash
python -m kinect_forge capture --output scans/part --frames 200 --roi 100,80,300,300
```

## Dataset structure
```
scans/<name>/
  metadata.json
  color/
  depth/
```
