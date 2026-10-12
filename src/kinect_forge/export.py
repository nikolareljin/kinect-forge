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
    if suffix == ".glb":
        _to_trimesh(mesh).export(str(path))
        return
    if suffix == ".gltf":
        # Embedded, so the .gltf is one self-contained file. Otherwise trimesh
        # writes its buffers as gltf_buffer_N.bin beside it, and two exports into
        # the same folder overwrite each other's geometry.
        _to_trimesh(mesh).export(str(path), embed_buffers=True)
        return
    if suffix == ".stl" and not mesh.has_triangle_normals():
        # Open3D refuses to write STL without facet normals ("Write STL failed:
        # compute normals first") and leaves an empty file behind. Work on a copy
        # so the caller's mesh is not changed.
        mesh = o3d.geometry.TriangleMesh(mesh)
        mesh.compute_triangle_normals()

    if not o3d.io.write_triangle_mesh(path, mesh):
        raise RuntimeError("Failed to write mesh output.")
