from __future__ import annotations

import warnings
from pathlib import Path
from typing import Callable, List, Optional, Tuple, cast

import numpy as np
import open3d as o3d

from kinect_forge.config import ReconstructionConfig
from kinect_forge.dataset import list_frame_pairs, load_metadata
from kinect_forge.export import write_mesh


def _rgbd_from_paths(
    color_path: Path,
    depth_path: Path,
    depth_scale: float,
    depth_trunc: float,
) -> o3d.geometry.RGBDImage:
    color = o3d.io.read_image(str(color_path))
    depth = o3d.io.read_image(str(depth_path))
    return o3d.geometry.RGBDImage.create_from_color_and_depth(
        color,
        depth,
        depth_scale=depth_scale,
        depth_trunc=depth_trunc,
        convert_rgb_to_intensity=False,
    )


def _estimate_poses(
    rgbd_images: List[o3d.geometry.RGBDImage],
    intrinsic: o3d.camera.PinholeCameraIntrinsic,
) -> List[np.ndarray]:
    poses: List[np.ndarray] = [np.eye(4)]
    odom_jacobian = o3d.pipelines.odometry.RGBDOdometryJacobianFromHybridTerm()
    for idx in range(1, len(rgbd_images)):
        success, trans, _ = o3d.pipelines.odometry.compute_rgbd_odometry(
            rgbd_images[idx - 1],
            rgbd_images[idx],
            intrinsic,
            np.eye(4),
            odom_jacobian,
        )
        if not success:
            trans = np.eye(4)
        poses.append(trans @ poses[-1])
    return poses


def _select_keyframes(
    pairs: List[Tuple[Path, Path]],
    depth_scale: float,
    threshold: float,
) -> List[Tuple[Path, Path]]:
    if threshold <= 0:
        return pairs

    selected: List[Tuple[Path, Path]] = []
    last_depth: np.ndarray | None = None
    for color_path, depth_path in pairs:
        depth = o3d.io.read_image(str(depth_path))
        depth_arr = np.asarray(depth).astype(np.float32) / depth_scale
        if last_depth is None:
            selected.append((color_path, depth_path))
            last_depth = depth_arr
            continue
        delta = np.mean(np.abs(depth_arr - last_depth))
        if delta >= threshold:
            selected.append((color_path, depth_path))
            last_depth = depth_arr
    return selected


def _assert_depth_frames(pairs: List[Tuple[Path, Path]], depth_scale: float) -> None:
    sample = pairs[: min(5, len(pairs))]
    if not sample:
        return
    ratios: List[float] = []
    for _, depth_path in sample:
        depth = o3d.io.read_image(str(depth_path))
        depth_arr = np.asarray(depth).astype(np.float32) / depth_scale
        if depth_arr.size == 0:
            continue
        ratios.append(float(np.count_nonzero(depth_arr) / depth_arr.size))
    if ratios and max(ratios) < 0.01:
        raise RuntimeError(
            "Depth frames are mostly empty. Check capture depth_min/depth_max or disable "
            "background masking."
        )


def _rgbd_to_pcd(
    rgbd: o3d.geometry.RGBDImage,
    intrinsic: o3d.camera.PinholeCameraIntrinsic,
    voxel_size: float,
) -> o3d.geometry.PointCloud:
    pcd = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd, intrinsic)
    if voxel_size > 0:
        pcd = pcd.voxel_down_sample(voxel_size)
    pcd.estimate_normals()
    return pcd


def _refine_poses_icp(
    rgbd_images: List[o3d.geometry.RGBDImage],
    intrinsic: o3d.camera.PinholeCameraIntrinsic,
    poses: List[np.ndarray],
    icp_distance: float,
    icp_voxel: float,
    icp_iterations: int,
) -> List[np.ndarray]:
    refined: List[np.ndarray] = [poses[0]]
    pcd_prev = _rgbd_to_pcd(rgbd_images[0], intrinsic, icp_voxel)
    criteria = o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=icp_iterations)
    for idx in range(1, len(rgbd_images)):
        pcd = _rgbd_to_pcd(rgbd_images[idx], intrinsic, icp_voxel)
        initial = np.linalg.inv(poses[idx - 1]) @ poses[idx]
        result = o3d.pipelines.registration.registration_icp(
            pcd,
            pcd_prev,
            icp_distance,
            initial,
            o3d.pipelines.registration.TransformationEstimationPointToPlane(),
            criteria,
        )
        refined_pose = refined[-1] @ result.transformation
        refined.append(refined_pose)
        pcd_prev = pcd
    return refined


