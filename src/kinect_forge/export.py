from __future__ import annotations

from pathlib import Path

import numpy as np
import open3d as o3d
import trimesh


def _to_trimesh(mesh: o3d.geometry.TriangleMesh) -> trimesh.Trimesh:
    vertices = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.triangles)
    vertex_normals = None
    vertex_colors = None
    if mesh.has_vertex_normals():
        vertex_normals = np.asarray(mesh.vertex_normals)
    if mesh.has_vertex_colors():
        colors = np.asarray(mesh.vertex_colors)
        vertex_colors = (colors * 255).astype(np.uint8)
    return trimesh.Trimesh(
        vertices=vertices,
        faces=faces,
        vertex_normals=vertex_normals,
        vertex_colors=vertex_colors,
        process=False,
    )


def write_mesh(path: Path, mesh: o3d.geometry.TriangleMesh) -> None:
    if mesh.is_empty():
        raise RuntimeError("Mesh is empty or could not be generated.")
    suffix = path.suffix.lower()
    if suffix in {".glb", ".gltf"}:
        tm = _to_trimesh(mesh)
        tm.export(str(path))
        return

    if not o3d.io.write_triangle_mesh(str(path), mesh):
        raise RuntimeError("Failed to write mesh output.")
