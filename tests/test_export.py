import open3d as o3d
import pytest
import trimesh

from kinect_forge.export import write_mesh


def _box() -> o3d.geometry.TriangleMesh:
    mesh = o3d.geometry.TriangleMesh.create_box(width=0.1, height=0.2, depth=0.3)
    # TSDF extraction returns a mesh without triangle normals; match that.
    mesh.triangle_normals = o3d.utility.Vector3dVector()
    return mesh


def test_write_mesh_stl_without_normals(tmp_path):
    mesh = _box()
    assert not mesh.has_triangle_normals()
    out = tmp_path / "box.stl"

    write_mesh(out, mesh)

    loaded = trimesh.load(out)
    assert len(loaded.faces) == 12
    assert loaded.extents == pytest.approx([0.1, 0.2, 0.3])
    # The caller's mesh is left as it was.
    assert not mesh.has_triangle_normals()


def test_write_mesh_gltf_is_one_file(tmp_path):
    write_mesh(tmp_path / "a.gltf", _box())
    write_mesh(tmp_path / "b.gltf", _box())

    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.gltf", "b.gltf"]
    loaded = trimesh.load(tmp_path / "a.gltf", force="mesh")
    assert len(loaded.faces) == 12


@pytest.mark.parametrize("suffix", [".ply", ".obj", ".off", ".glb"])
def test_write_mesh_other_formats(tmp_path, suffix):
    out = tmp_path / f"box{suffix}"
    write_mesh(out, _box())
    assert out.stat().st_size > 0


def test_write_mesh_rejects_empty_mesh(tmp_path):
    with pytest.raises(RuntimeError, match="empty"):
        write_mesh(tmp_path / "x.stl", o3d.geometry.TriangleMesh())