def _rotation_to_quaternion(rotation: np.ndarray) -> np.ndarray:
    trace = float(np.trace(rotation))
    if trace > 0.0:
        s = np.sqrt(trace + 1.0) * 2.0
        quat = np.array(
            [
                0.25 * s,
                (rotation[2, 1] - rotation[1, 2]) / s,
                (rotation[0, 2] - rotation[2, 0]) / s,
                (rotation[1, 0] - rotation[0, 1]) / s,
            ]
        )
    else:
        diag = np.diag(rotation)
        idx = int(np.argmax(diag))
        if idx == 0:
            s = np.sqrt(1.0 + rotation[0, 0] - rotation[1, 1] - rotation[2, 2]) * 2.0
            quat = np.array(
                [
                    (rotation[2, 1] - rotation[1, 2]) / s,
                    0.25 * s,
                    (rotation[0, 1] + rotation[1, 0]) / s,
                    (rotation[0, 2] + rotation[2, 0]) / s,
                ]
            )
        elif idx == 1:
            s = np.sqrt(1.0 + rotation[1, 1] - rotation[0, 0] - rotation[2, 2]) * 2.0
            quat = np.array(
                [
                    (rotation[0, 2] - rotation[2, 0]) / s,
                    (rotation[0, 1] + rotation[1, 0]) / s,
                    0.25 * s,
                    (rotation[1, 2] + rotation[2, 1]) / s,
                ]
            )
        else:
            s = np.sqrt(1.0 + rotation[2, 2] - rotation[0, 0] - rotation[1, 1]) * 2.0
            quat = np.array(
                [
                    (rotation[1, 0] - rotation[0, 1]) / s,
                    (rotation[0, 2] + rotation[2, 0]) / s,
                    (rotation[1, 2] + rotation[2, 1]) / s,
                    0.25 * s,
                ]
            )
    quat /= np.linalg.norm(quat)
    if quat[0] < 0.0:
        quat *= -1.0
    return quat


def _quaternion_to_rotation(quat: np.ndarray) -> np.ndarray:
    w, x, y, z = quat / np.linalg.norm(quat)
    return np.array(
        [
            [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
            [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
            [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)],
        ]
    )


def _rotation_power(rotation: np.ndarray, alpha: float) -> np.ndarray:
    quat = _rotation_to_quaternion(rotation)
    angle = 2.0 * np.arccos(np.clip(quat[0], -1.0, 1.0))
    sin_half = np.linalg.norm(quat[1:])
    if np.isclose(sin_half, 0.0) or np.isclose(angle, 0.0):
        return np.eye(3)

    axis = quat[1:] / sin_half
    scaled_half = alpha * angle * 0.5
    scaled_quat = np.concatenate(([np.cos(scaled_half)], axis * np.sin(scaled_half)))
    return _quaternion_to_rotation(scaled_quat)


def _interpolate_rigid_transform(transform: np.ndarray, alpha: float) -> np.ndarray:
    correction = np.eye(4)
    correction[:3, :3] = _rotation_power(transform[:3, :3], alpha)
    correction[:3, 3] = transform[:3, 3] * alpha
    return correction


def _loop_closure_residual(last_pose: np.ndarray, last_to_first: np.ndarray) -> np.ndarray:
    return cast(np.ndarray, last_pose @ last_to_first)


def _apply_loop_closure(
    poses: List[np.ndarray],
    rgbd_images: List[o3d.geometry.RGBDImage],
    intrinsic: o3d.camera.PinholeCameraIntrinsic,
    icp_distance: float,
    icp_voxel: float,
    icp_iterations: int,
) -> List[np.ndarray]:
    """Distribute loop closure error linearly across all poses.

    Aligns the last frame back to the first frame via ICP to measure accumulated
    drift, then spreads the correction evenly across every intermediate pose.
    Applies only when at least 4 frames are present.
    """
    n = len(poses)
    if n < 4:
        return poses

    pcd_first = _rgbd_to_pcd(rgbd_images[0], intrinsic, icp_voxel)
    pcd_last = _rgbd_to_pcd(rgbd_images[-1], intrinsic, icp_voxel)
    criteria = o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=icp_iterations)
    result = o3d.pipelines.registration.registration_icp(
        pcd_last,
        pcd_first,
        icp_distance,
        np.linalg.inv(poses[-1]),
        o3d.pipelines.registration.TransformationEstimationPointToPlane(),
        criteria,
    )
    # A perfect loop satisfies poses[-1] @ (last -> first) == I.
    loop_error = _loop_closure_residual(poses[-1], result.transformation)
    inv_error = np.linalg.inv(loop_error)

    corrected: List[np.ndarray] = []
    for i, pose in enumerate(poses):
        alpha = i / (n - 1)
        corrected.append(_interpolate_rigid_transform(inv_error, alpha) @ pose)
    return corrected


