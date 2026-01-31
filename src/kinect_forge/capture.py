from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import imageio.v3 as iio
import numpy as np

from kinect_forge.config import CaptureConfig, KinectIntrinsics
from kinect_forge.dataset import DatasetMeta, ensure_dirs, write_metadata
from kinect_forge.sensors.base import Sensor


def _write_color(path: Path, color: np.ndarray) -> None:
    iio.imwrite(path, color, extension=".png")


def _write_depth(path: Path, depth: np.ndarray) -> None:
    if depth.dtype != np.uint16:
        depth = depth.astype(np.uint16)
    iio.imwrite(path, depth, extension=".png")


def _apply_depth_mask(
    color: np.ndarray,
    depth: np.ndarray,
    depth_min: float,
    depth_max: float,
    depth_scale: float,
    mask_background: bool,
) -> tuple[np.ndarray, np.ndarray]:
    depth_m = depth.astype(np.float32) / depth_scale
    mask = (depth_m >= depth_min) & (depth_m <= depth_max)
    if mask_background:
        color = color.copy()
        color[~mask] = 0
    depth_masked = depth.copy()
    depth_masked[~mask] = 0
    return color, depth_masked


def capture_frames(
    sensor: Sensor,
    output_dir: Path,
    config: CaptureConfig,
    intrinsics: Optional[KinectIntrinsics] = None,
) -> None:
    if config.mode not in {"standard", "turntable"}:
        raise ValueError("mode must be 'standard' or 'turntable'")
    output_dir.mkdir(parents=True, exist_ok=True)
    color_dir, depth_dir = ensure_dirs(output_dir)
    intrinsics = intrinsics or KinectIntrinsics()
    meta = DatasetMeta(
        intrinsics=intrinsics,
        depth_scale=config.depth_scale,
        depth_trunc=config.depth_trunc,
    )
    write_metadata(output_dir, meta)

    sensor.start()
    try:
        for _ in range(config.warmup):
            _ = sensor.get_frame()
            time.sleep(0.01)

        frame_period = 1.0 / config.fps if config.fps > 0 else 0.0
        last_ts = time.monotonic()
        saved = 0
        total = 0
        last_saved_depth: Optional[np.ndarray] = None
        while saved < config.frames and total < config.max_frames_total:
            total += 1
            frame = sensor.get_frame()
            color, depth = _apply_depth_mask(
                frame.color,
                frame.depth,
                config.depth_min,
                config.depth_max,
                config.depth_scale,
                config.mask_background,
            )
            save_frame = True
            if config.mode == "turntable" and last_saved_depth is not None:
                depth_m = depth.astype(np.float32) / config.depth_scale
                last_m = last_saved_depth.astype(np.float32) / config.depth_scale
                delta = np.mean(np.abs(depth_m - last_m))
                save_frame = delta >= config.change_threshold

            if save_frame:
                color_path = color_dir / f"color_{saved:06d}.png"
                depth_path = depth_dir / f"depth_{saved:06d}.png"
                _write_color(color_path, color)
                _write_depth(depth_path, depth)
                last_saved_depth = depth
                saved += 1

            if frame_period > 0:
                elapsed = time.monotonic() - last_ts
                if elapsed < frame_period:
                    time.sleep(frame_period - elapsed)
                last_ts = time.monotonic()
    finally:
        sensor.stop()
