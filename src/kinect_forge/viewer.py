from __future__ import annotations

from pathlib import Path

import open3d as o3d

from kinect_forge.dataset import list_frame_pairs, load_metadata


def view_mesh(mesh_path: Path) -> None:
    mesh = o3d.io.read_triangle_mesh(str(mesh_path))
    if mesh.is_empty():
        raise RuntimeError("Mesh is empty or could not be read.")
    mesh.compute_vertex_normals()
    o3d.visualization.draw_geometries([mesh])


def view_dataset(input_dir: Path, every: int = 10) -> None:
    meta = load_metadata(input_dir)
    pairs = list_frame_pairs(input_dir)
    if not pairs:
        raise RuntimeError("No frames found in the dataset.")

    intrinsic = o3d.camera.PinholeCameraIntrinsic(
        meta.intrinsics.width,
        meta.intrinsics.height,
        meta.intrinsics.fx,
        meta.intrinsics.fy,
        meta.intrinsics.cx,
        meta.intrinsics.cy,
    )

    pcds = []
    for idx, (color_path, depth_path) in enumerate(pairs):
        if every > 1 and idx % every != 0:
            continue
        color = o3d.io.read_image(str(color_path))
        depth = o3d.io.read_image(str(depth_path))
        rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(
            color,
            depth,
            depth_scale=meta.depth_scale,
            depth_trunc=meta.depth_trunc,
            convert_rgb_to_intensity=False,
        )
        pcd = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd, intrinsic)
        pcds.append(pcd)

    if not pcds:
        raise RuntimeError("No point clouds generated from dataset.")

    merged = pcds[0]
    for pcd in pcds[1:]:
        merged += pcd
    merged = merged.voxel_down_sample(0.01)
    merged.estimate_normals()
    o3d.visualization.draw_geometries([merged])