def _estimate_turntable_poses(
    rgbd_images: List[o3d.geometry.RGBDImage],
    intrinsic: o3d.camera.PinholeCameraIntrinsic,
    icp_distance: float,
    icp_voxel: float,
    icp_iterations: int,
) -> List[np.ndarray]:
    """Estimate poses for a turntable dataset using rotation-prior ICP.

    Each frame is registered against frame 0 using a Y-axis rotation initial
    guess computed from the frame index. This avoids drift from sequential
    odometry and handles the known-axis rotation of a turntable.
    """
    n = len(rgbd_images)
    poses: List[np.ndarray] = [np.eye(4)]
    pcd_ref = _rgbd_to_pcd(rgbd_images[0], intrinsic, icp_voxel)
    criteria = o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=icp_iterations)
    for i in range(1, n):
        angle = 2.0 * np.pi * i / n
        c, s = float(np.cos(angle)), float(np.sin(angle))
        initial = np.array(
            [
                [c, 0.0, s, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [-s, 0.0, c, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ]
        )
        pcd = _rgbd_to_pcd(rgbd_images[i], intrinsic, icp_voxel)
        result = o3d.pipelines.registration.registration_icp(
            pcd,
            pcd_ref,
            icp_distance,
            initial,
            o3d.pipelines.registration.TransformationEstimationPointToPlane(),
            criteria,
        )
        poses.append(result.transformation)
    return poses


def _clean_mesh(
    mesh: o3d.geometry.TriangleMesh, config: ReconstructionConfig
) -> o3d.geometry.TriangleMesh:
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()
    mesh.remove_unreferenced_vertices()
    if config.smooth_iterations > 0:
        mesh = mesh.filter_smooth_taubin(number_of_iterations=config.smooth_iterations)
    if config.fill_hole_radius > 0 and hasattr(mesh, "fill_holes"):
        mesh = mesh.fill_holes(config.fill_hole_radius)
    mesh.compute_vertex_normals()
    return mesh


def reconstruct_mesh(
    input_dir: Path,
    output_mesh: Path,
    config: ReconstructionConfig,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    meta = load_metadata(input_dir)
    pairs = list_frame_pairs(input_dir)
    if not pairs:
        raise RuntimeError("No frames found in the dataset.")

    depth_scale = config.depth_scale if config.depth_scale > 0 else meta.depth_scale
    depth_trunc = config.depth_trunc if config.depth_trunc > 0 else meta.depth_trunc

    if meta.depth_format == "11bit" and depth_scale >= 999.0:
        warnings.warn(
            "Dataset captured with DEPTH_11BIT but depth_scale=1000.0. "
            "Metric scale will be incorrect. Recapture using DEPTH_MM (default).",
            stacklevel=2,
        )

    pairs = _select_keyframes(pairs, depth_scale, config.keyframe_threshold)
    if not pairs:
        raise RuntimeError("Keyframe selection removed all frames.")
    _assert_depth_frames(pairs, depth_scale)

    intrinsic = o3d.camera.PinholeCameraIntrinsic(
        meta.intrinsics.width,
        meta.intrinsics.height,
        meta.intrinsics.fx,
        meta.intrinsics.fy,
        meta.intrinsics.cx,
        meta.intrinsics.cy,
    )

    rgbd_images = [
        _rgbd_from_paths(color, depth, depth_scale, depth_trunc) for color, depth in pairs
    ]

    if meta.capture_mode == "turntable":
        poses = _estimate_turntable_poses(
            rgbd_images,
            intrinsic,
            config.icp_distance,
            config.icp_voxel,
            config.icp_iterations,
        )
    else:
        poses = _estimate_poses(rgbd_images, intrinsic)
        if config.loop_closure and len(rgbd_images) >= 4:
            poses = _apply_loop_closure(
                poses,
                rgbd_images,
                intrinsic,
                config.icp_distance,
                config.icp_voxel,
                config.icp_iterations,
            )
        if config.icp_refine and len(rgbd_images) > 1:
            poses = _refine_poses_icp(
                rgbd_images,
                intrinsic,
                poses,
                config.icp_distance,
                config.icp_voxel,
                config.icp_iterations,
            )

    volume = o3d.pipelines.integration.ScalableTSDFVolume(
        voxel_length=config.voxel_length,
        sdf_trunc=config.sdf_trunc,
        color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8,
    )

    total_frames = len(rgbd_images)
    for idx, (rgbd, pose) in enumerate(zip(rgbd_images, poses)):
        volume.integrate(rgbd, intrinsic, np.linalg.inv(pose))
        if progress_callback is not None:
            progress_callback(idx + 1, total_frames)

    mesh = volume.extract_triangle_mesh()
    mesh = _clean_mesh(mesh, config)
    if mesh.is_empty():
        raise RuntimeError("Reconstruction produced an empty mesh.")

    output_mesh.parent.mkdir(parents=True, exist_ok=True)
    write_mesh(output_mesh, mesh)
