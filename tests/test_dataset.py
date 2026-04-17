import json

from kinect_forge.config import KinectIntrinsics
from kinect_forge.dataset import DatasetMeta, load_metadata, write_metadata


def test_dataset_meta_round_trips_capture_mode(tmp_path):
    meta = DatasetMeta(
        intrinsics=KinectIntrinsics(),
        depth_scale=1000.0,
        depth_trunc=3.0,
        capture_mode="turntable",
        depth_format="11bit",
    )

    write_metadata(tmp_path, meta)

    loaded = load_metadata(tmp_path)
    assert loaded.capture_mode == "turntable"
    assert loaded.depth_format == "11bit"


def test_dataset_meta_defaults_capture_mode_for_older_metadata(tmp_path):
    payload = {
        "intrinsics": KinectIntrinsics().to_dict(),
        "depth_scale": 1000.0,
        "depth_trunc": 3.0,
        "depth_format": "mm",
    }
    (tmp_path / "metadata.json").write_text(json.dumps(payload))

    loaded = load_metadata(tmp_path)
    assert loaded.capture_mode == "standard"
