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


def test_a_malformed_calibration_file_is_not_reported_as_loaded(tmp_path, monkeypatch):
    """The status line has to agree with what capture actually loads.

    `_refresh_calib_status` used to test only that `calibration.json` existed. A
    file that was present but unreadable made the interface say "loaded" while
    `_find_default_calibration` quietly fell back to the Kinect v1 defaults --
    the GUI claiming one thing and the capture doing another.
    """
    from kinect_forge.capture import _find_default_calibration

    monkeypatch.chdir(tmp_path)
    (tmp_path / "calibration.json").write_text("{not json at all")

    assert _find_default_calibration() is None


def test_a_valid_calibration_file_is_loaded(tmp_path, monkeypatch):
    import json

    from kinect_forge.capture import _find_default_calibration
    from kinect_forge.config import KinectIntrinsics

    monkeypatch.chdir(tmp_path)
    (tmp_path / "calibration.json").write_text(json.dumps(KinectIntrinsics().to_dict()))

    assert _find_default_calibration() is not None


def test_no_calibration_file_is_not_an_error(tmp_path, monkeypatch):
    from kinect_forge.capture import _find_default_calibration

    monkeypatch.chdir(tmp_path)
    assert _find_default_calibration() is None
