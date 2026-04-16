import numpy as np
import pytest

pytest.importorskip("open3d")

from kinect_forge.reconstruct import _interpolate_rigid_transform


def test_interpolate_rigid_transform_preserves_rigid_rotation():
    angle = np.pi / 2.0
    transform = np.array(
        [
            [np.cos(angle), 0.0, np.sin(angle), 1.0],
            [0.0, 1.0, 0.0, 2.0],
            [-np.sin(angle), 0.0, np.cos(angle), 3.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )

    halfway = _interpolate_rigid_transform(transform, 0.5)

    assert np.allclose(halfway[:3, 3], [0.5, 1.0, 1.5])
    assert np.allclose(halfway[:3, :3].T @ halfway[:3, :3], np.eye(3), atol=1e-6)
    assert np.isclose(np.linalg.det(halfway[:3, :3]), 1.0, atol=1e-6)


def test_interpolate_rigid_transform_keeps_endpoints():
    angle = np.pi / 3.0
    transform = np.array(
        [
            [np.cos(angle), -np.sin(angle), 0.0, 4.0],
            [np.sin(angle), np.cos(angle), 0.0, 5.0],
            [0.0, 0.0, 1.0, 6.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )

    assert np.allclose(_interpolate_rigid_transform(transform, 0.0), np.eye(4))
    assert np.allclose(_interpolate_rigid_transform(transform, 1.0), transform)
