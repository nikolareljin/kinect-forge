# Changelog

## Unreleased
### Fixed
- **`scripts/package.sh` never installed PyInstaller.** It called
  `python -m PyInstaller` in whatever environment it found, so the release build
  failed with `No module named PyInstaller` the first time it ever ran. The
  `packaging` extra declaring `pyinstaller>=6.7` already existed; nothing
  installed it. The script now creates and populates a venv the same way
  `lint.sh` and `test.sh` do.
- **The release would have carried thousands of loose files.** `artifact_paths`
  was `dist/**`, and PyInstaller's COLLECT build is a directory — 6424 files and
  1.3 GB here, since `--collect-submodules open3d` bundles the whole library — so
  every one of them would have been attached to the release individually.
  PyInstaller's generated `.spec` is ignored.

### Changed
- **A release ships the wheel and sdist, not a frozen bundle.** The single
  archive was still 501 MB, and it cannot be made small: `libOpen3D.so` alone is
  768 MB, and dropping everything this project does not use — the TensorFlow ops
  (45 MB), the PyTorch ops (35 MB), `dash` (35 MB), `jedi` (32 MB) — still leaves
  over a gigabyte. `scripts/package.sh` now builds the distributables instead:
  **two files, 76 KB total**, with `pip` resolving open3d from PyPI where it is
  cached once per machine rather than copied into every release. The frozen build
  moved to `scripts/bundle.sh` for local use and is not run by CI; the
  `pyinstaller` dependency moved to a `bundle` extra, and `packaging` now carries
  `build`.
- **The packaging workflow could never have started.** `release-build.yml`
  declares `contents: write`, this repository's default workflow token is `read`,
  and `package.yml` granted nothing — so GitHub refused the run before any step,
  as `startup_failure`. Pushing `0.2.0`, the first tag ever to reach the workflow,
  is what surfaced it.
- **Merging a release branch tagged nothing.** Only `ci.yml` runs on a push to
  `main`, and `package.yml` triggers *on* a tag, so nothing in this repository
  could ever create one — 0.2.0 reached `main` untagged for that reason. The
  sibling repositories in this workspace have carried an `auto-tag-release.yml`
  for some time; this one was onboarded to the shared workflows with lint/test
  and packaging only. Added, calling ci-helpers' tag-only `auto-tag.yml` with
  `update_production_tag: false`, since this repository has no floating
  `production` ref and `package.yml` already publishes the release.
- **Tagging a release the way this repository tags would not have built one.**
  `package.yml` triggered on `v*`, but the only tag here is `0.1.0` — bare, no
  prefix. The trigger now matches the convention actually in use.
- **CI could not import Open3D at all.** `import open3d` links EGL at import time,
  so it raised `ImportError: libEGL.so.1` on a bare GitHub runner. The suite hid
  this behind `pytest.importorskip("open3d")` — every Open3D test skipped, which is
  why the reconstruction code shipped with the pose bug above. `scripts/ci_system_deps.sh`
  installs the libraries and runs ahead of `./test`. It cannot hang off
  `extra_command`, because ci-helpers runs the `Extra` step *after* `Test`.
- **Every reconstruction fused each surface twice.** `reconstruct.py` mixed two
  opposite pose conventions. `_estimate_poses` accumulates RGBD odometry into
  **world-to-camera** matrices, but `_refine_poses_icp`, `_estimate_turntable_poses`
  and the TSDF integration call all treated them as **camera-to-world** — because
  `registration_icp(source, target)` returns `T_target<-source`, which composes the
  other way round. On a synthetic scene with only 0.15 rad of camera motion, the
  integrated mesh came out with twice the vertices and a bounding box 0.22 m wider
  than the object. The three mismatched sites now follow the producer, the
  convention is written down at the top of the module, and two tests pin it by
  driving the refinement with a known-perfect registration oracle.
- **The mesh thumbnail could never have rendered.** `_render_mesh_thumbnail` called
  `o3d.io.write_image_to_memory`, which does not exist in Open3D, and passed a
  bounding box to `setup_camera` where a 3-vector centre belongs while omitting the
  required `up` argument. A `try/except Exception: return None` around the whole
  body turned both into a silently missing image. It now encodes through
  `o3d.io.write_image`, frames the mesh from its bounding sphere, and only catches
  the one call that legitimately depends on the machine — building an
  `OffscreenRenderer` without a GPU — which it logs.
### Changed
- Thumbnail rendering moved from `gui.py` to `viewer.py`. It is pure Open3D with no
  Tk dependency, so its tests no longer need to skip when tkinter is absent, and
  `tests/test_reconstruct.py` no longer skips itself when Open3D fails to import —
  Open3D is a declared dependency and a failure to import it is a real failure.
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
- **The calibration status said "loaded" for a file it could not read.**
  `_refresh_calib_status` tested only that `calibration.json` existed, while
  `capture._find_default_calibration()` quietly fell back to the Kinect v1
  defaults when the file was malformed — the interface claiming one thing and the
  capture doing another. It asks the same helper capture asks now, so the two
  cannot disagree, and says so explicitly when the file is present but unreadable.

### Changed
- **The lint is pinned to a rule set instead of inheriting one.** `[tool.ruff]`
  set only `line-length`, so it took whatever ruff's defaults were, and
  `pyproject.toml` asks for `ruff>=0.6` — pip installs the newest. ruff 0.16
  widened its defaults and **147 errors appeared in CI without a line of this
  code changing**. `select` is now explicit and wider than the pre-0.16 default:
  import sorting, pyupgrade, bugbear and comprehension checks. `B008` is ignored
  because every hit is `typer.Option` in an argument default, which is typer's
  documented idiom. 127 findings were auto-fixed; six needed judgement —
  a chained exception in `presets.py`, `strict=True` on a `zip` whose inputs must
  correspond, and four `dict()` calls rewritten as literals.
- **mypy analyses as 3.12, not the 3.10 in `requires-python`.** numpy 2.3+ writes
  its stubs with PEP 695 `type` statements, which mypy refuses to read when
  targeting anything older — it stops inside `numpy/__init__.pyi` before checking
  a line of this project. CI runs 3.12, so this matches what executes. The cost is
  recorded in `pyproject.toml`: the `>=3.10` claim is no longer type-verified.
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
