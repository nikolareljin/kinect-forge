from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from kinect_forge.config import ReconstructionConfig

_DEFAULT_PRESETS_PATH = Path(__file__).resolve().parents[2] / "config" / "presets.json"


def _load_presets() -> Dict[str, Any]:
    override = os.environ.get("KINECT_FORGE_PRESETS", "").strip()
    path = Path(override) if override else _DEFAULT_PRESETS_PATH
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise ValueError(f"Preset config not found: {path}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Preset config invalid JSON: {path}") from exc


def _get_preset(group: str, name: str) -> Dict[str, Any]:
    presets = _load_presets()
    group_data = presets.get(group, {})
    if not isinstance(group_data, dict):
        raise ValueError(f"Preset group '{group}' is invalid.")
    preset = group_data.get(name)
    if not isinstance(preset, dict):
        raise ValueError(f"Preset '{name}' not found in '{group}'.")
    return preset


def reconstruction_preset(name: str) -> ReconstructionConfig:
    preset = name.lower()
    data = _get_preset("reconstruction", preset)
    return ReconstructionConfig(
        voxel_length=float(data.get("voxel_length", 0.003)),
        sdf_trunc=float(data.get("sdf_trunc", 0.03)),
        depth_trunc=float(data.get("depth_trunc", 2.0)),
        keyframe_threshold=float(data.get("keyframe_threshold", 0.003)),
        icp_refine=bool(data.get("icp_refine", True)),
        icp_distance=float(data.get("icp_distance", 0.015)),
        icp_voxel=float(data.get("icp_voxel", 0.008)),
        icp_iterations=int(data.get("icp_iterations", 40)),
        smooth_iterations=int(data.get("smooth_iterations", 5)),
        fill_hole_radius=float(data.get("fill_hole_radius", 0.008)),
        preset=preset,
    )


def capture_preset(name: str):
    preset = name.lower()
    return _get_preset("capture", preset)
