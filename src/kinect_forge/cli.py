from __future__ import annotations

import json
import pathlib
from typing import List, Optional

import typer
from rich.console import Console

from kinect_forge.calibration import calibrate_intrinsics, save_intrinsics
from kinect_forge.capture import capture_frames
from kinect_forge.config import CaptureConfig, ReconstructionConfig
from kinect_forge.config import KinectIntrinsics
from kinect_forge.measure import measure_mesh
from kinect_forge.presets import reconstruction_preset
from kinect_forge.reconstruct import reconstruct_mesh
from kinect_forge.sensors.freenect_v1 import FreenectV1Sensor, probe_device
from kinect_forge.viewer import view_dataset, view_mesh

app = typer.Typer(add_completion=False)
console = Console()


@app.command()
def status() -> None:
    """Show current configuration and backend status."""
    backend_ok = probe_device()
    if backend_ok:
        console.print("Kinect v1 backend detected and streaming.")
    else:
        console.print(
            "Kinect v1 backend not detected. Ensure libfreenect and python3-freenect "
            "are installed and the device is connected."
        )


@app.command()
def capture(
    output: pathlib.Path = typer.Option("captures", help="Output directory"),
    frames: int = typer.Option(300, help="Number of RGB-D frames to capture"),
    fps: float = typer.Option(30.0, help="Target capture FPS"),
    warmup: int = typer.Option(15, help="Warmup frames before recording"),
    mode: str = typer.Option("standard", help="Capture mode: standard|turntable"),
    change_threshold: float = typer.Option(
        0.01, help="Turntable depth change threshold (meters)"
    ),
    max_frames_total: int = typer.Option(
        3000, help="Hard stop for total frames read in turntable mode"
    ),
    depth_min: float = typer.Option(0.3, help="Minimum depth in meters"),
    depth_max: float = typer.Option(2.5, help="Maximum depth in meters"),
    mask_background: bool = typer.Option(True, help="Zero out background pixels"),
    intrinsics_path: Optional[pathlib.Path] = typer.Option(
        None, help="Optional intrinsics JSON from calibrate"
    ),
) -> None:
    """Capture RGB-D frames using Kinect v1 (libfreenect)."""
    sensor = FreenectV1Sensor()
    config = CaptureConfig(
        frames=frames,
        fps=fps,
        warmup=warmup,
        mode=mode.lower(),
        change_threshold=change_threshold,
        max_frames_total=max_frames_total,
        depth_min=depth_min,
        depth_max=depth_max,
        mask_background=mask_background,
    )
    intrinsics = None
    if intrinsics_path is not None:
        payload = json.loads(intrinsics_path.read_text())
        intrinsics = KinectIntrinsics.from_dict(payload)
    capture_frames(sensor, output, config, intrinsics=intrinsics)
    console.print(f"Capture complete: {frames} frames saved to {output}")


@app.command()
def reconstruct(
    input_dir: pathlib.Path = typer.Option(..., help="Directory with captured frames"),
    output_mesh: pathlib.Path = typer.Option("model.ply", help="Output mesh file"),
    preset: str = typer.Option("small", help="Reconstruction preset: small|medium|large"),
    voxel_length: Optional[float] = typer.Option(None, help="TSDF voxel size in meters"),
    sdf_trunc: Optional[float] = typer.Option(None, help="TSDF truncation distance in meters"),
    depth_scale: Optional[float] = typer.Option(None, help="Depth scale (mm -> meters)"),
    depth_trunc: Optional[float] = typer.Option(None, help="Max depth in meters"),
    keyframe_threshold: Optional[float] = typer.Option(
        None, help="Depth change threshold for keyframe selection (meters)"
    ),
    icp: Optional[bool] = typer.Option(
        None, "--icp/--no-icp", help="Enable/disable ICP refinement"
    ),
    icp_distance: Optional[float] = typer.Option(
        None, help="ICP max correspondence distance"
    ),
    icp_voxel: Optional[float] = typer.Option(None, help="ICP voxel downsample size"),
    icp_iterations: Optional[int] = typer.Option(None, help="ICP max iterations"),
    smooth: Optional[int] = typer.Option(None, help="Mesh smoothing iterations"),
    fill_hole_radius: Optional[float] = typer.Option(
        None, help="Fill holes radius (meters)"
    ),
) -> None:
    """Reconstruct a mesh from captured frames."""
    config = reconstruction_preset(preset)
    keyframe_threshold = (
        config.keyframe_threshold if keyframe_threshold is None else keyframe_threshold
    )
    config = ReconstructionConfig(
        voxel_length=config.voxel_length if voxel_length is None else voxel_length,
        sdf_trunc=config.sdf_trunc if sdf_trunc is None else sdf_trunc,
        depth_scale=config.depth_scale if depth_scale is None else depth_scale,
        depth_trunc=config.depth_trunc if depth_trunc is None else depth_trunc,
        keyframe_threshold=keyframe_threshold,
        icp_refine=config.icp_refine if icp is None else icp,
        icp_distance=config.icp_distance if icp_distance is None else icp_distance,
        icp_voxel=config.icp_voxel if icp_voxel is None else icp_voxel,
        icp_iterations=config.icp_iterations if icp_iterations is None else icp_iterations,
        smooth_iterations=config.smooth_iterations if smooth is None else smooth,
        fill_hole_radius=config.fill_hole_radius
        if fill_hole_radius is None
        else fill_hole_radius,
        preset=config.preset,
    )
    reconstruct_mesh(input_dir, output_mesh, config)
    console.print(f"Mesh written to {output_mesh}")


@app.command()
def measure(
    mesh: pathlib.Path = typer.Option(..., help="Mesh to analyze"),
) -> None:
    """Measure dimensions from a mesh."""
    measurements = measure_mesh(mesh)
    console.print(
        "Axis-aligned dimensions (m): "
        f"{measurements.axis_aligned[0]:.4f}, "
        f"{measurements.axis_aligned[1]:.4f}, "
        f"{measurements.axis_aligned[2]:.4f}"
    )
    console.print(
        "Oriented dimensions (m): "
        f"{measurements.oriented[0]:.4f}, "
        f"{measurements.oriented[1]:.4f}, "
        f"{measurements.oriented[2]:.4f}"
    )
    if measurements.volume is not None:
        console.print(f"Volume (m^3): {measurements.volume:.6f}")


@app.command()
def calibrate(
    images: List[pathlib.Path] = typer.Option(
        ..., help="Calibration images (space-separated list)"
    ),
    rows: int = typer.Option(7, help="Chessboard inner corners rows"),
    cols: int = typer.Option(9, help="Chessboard inner corners cols"),
    square_size: float = typer.Option(0.025, help="Square size in meters"),
    output: pathlib.Path = typer.Option("intrinsics.json", help="Output JSON"),
) -> None:
    """Calibrate camera intrinsics from chessboard images."""
    intrinsics = calibrate_intrinsics(images, (cols, rows), square_size)
    save_intrinsics(output, intrinsics)
    console.print(f"Intrinsics saved to {output}")


@app.command()
def view(
    mesh: Optional[pathlib.Path] = typer.Option(None, help="Mesh to view"),
    dataset: Optional[pathlib.Path] = typer.Option(None, help="Dataset to preview"),
    every: int = typer.Option(10, help="Use every Nth frame for dataset preview"),
) -> None:
    """Preview a mesh or a dataset point cloud."""
    if mesh is None and dataset is None:
        raise typer.BadParameter("Provide --mesh or --dataset")
    if mesh is not None:
        view_mesh(mesh)
    if dataset is not None:
        view_dataset(dataset, every=every)


if __name__ == "__main__":
    app()
