from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

import cv2
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


def _apply_roi(
    color: np.ndarray, depth: np.ndarray, x: int, y: int, w: int, h: int
) -> tuple[np.ndarray, np.ndarray]:
    if w <= 0 or h <= 0:
        return color, depth
    x0 = max(x, 0)
    y0 = max(y, 0)
    x1 = min(x0 + w, color.shape[1])
    y1 = min(y0 + h, color.shape[0])
    color_masked = np.zeros_like(color)
    depth_masked = np.zeros_like(depth)
    color_masked[y0:y1, x0:x1] = color[y0:y1, x0:x1]
    depth_masked[y0:y1, x0:x1] = depth[y0:y1, x0:x1]
    return color_masked, depth_masked


def _apply_color_mask(
    color: np.ndarray,
    depth: np.ndarray,
    hsv_lower: tuple[int, int, int],
    hsv_upper: tuple[int, int, int],
) -> tuple[np.ndarray, np.ndarray]:
    hsv = cv2.cvtColor(color, cv2.COLOR_RGB2HSV)
    lower = np.array(hsv_lower, dtype=np.uint8)
    upper = np.array(hsv_upper, dtype=np.uint8)
    mask = cv2.inRange(hsv, lower, upper) > 0
    color_masked = color.copy()
    depth_masked = depth.copy()
    color_masked[~mask] = 0
    depth_masked[~mask] = 0
    return color_masked, depth_masked


def capture_frames(
    sensor: Sensor,
    output_dir: Path,
    config: CaptureConfig,
    intrinsics: Optional[KinectIntrinsics] = None,
    preview_cb: Optional[Callable[[np.ndarray, np.ndarray], None]] = None,
    tilt_cb: Optional[Callable[[float], None]] = None,
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
        turntable_model=config.turntable_model,
        turntable_diameter_mm=config.turntable_diameter_mm,
        turntable_rotation_seconds=config.turntable_rotation_seconds,
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
        stagnant = 0
        tilt_angle = config.tilt_min
        tilt_dir = 1.0
        next_tilt_at = config.tilt_hold_frames
        if config.tilt_sweep and tilt_cb is not None:
            tilt_cb(tilt_angle)
        while saved < config.frames and total < config.max_frames_total:
            total += 1
            frame = sensor.get_frame()
            if preview_cb is not None:
                preview_cb(frame.color, frame.depth)
            color, depth = _apply_depth_mask(
                frame.color,
                frame.depth,
                config.depth_min,
                config.depth_max,
                config.depth_scale,
                config.mask_background,
            )
            color, depth = _apply_roi(
                color, depth, config.roi_x, config.roi_y, config.roi_w, config.roi_h
            )
            if config.color_mask:
                color, depth = _apply_color_mask(
                    color, depth, config.hsv_lower, config.hsv_upper
                )
            save_frame = True
            if config.mode == "turntable" and last_saved_depth is not None:
                depth_m = depth.astype(np.float32) / config.depth_scale
                last_m = last_saved_depth.astype(np.float32) / config.depth_scale
                delta = np.mean(np.abs(depth_m - last_m))
                save_frame = bool(delta >= config.change_threshold)

            if save_frame:
                color_path = color_dir / f"color_{saved:06d}.png"
                depth_path = depth_dir / f"depth_{saved:06d}.png"
                _write_color(color_path, color)
                _write_depth(depth_path, depth)
                last_saved_depth = depth
                saved += 1
                stagnant = 0
                if config.tilt_sweep and tilt_cb is not None and saved >= next_tilt_at:
                    tilt_angle += tilt_dir * config.tilt_step
                    if tilt_angle > config.tilt_max:
                        tilt_angle = config.tilt_max
                        tilt_dir = -1.0
                    elif tilt_angle < config.tilt_min:
                        tilt_angle = config.tilt_min
                        tilt_dir = 1.0
                    tilt_cb(tilt_angle)
                    next_tilt_at = saved + max(1, config.tilt_hold_frames)
            elif config.auto_stop and config.mode == "turntable":
                if last_saved_depth is not None:
                    depth_m = depth.astype(np.float32) / config.depth_scale
                    last_m = last_saved_depth.astype(np.float32) / config.depth_scale
                    delta = np.mean(np.abs(depth_m - last_m))
                    if delta < config.auto_stop_delta:
                        stagnant += 1
                    else:
                        stagnant = 0
                    if stagnant >= config.auto_stop_patience:
                        break

            if frame_period > 0:
                elapsed = time.monotonic() - last_ts
                if elapsed < frame_period:
                    time.sleep(frame_period - elapsed)
                last_ts = time.monotonic()
    finally:
        sensor.stop()
