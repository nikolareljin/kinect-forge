import numpy as np

from kinect_forge.reconstruct import _interpolate_rigid_transform, _loop_closure_residual


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


def test_loop_closure_residual_is_identity_for_perfect_loop():
    angle = np.pi / 6.0
    last_pose = np.array(
        [
            [np.cos(angle), -np.sin(angle), 0.0, 0.4],
            [np.sin(angle), np.cos(angle), 0.0, -0.2],
            [0.0, 0.0, 1.0, 0.1],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )

    residual = _loop_closure_residual(last_pose, np.linalg.inv(last_pose))
    assert np.allclose(residual, np.eye(4))


class _FakeIcpResult:
    def __init__(self, transformation):
        self.transformation = transformation


def _rot_y(angle):
    c, s = np.cos(angle), np.sin(angle)
    return np.array(
        [[c, 0.0, s, 0.0], [0.0, 1.0, 0.0, 0.0], [-s, 0.0, c, 0.0], [0.0, 0.0, 0.0, 1.0]]
    )


def _world_to_camera_track(count):
    """A drift-free world-to-camera track: poses[i] = T_ci<-c0."""
    track = []
    for i in range(count):
        pose = _rot_y(0.1 * i)
        pose[0, 3] = 0.05 * i
        track.append(pose)
    track[0] = np.eye(4)
    return track


def _stub_registration(monkeypatch, transformation_for):
    """Replace ICP with an oracle so only the surrounding pose algebra is tested."""
    import open3d as o3d

    from kinect_forge import reconstruct

    monkeypatch.setattr(reconstruct, "_rgbd_to_pcd", lambda rgbd, intrinsic, voxel: rgbd)

    def fake_icp(source, target, distance, init, estimation, criteria=None):
        return _FakeIcpResult(transformation_for(source, target))

    monkeypatch.setattr(o3d.pipelines.registration, "registration_icp", fake_icp)


def test_refine_poses_icp_returns_world_to_camera_poses(monkeypatch):
    """ICP returns T_target<-source, i.e. camera-to-world; poses must stay world-to-camera.

    Feeding the refinement a perfect ICP oracle must leave a drift-free track
    unchanged. Composing the ICP result in the wrong direction doubles the motion.
    """
    from kinect_forge.reconstruct import _refine_poses_icp

    poses = _world_to_camera_track(4)
    # source/target are frame indices; the true relative transform is T_prev<-cur.
    _stub_registration(
        monkeypatch,
        lambda source, target: poses[target] @ np.linalg.inv(poses[source]),
    )

    refined = _refine_poses_icp([0, 1, 2, 3], None, poses, 0.05, 0.005, 30)

    for got, want in zip(refined, poses, strict=True):
        assert np.allclose(got, want, atol=1e-9)


def test_estimate_turntable_poses_inverts_the_icp_result(monkeypatch):
    """ICP registers frame i onto frame 0, so its result is T_c0<-ci and must be inverted."""
    from kinect_forge.reconstruct import _estimate_turntable_poses

    poses = _world_to_camera_track(4)
    _stub_registration(
        monkeypatch,
        lambda source, target: np.linalg.inv(poses[source]),  # T_c0<-ci
    )

    estimated = _estimate_turntable_poses([0, 1, 2, 3], None, 0.05, 0.005, 30)

    for got, want in zip(estimated, poses, strict=True):
        assert np.allclose(got, want, atol=1e-9)
