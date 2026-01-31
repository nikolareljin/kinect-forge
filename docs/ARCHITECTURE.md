# Architecture

## Modules
- `kinect_forge.sensors`: sensor backends and discovery
- `kinect_forge.capture`: synchronized RGB-D capture + preprocessing
- `kinect_forge.reconstruct`: TSDF/mesh reconstruction
- `kinect_forge.measure`: dimensions and volume utilities
- `kinect_forge.calibration`: chessboard-based intrinsics calibration
- `kinect_forge.export`: mesh export helpers (PLY/OBJ/GLB)
- `kinect_forge.presets`: tuned reconstruction presets
- `kinect_forge.viewer`: mesh and dataset preview
- `kinect_forge.io`: file formats and dataset organization

## Data flow
1) Sensor backend produces calibrated RGB + depth frames.
2) Capture pipeline timestamps, filters, and persists frames.
3) Reconstruction integrates frames into a TSDF volume.
4) Mesh extraction and cleanup produce final model.
5) Measurement utilities compute dimensions and volume.
