from __future__ import annotations

import tempfile
import webbrowser
from pathlib import Path

import numpy as np
import open3d as o3d
import plotly.graph_objects as go

from kinect_forge.dataset import list_frame_pairs, load_metadata


def _open_figure(fig: go.Figure, title: str) -> Path:
    with tempfile.NamedTemporaryFile(
        prefix="kinect-forge-", suffix=".html", delete=False
    ) as handle:
        output = Path(handle.name)
    fig.update_layout(title=title)
    fig.write_html(str(output), include_plotlyjs=True, auto_open=False)
    webbrowser.open(output.as_uri())
    return output


def _sample_points(
    points: np.ndarray, colors: np.ndarray | None = None, max_points: int = 30000
) -> tuple[np.ndarray, np.ndarray | None]:
    if len(points) <= max_points:
        return points, colors
    step = max(1, len(points) // max_points)
    points = points[::step]
    if colors is not None:
        colors = colors[::step]
    return points, colors


def view_mesh(mesh_path: Path) -> Path:
    mesh = o3d.io.read_triangle_mesh(str(mesh_path))
    if mesh.is_empty():
        raise RuntimeError("Mesh is empty or could not be read.")
    vertices = np.asarray(mesh.vertices)
    triangles = np.asarray(mesh.triangles)
    if len(vertices) == 0 or len(triangles) == 0:
        raise RuntimeError("Mesh has no vertices or triangles.")

    fig = go.Figure(
        data=[
            go.Mesh3d(
                x=vertices[:, 0],
                y=vertices[:, 1],
                z=vertices[:, 2],
                i=triangles[:, 0],
                j=triangles[:, 1],
                k=triangles[:, 2],
                color="#6d8cff",
                flatshading=False,
                opacity=1.0,
            )
        ]
    )
    fig.update_layout(
        scene=dict(aspectmode="data"),
        margin=dict(l=0, r=0, b=0, t=40),
    )
    return _open_figure(fig, f"Kinect Forge Mesh: {mesh_path.name}")


def view_dataset(input_dir: Path, every: int = 10) -> Path:
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
    points = np.asarray(merged.points)
    if len(points) == 0:
        raise RuntimeError("Merged point cloud is empty.")
    colors = np.asarray(merged.colors) if merged.has_colors() else None
    points, colors = _sample_points(points, colors)

    marker: dict[str, object] = {"size": 2, "opacity": 0.9}
    if colors is not None and len(colors) == len(points):
        rgb = np.clip(colors * 255.0, 0, 255).astype(np.uint8)
        marker["color"] = [f"rgb({r},{g},{b})" for r, g, b in rgb]
    else:
        marker["color"] = points[:, 2]
        marker["colorscale"] = "Viridis"

    fig = go.Figure(
        data=[
            go.Scatter3d(
                x=points[:, 0],
                y=points[:, 1],
                z=points[:, 2],
                mode="markers",
                marker=marker,
            )
        ]
    )
    fig.update_layout(
        scene=dict(aspectmode="data"),
        margin=dict(l=0, r=0, b=0, t=40),
    )
    return _open_figure(fig, f"Kinect Forge Dataset: {input_dir.name}")
