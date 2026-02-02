from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class KinectIntrinsics:
    width: int = 640
    height: int = 480
    fx: float = 525.0
    fy: float = 525.0
    cx: float = 319.5
    cy: float = 239.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(payload: Dict[str, Any]) -> "KinectIntrinsics":
        return KinectIntrinsics(
            width=int(payload["width"]),
            height=int(payload["height"]),
            fx=float(payload["fx"]),
            fy=float(payload["fy"]),
            cx=float(payload["cx"]),
            cy=float(payload["cy"]),
        )


@dataclass(frozen=True)
class CaptureConfig:
    frames: int = 300
    fps: float = 30.0
    warmup: int = 15
    depth_scale: float = 1000.0
    depth_trunc: float = 3.0
    mode: str = "standard"
    change_threshold: float = 0.01
    max_frames_total: int = 3000
    depth_min: float = 0.1
    depth_max: float = 4.0
    mask_background: bool = True
    auto_stop: bool = False
    auto_stop_patience: int = 30
    auto_stop_delta: float = 0.002
    roi_x: int = 0
    roi_y: int = 0
    roi_w: int = 0
    roi_h: int = 0
    color_mask: bool = False
    hsv_lower: tuple[int, int, int] = (0, 0, 0)
    hsv_upper: tuple[int, int, int] = (179, 255, 255)
    turntable_model: Optional[str] = None
    turntable_diameter_mm: Optional[int] = None
    turntable_rotation_seconds: Optional[float] = None


@dataclass(frozen=True)
class ReconstructionConfig:
    voxel_length: float = 0.004
    sdf_trunc: float = 0.04
    depth_scale: float = 1000.0
    depth_trunc: float = 3.0
    keyframe_threshold: float = 0.0
    icp_refine: bool = False
    icp_distance: float = 0.02
    icp_voxel: float = 0.01
    icp_iterations: int = 30
    smooth_iterations: int = 0
    fill_hole_radius: float = 0.0
    preset: str = "small"
