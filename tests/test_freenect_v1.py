import json
import sys
import types

import numpy as np
import pytest

from kinect_forge.capture import capture_frames
from kinect_forge.config import CaptureConfig
from kinect_forge.sensors.freenect_v1 import FreenectV1Config, FreenectV1Sensor


def _fake_freenect(registered: bool) -> types.SimpleNamespace:
    calls: list[int] = []
    mod = types.SimpleNamespace(VIDEO_RGB=0, DEPTH_11BIT=1, DEPTH_MM=5, calls=calls)
    if registered:
        mod.DEPTH_REGISTERED = 4

    def sync_get_video(format: int) -> tuple[np.ndarray, int]:
        return np.zeros((4, 4, 3), dtype=np.uint8), 0

    def sync_get_depth(format: int) -> tuple[np.ndarray, int]:
        calls.append(format)
        return np.full((4, 4), 500, dtype=np.uint16), 0

    mod.sync_get_video = sync_get_video
    mod.sync_get_depth = sync_get_depth
    return mod


@pytest.mark.parametrize(
    ("has_registered", "config", "expected_format", "expected_flag"),
    [
        (True, FreenectV1Config(), 4, True),
        (True, FreenectV1Config(depth_registration=False), 5, False),
        (True, FreenectV1Config(depth_format="11bit"), 1, False),
        (False, FreenectV1Config(), 5, False),
    ],
)
def test_depth_format_follows_registration_setting(
    monkeypatch, has_registered, config, expected_format, expected_flag
):
    fake = _fake_freenect(has_registered)
    monkeypatch.setitem(sys.modules, "freenect", fake)

    sensor = FreenectV1Sensor(config)
    sensor.get_frame()

    assert fake.calls == [expected_format]
    assert sensor.depth_registered is expected_flag


def test_capture_records_whether_depth_was_registered(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "freenect", _fake_freenect(True))
    sensor = FreenectV1Sensor()

    capture_frames(sensor, tmp_path, CaptureConfig(frames=1, fps=0, warmup=0))

    assert json.loads((tmp_path / "metadata.json").read_text())["depth_registered"] is True
