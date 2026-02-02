from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

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
    criteria = o3d.pipelines.registration.ICPConvergenceCriteria(
        max_iteration=icp_iterations
    )
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


def _clean_mesh(mesh: o3d.geometry.TriangleMesh, config: ReconstructionConfig) -> o3d.geometry.TriangleMesh:
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


def reconstruct_mesh(input_dir: Path, output_mesh: Path, config: ReconstructionConfig) -> None:
    meta = load_metadata(input_dir)
    pairs = list_frame_pairs(input_dir)
    if not pairs:
        raise RuntimeError("No frames found in the dataset.")

    depth_scale = config.depth_scale if config.depth_scale > 0 else meta.depth_scale
    depth_trunc = config.depth_trunc if config.depth_trunc > 0 else meta.depth_trunc
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
        _rgbd_from_paths(color, depth, depth_scale, depth_trunc)
        for color, depth in pairs
    ]

    poses = _estimate_poses(rgbd_images, intrinsic)
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

    for rgbd, pose in zip(rgbd_images, poses):
        volume.integrate(rgbd, intrinsic, np.linalg.inv(pose))

    mesh = volume.extract_triangle_mesh()
    mesh = _clean_mesh(mesh, config)
    if mesh.is_empty():
        raise RuntimeError("Reconstruction produced an empty mesh.")

    output_mesh.parent.mkdir(parents=True, exist_ok=True)
    write_mesh(output_mesh, mesh)
