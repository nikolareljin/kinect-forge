from __future__ import annotations

from kinect_forge.config import ReconstructionConfig


def reconstruction_preset(name: str) -> ReconstructionConfig:
    preset = name.lower()
    if preset == "small":
        return ReconstructionConfig(
            voxel_length=0.003,
            sdf_trunc=0.03,
            depth_trunc=2.0,
            keyframe_threshold=0.003,
            icp_refine=True,
            icp_distance=0.015,
            icp_voxel=0.008,
            icp_iterations=40,
            smooth_iterations=5,
            fill_hole_radius=0.008,
            preset="small",
        )
    if preset == "medium":
        return ReconstructionConfig(
            voxel_length=0.006,
            sdf_trunc=0.05,
            depth_trunc=3.0,
            keyframe_threshold=0.005,
            icp_refine=True,
            icp_distance=0.025,
            icp_voxel=0.012,
            icp_iterations=30,
            smooth_iterations=3,
            fill_hole_radius=0.01,
            preset="medium",
        )
    if preset == "large":
        return ReconstructionConfig(
            voxel_length=0.01,
            sdf_trunc=0.08,
            depth_trunc=4.0,
            keyframe_threshold=0.008,
            icp_refine=False,
            icp_distance=0.03,
            icp_voxel=0.02,
            icp_iterations=20,
            smooth_iterations=0,
            fill_hole_radius=0.0,
            preset="large",
        )
    if preset == "small-object":
        return ReconstructionConfig(
            voxel_length=0.0025,
            sdf_trunc=0.02,
            depth_trunc=1.5,
            keyframe_threshold=0.002,
            icp_refine=True,
            icp_distance=0.01,
            icp_voxel=0.006,
            icp_iterations=50,
            smooth_iterations=6,
            fill_hole_radius=0.006,
            preset="small-object",
        )
    if preset == "face-scan":
        return ReconstructionConfig(
            voxel_length=0.003,
            sdf_trunc=0.025,
            depth_trunc=1.5,
            keyframe_threshold=0.003,
            icp_refine=True,
            icp_distance=0.012,
            icp_voxel=0.007,
            icp_iterations=45,
            smooth_iterations=4,
            fill_hole_radius=0.01,
            preset="face-scan",
        )
    raise ValueError("preset must be small, medium, large, small-object, or face-scan")
