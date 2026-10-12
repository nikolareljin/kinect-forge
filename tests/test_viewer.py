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


def test_mesh_figure_uses_vertex_colours() -> None:
    import open3d as o3d

    from kinect_forge.viewer import _mesh_figure

    mesh = o3d.geometry.TriangleMesh.create_box()
    mesh.paint_uniform_color([1.0, 0.5, 0.0])

    trace = _mesh_figure(mesh).data[0]

    assert trace.color is None
    assert len(trace.vertexcolor) == len(mesh.vertices)
    assert trace.vertexcolor[0] == "rgb(255,127,0)"


def test_mesh_figure_without_colours_and_views_from_the_sensor() -> None:
    import open3d as o3d

    from kinect_forge.viewer import _mesh_figure

    fig = _mesh_figure(o3d.geometry.TriangleMesh.create_box())

    assert fig.data[0].color == "#6d8cff"
    camera = fig.layout.scene.camera
    assert (camera.up.x, camera.up.y, camera.up.z) == (0, -1, 0)
    assert camera.eye.z < 0
