# Reconstruction

## Pipeline overview
1) Load RGB-D pairs and camera intrinsics.
2) Estimate camera poses (odometry).
3) Integrate into TSDF volume.
4) Extract mesh and clean up.

## Presets
- `small`: higher resolution, better for tabletop items
- `medium`: balanced for larger objects
- `large`: faster, coarser for big scenes

## Key parameters
- `voxel_length`: smaller values give more detail but require more compute
- `sdf_trunc`: truncation distance; keep proportional to voxel size
- `depth_trunc`: ignore far depth noise
- `icp`: helps align frames, especially with turntable motion
- `smooth` + `fill_hole_radius`: improve mesh readability

## Example
```bash
python -m kinect_forge reconstruct --input-dir scans/part --output-mesh scans/part/model.glb \
  --preset small --icp --smooth 8 --fill-hole-radius 0.01
```
