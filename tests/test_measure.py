import numpy as np
import pytest

from kinect_forge.measure import _bbox_extent


class _BBoxGetExtent:
    def get_extent(self):
        return [1.0, 2.0, 3.0]


class _BBoxExtentAttr:
    extent = [4.0, 5.0, 6.0]


class _BBoxBounds:
    def get_max_bound(self):
        return [3.0, 3.0, 3.0]

    def get_min_bound(self):
        return [1.0, 1.0, 1.0]


def test_bbox_extent_uses_get_extent():
    extent = _bbox_extent(_BBoxGetExtent())
    assert np.allclose(extent, [1.0, 2.0, 3.0])


def test_bbox_extent_uses_extent_attr():
    extent = _bbox_extent(_BBoxExtentAttr())
    assert np.allclose(extent, [4.0, 5.0, 6.0])


def test_bbox_extent_uses_bounds():
    extent = _bbox_extent(_BBoxBounds())
    assert np.allclose(extent, [2.0, 2.0, 2.0])


def test_bbox_extent_missing():
    with pytest.raises(AttributeError):
        _bbox_extent(object())


def test_measure_mesh_reports_box_dimensions_and_volume(tmp_path):
    import open3d as o3d

    from kinect_forge.measure import measure_mesh

    path = tmp_path / "box.ply"
    o3d.io.write_triangle_mesh(path, o3d.geometry.TriangleMesh.create_box(0.1, 0.2, 0.3))

    result = measure_mesh(path)

    assert result.axis_aligned == pytest.approx((0.1, 0.2, 0.3))
    assert sorted(result.oriented) == pytest.approx([0.1, 0.2, 0.3])
    assert result.volume == pytest.approx(0.006)


def test_measure_mesh_has_no_volume_for_an_open_surface(tmp_path):
    import open3d as o3d

    from kinect_forge.measure import measure_mesh

    box = o3d.geometry.TriangleMesh.create_box(0.1, 0.2, 0.3)
    box.triangles = o3d.utility.Vector3iVector(np.asarray(box.triangles)[2:])
    path = tmp_path / "open.ply"
    o3d.io.write_triangle_mesh(path, box)

    assert measure_mesh(path).volume is None
