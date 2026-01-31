from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from kinect_forge.config import KinectIntrinsics


@dataclass(frozen=True)
class DatasetMeta:
    intrinsics: KinectIntrinsics
    depth_scale: float
    depth_trunc: float
    color_format: str = "rgb"
    depth_unit: str = "mm"
    turntable_model: Optional[str] = None
    turntable_diameter_mm: Optional[int] = None
    turntable_rotation_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intrinsics": self.intrinsics.to_dict(),
            "depth_scale": self.depth_scale,
            "depth_trunc": self.depth_trunc,
            "color_format": self.color_format,
            "depth_unit": self.depth_unit,
            "turntable_model": self.turntable_model,
            "turntable_diameter_mm": self.turntable_diameter_mm,
            "turntable_rotation_seconds": self.turntable_rotation_seconds,
        }


def ensure_dirs(root: Path) -> Tuple[Path, Path]:
    color_dir = root / "color"
    depth_dir = root / "depth"
    color_dir.mkdir(parents=True, exist_ok=True)
    depth_dir.mkdir(parents=True, exist_ok=True)
    return color_dir, depth_dir


def write_metadata(root: Path, meta: DatasetMeta) -> None:
    path = root / "metadata.json"
    path.write_text(json.dumps(meta.to_dict(), indent=2))


def load_metadata(root: Path) -> DatasetMeta:
    payload = json.loads((root / "metadata.json").read_text())
    intrinsics = KinectIntrinsics.from_dict(payload["intrinsics"])
    return DatasetMeta(
        intrinsics=intrinsics,
        depth_scale=float(payload["depth_scale"]),
        depth_trunc=float(payload["depth_trunc"]),
        color_format=payload.get("color_format", "rgb"),
        depth_unit=payload.get("depth_unit", "mm"),
        turntable_model=payload.get("turntable_model"),
        turntable_diameter_mm=payload.get("turntable_diameter_mm"),
        turntable_rotation_seconds=payload.get("turntable_rotation_seconds"),
    )


def list_frame_pairs(root: Path) -> List[Tuple[Path, Path]]:
    color_dir = root / "color"
    depth_dir = root / "depth"
    color_files = sorted(color_dir.glob("color_*.png"))
    pairs: List[Tuple[Path, Path]] = []
    for color in color_files:
        idx = color.stem.split("_")[-1]
        depth = depth_dir / f"depth_{idx}.png"
        if depth.exists():
            pairs.append((color, depth))
    return pairs
