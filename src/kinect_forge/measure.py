from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import open3d as o3d
import numpy as np


@dataclass(frozen=True)
class MeshMeasurements:
    axis_aligned: Tuple[float, float, float]
    oriented: Tuple[float, float, float]
    volume: Optional[float]


def measure_mesh(mesh_path: Path) -> MeshMeasurements:
    mesh = o3d.io.read_triangle_mesh(str(mesh_path))
    if mesh.is_empty():
        raise RuntimeError("Mesh is empty or could not be read.")
    aabb = mesh.get_axis_aligned_bounding_box()
    obb = mesh.get_oriented_bounding_box()
    aabb_dims = _bbox_extent(aabb)
    obb_dims = _bbox_extent(obb)
    volume = None
    if mesh.is_watertight():
        volume = float(mesh.get_volume())
    return MeshMeasurements(
        axis_aligned=(float(aabb_dims[0]), float(aabb_dims[1]), float(aabb_dims[2])),
        oriented=(float(obb_dims[0]), float(obb_dims[1]), float(obb_dims[2])),
        volume=volume,
    )


def _bbox_extent(bbox: object) -> np.ndarray:
    get_extent = getattr(bbox, "get_extent", None)
    if callable(get_extent):
        return np.asarray(get_extent())
    extent = getattr(bbox, "extent", None)
    if extent is not None:
        return np.asarray(extent)
    max_bound = getattr(bbox, "get_max_bound", None)
    min_bound = getattr(bbox, "get_min_bound", None)
    if callable(max_bound) and callable(min_bound):
        return np.asarray(max_bound()) - np.asarray(min_bound())
    raise AttributeError("Bounding box does not expose an extent method or attribute.")
