from __future__ import annotations

from typing import Any

import numpy as np

from kinect_forge.viewer import _thumbnail_camera


class _Bounds:
    def __init__(self, center: list[float], extent: list[float]) -> None:
        self._center = np.array(center, dtype=np.float64)
        self._extent = np.array(extent, dtype=np.float64)

    def get_center(self) -> Any:
        return self._center

    def get_extent(self) -> Any:
        return self._extent


def test_thumbnail_camera_frames_the_bounding_sphere() -> None:
    center, eye, up = _thumbnail_camera(_Bounds([1.0, 2.0, 3.0], [2.0, 2.0, 2.0]))

    assert np.allclose(center, [1.0, 2.0, 3.0])
    assert np.allclose(up, [0.0, -1.0, 0.0])

    # A 60 degree vertical FOV only fits a sphere of `radius` beyond
    # radius / tan(30 degrees) ~= 1.73 * radius.
    radius = float(np.linalg.norm([2.0, 2.0, 2.0])) / 2.0
    distance = float(np.linalg.norm(np.asarray(eye) - np.asarray(center)))
    assert distance > radius / np.tan(np.radians(30.0))


def test_thumbnail_camera_handles_a_degenerate_mesh() -> None:
    """A flat or single-point mesh has zero extent; the eye must not land on the center."""
    center, eye, _ = _thumbnail_camera(_Bounds([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]))

    assert float(np.linalg.norm(np.asarray(eye) - np.asarray(center))) > 0.0
