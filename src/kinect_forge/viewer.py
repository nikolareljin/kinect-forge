from __future__ import annotations

import logging
import tempfile
import webbrowser
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import open3d as o3d
import plotly.graph_objects as go

from kinect_forge.dataset import list_frame_pairs, load_metadata

_LOG = logging.getLogger(__name__)

_THUMBNAIL_WIDTH = 400
_THUMBNAIL_HEIGHT = 300


def _thumbnail_camera(
    bounds: Any,
) -> tuple[npt.NDArray[Any], npt.NDArray[Any], npt.NDArray[Any]]:
    """Return (center, eye, up) framing `bounds` for a 60 degree vertical FOV.

    Open3D's camera looks down +Z with +Y pointing down, so `up` is -Y and the eye
    sits on -Z. A 60 degree FOV needs a distance of at least radius / tan(30 degrees)
    ~= 1.73 * radius to fit the bounding sphere; 2.5 leaves a margin.
    """
    center = np.asarray(bounds.get_center(), dtype=np.float32)
    radius = float(np.linalg.norm(np.asarray(bounds.get_extent(), dtype=np.float64))) / 2.0
    if radius <= 0.0:
        radius = 1.0
    offset = np.array([radius * 1.2, -radius * 1.2, -radius * 2.5], dtype=np.float32)
    up = np.array([0.0, -1.0, 0.0], dtype=np.float32)
    return center, center + offset, up


# Scans are in the Kinect camera frame: x right, y down, z away from the sensor.
# Plotly puts +z up by default, which shows a face lying on its back. Look from
# the sensor instead (eye on -z, -y up) so the first view matches what the camera saw.
_SCENE_LAYOUT: dict[str, Any] = {
    "aspectmode": "data",
    "camera": {"up": {"x": 0, "y": -1, "z": 0}, "eye": {"x": 0, "y": 0, "z": -2}},
}


def _rgb_strings(colors: npt.NDArray[Any]) -> list[str]:
    rgb = np.clip(colors * 255.0, 0, 255).astype(np.uint8)
    return [f"rgb({r},{g},{b})" for r, g, b in rgb]


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
    points: npt.NDArray[Any], colors: npt.NDArray[Any] | None = None, max_points: int = 30000
) -> tuple[npt.NDArray[Any], npt.NDArray[Any] | None]:
    if len(points) <= max_points:
        return points, colors
    step = max(1, len(points) // max_points)
    points = points[::step]
    if colors is not None:
        colors = colors[::step]
    return points, colors


def _mesh_figure(mesh: o3d.geometry.TriangleMesh) -> go.Figure:
    vertices = np.asarray(mesh.vertices)
    triangles = np.asarray(mesh.triangles)
    if len(vertices) == 0 or len(triangles) == 0:
        raise RuntimeError("Mesh has no vertices or triangles.")

    # Show the scanned colour when the mesh has it, so a colour/depth misalignment
    # is visible; a flat fill hides it.
    shading: dict[str, Any] = {"color": "#6d8cff"}
    if mesh.has_vertex_colors():
        shading = {"vertexcolor": _rgb_strings(np.asarray(mesh.vertex_colors))}

    fig = go.Figure(
        data=[
            go.Mesh3d(
                x=vertices[:, 0],
                y=vertices[:, 1],
                z=vertices[:, 2],
                i=triangles[:, 0],
                j=triangles[:, 1],
                k=triangles[:, 2],
                flatshading=False,
                opacity=1.0,
                **shading,
            )
        ]
    )
    fig.update_layout(scene=_SCENE_LAYOUT, margin={"l": 0, "r": 0, "b": 0, "t": 40})
    return fig


def view_mesh(mesh_path: Path) -> Path:
    mesh = o3d.io.read_triangle_mesh(mesh_path)
    if mesh.is_empty():
        raise RuntimeError("Mesh is empty or could not be read.")
    return _open_figure(_mesh_figure(mesh), f"Kinect Forge Mesh: {mesh_path.name}")


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
        color = o3d.io.read_image(color_path)
        depth = o3d.io.read_image(depth_path)
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
        marker["color"] = _rgb_strings(colors)
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
    fig.update_layout(scene=_SCENE_LAYOUT, margin={"l": 0, "r": 0, "b": 0, "t": 40})
    return _open_figure(fig, f"Kinect Forge Dataset: {input_dir.name}")


def render_mesh_thumbnail(mesh_path: Path) -> bytes | None:
    """Render a PNG thumbnail of the mesh using Open3D offscreen rendering.

    Returns raw PNG bytes, or None when offscreen rendering is unavailable
    (headless session, no GPU/EGL) or the mesh is empty. Anything else is a
    defect and propagates rather than silently producing no thumbnail.
    """
    mesh = o3d.io.read_triangle_mesh(mesh_path)
    if mesh.is_empty():
        return None
    mesh.compute_vertex_normals()

    try:
        renderer = o3d.visualization.rendering.OffscreenRenderer(
            _THUMBNAIL_WIDTH, _THUMBNAIL_HEIGHT
        )
    except Exception as exc:  # pragma: no cover - depends on GPU/EGL availability
        _LOG.warning("Offscreen rendering unavailable, skipping thumbnail: %s", exc)
        return None

    mat = o3d.visualization.rendering.MaterialRecord()
    mat.shader = "defaultLit"
    renderer.scene.add_geometry("mesh", mesh, mat)
    renderer.setup_camera(60.0, *_thumbnail_camera(mesh.get_axis_aligned_bounding_box()))
    img = renderer.render_to_image()

    # Open3D has no write-image-to-memory binding; round-trip through a temp file.
    with tempfile.TemporaryDirectory(prefix="kinect-forge-thumb-") as tmp:
        png_path = Path(tmp) / "thumbnail.png"
        if not o3d.io.write_image(png_path, img):
            _LOG.warning("Open3D could not encode the thumbnail PNG")
            return None
        return png_path.read_bytes()
