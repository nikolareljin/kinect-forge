# Troubleshooting

## Kinect not detected
- Confirm USB power + data cable are connected.
- Run `python -m kinect_forge status`.
- Ensure `libfreenect-dev` and freenect Python bindings are installed.
- On Ubuntu 24.04+, rerun `./setup` to install `freenect==0.1.0` into `.venv`.
- Check udev rules if access requires sudo.

## Reconstruction looks noisy
- Reduce `depth-max` and enable background masking.
- Use the `small` preset and enable ICP.
- Move slowly and keep lighting consistent.

## Mesh has holes
- Increase `fill-hole-radius`.
- Capture more views of occluded areas.
- Use a turntable to get full coverage.

## GUI doesn't open
- Confirm Tkinter is available (usually `python3-tk` package).
- Try running the CLI pipeline to verify dependencies.
