# Changelog

## Unreleased
### Fixed
- **CI lint has never passed on this repository, and now does.** `mypy --strict`
  failed on 48 errors, so `Test`, `Build`, `Docker` and `Extra` were all skipped and
  the tests in this branch had never run anywhere.
  - `viewer.py` imports `plotly.graph_objects`, and **plotly was not declared** in
    `pyproject.toml`. It was reaching the environment only through
    `open3d -> dash -> plotly`, so the import worked by accident and would have
    broken the day open3d dropped dash. It is a dependency now.
  - `cv2`, `trimesh`, `imageio` and `plotly` ship no `py.typed` marker and have no
    typeshed stubs, so strict mode rejects every import of them. `open3d` and
    `freenect` were already listed in `[[tool.mypy.overrides]]`; these four were
    missing.
  - 42 annotations used a bare `np.ndarray`, which `disallow_any_generics` refuses.
    They are `npt.NDArray[Any]` now — the same meaning, said explicitly.
  - The `# type: ignore` on the `freenect` import in `gui.py` was stale once the
    override existed, and strict mode reports an unused ignore as an error.

### Changed
- `scripts/script-helpers` advanced from 0.11.0 to **0.30.0**. Nothing in the library
  was renamed or removed across that span, and the four functions this repo calls
  (`parse_common_args`, `log_info`, `log_warn`, `log_error`) are unchanged.
- The `.gitmodules` url gained its missing `.git` suffix, matching the fleet
  convention.

## 0.2.0 - 2026-04-15
### Fixed
- `probe_device` dead code: orphaned `try/except` block inside `set_tilt_degs` moved
  into `probe_device` where it belongs; function now returns `True` on success (KF-001).
- `depth_format` stored in `metadata.json` at capture time; `reconstruct_mesh` warns
  when a `DEPTH_11BIT` dataset is loaded with `depth_scale=1000.0` (KF-007).
### Added
- `calibration.json` in the working directory is auto-loaded as default intrinsics
  when no explicit `--intrinsics` path is provided (KF-006).
- Calibration status badge in GUI Capture tab shows which intrinsics are active (KF-006).
- Turntable rotation-prior ICP pose estimation: for turntable datasets, each frame is
  registered against frame 0 using a Y-axis rotation initial guess computed from frame
  index, replacing sequential RGBD odometry that accumulated drift (KF-004).
- `reconstruct_mesh` accepts an optional `progress_callback(current, total)` parameter
  called after each frame is integrated into the TSDF volume (KF-008).
- Progress bar and frame counter in GUI Reconstruct tab (KF-008).
- Loop closure for standard scanning mode: ICP between last and first frame distributes
  accumulated drift linearly across all poses; enabled via `loop_closure=True` in
  `ReconstructionConfig` or the Loop Closure checkbox in the GUI (KF-005).
- Pipeline tab as the first GUI tab: guided three-step workflow (Capture, Build Model,
  View) with preset selectors, progress bar, and step status indicators (KF-009).
- Mesh thumbnail rendered via Open3D offscreen renderer after reconstruction; displayed
  in the Pipeline tab and View tab automatically (KF-010).
- Turntable presets and capture metadata fields for turntable settings.

## 0.1.0 - 2026-01-31
- Added Kinect v1 capture pipeline with turntable mode, auto-stop, ROI, and HSV masking.
- Added reconstruction presets, ICP refinement, mesh cleanup, and export helpers.
- Added GUI app with capture/reconstruct/measure/view/calibrate tabs.
- Added calibration, viewer, and measurement tooling.
- Added packaging scripts for Linux/Windows/macOS (PyInstaller).
- Added local scripts for update, lint, and test with script-helpers submodule.
- Added documentation for setup, workflows, GUI, reconstruction, calibration, packaging, and troubleshooting.
