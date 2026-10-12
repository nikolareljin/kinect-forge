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


def test_capture_cli_warns_when_registration_is_unavailable(monkeypatch, tmp_path):
    from typer.testing import CliRunner

    from kinect_forge import cli

    monkeypatch.setitem(sys.modules, "freenect", _fake_freenect(False))
    monkeypatch.setattr(cli, "capture_frames", lambda *args, **kwargs: None)

    result = CliRunner().invoke(cli.app, ["capture", "--output", str(tmp_path / "scan")])

    assert result.exit_code == 0, result.output
    assert "DEPTH_REGISTERED" in result.output


def test_capture_cli_is_quiet_when_registration_works(monkeypatch, tmp_path):
    from typer.testing import CliRunner

    from kinect_forge import cli

    monkeypatch.setitem(sys.modules, "freenect", _fake_freenect(True))
    monkeypatch.setattr(cli, "capture_frames", lambda *args, **kwargs: None)

    result = CliRunner().invoke(cli.app, ["capture", "--output", str(tmp_path / "scan")])

    assert result.exit_code == 0, result.output
    assert "DEPTH_REGISTERED" not in result.output


class _FakeSyncLib:
    """Stands in for libfreenect_sync loaded through ctypes."""

    def __init__(self, accel: tuple[int, int, int], set_rc: int = 0) -> None:
        self.accel = accel
        self.set_rc = set_rc
        self.angles: list[int] = []
        self._state = None

    def freenect_sync_set_tilt_degs(self, angle: int, index: int) -> int:
        self.angles.append(angle)
        return self.set_rc

    def freenect_sync_get_tilt_state(self, state_ref, index: int) -> int:
        from kinect_forge.sensors import freenect_v1

        self._state = freenect_v1._RawTiltState(*self.accel, 0, 0)
        state_ref._obj.contents = self._state
        return 0


def _tilt_setup(monkeypatch, lib: _FakeSyncLib) -> types.SimpleNamespace:
    from kinect_forge.sensors import freenect_v1

    fake = _fake_freenect(True)
    fake.sync_stop = lambda: fake.calls.append("stop")
    monkeypatch.setitem(sys.modules, "freenect", fake)
    monkeypatch.setattr(freenect_v1, "_sync_library", lambda: lib)
    return fake


def test_set_tilt_uses_sync_api_and_sees_a_working_motor(monkeypatch):
    from kinect_forge.sensors.freenect_v1 import set_tilt_degs

    lib = _FakeSyncLib(accel=(0, -819, 12))
    _tilt_setup(monkeypatch, lib)

    assert set_tilt_degs(9.6) is True
    assert lib.angles == [10]


def test_set_tilt_reports_a_motor_with_no_accelerometer_data(monkeypatch):
    from kinect_forge.sensors.freenect_v1 import set_tilt_degs

    _tilt_setup(monkeypatch, _FakeSyncLib(accel=(0, 0, 0)))

    assert set_tilt_degs(5) is False


def test_set_tilt_raises_when_libfreenect_fails(monkeypatch):
    from kinect_forge.sensors.freenect_v1 import set_tilt_degs

    _tilt_setup(monkeypatch, _FakeSyncLib(accel=(0, -819, 0), set_rc=-1))

    with pytest.raises(RuntimeError, match="Failed to set tilt"):
        set_tilt_degs(5)


def test_tilt_cli_fails_when_motor_does_not_respond(monkeypatch):
    from typer.testing import CliRunner

    from kinect_forge import cli

    fake = _tilt_setup(monkeypatch, _FakeSyncLib(accel=(0, 0, 0)))

    result = CliRunner().invoke(cli.app, ["tilt", "--angle", "5"])

    assert result.exit_code == 1
    assert "tilt motor is most likely not responding" in " ".join(result.output.split())
    assert "Tilt set to" not in result.output
    assert fake.calls[-1] == "stop"


def test_capture_cli_applies_preset_tilt_sweep(monkeypatch, tmp_path):
    from typer.testing import CliRunner

    from kinect_forge import cli

    _tilt_setup(monkeypatch, _FakeSyncLib(accel=(0, -819, 0)))
    seen = {}

    def fake_capture(sensor, output, config, **kwargs):
        seen["config"] = config
        seen["tilt_cb"] = kwargs.get("tilt_cb")

    monkeypatch.setattr(cli, "capture_frames", fake_capture)

    result = CliRunner().invoke(
        cli.app,
        ["capture", "--output", str(tmp_path / "scan"), "--capture-preset", "face-scan"],
    )

    assert result.exit_code == 0, result.output
    assert seen["config"].tilt_sweep is True
    assert seen["tilt_cb"] is not None


def test_capture_cli_flags_win_over_the_preset(monkeypatch, tmp_path):
    from typer.testing import CliRunner

    from kinect_forge import cli

    _tilt_setup(monkeypatch, _FakeSyncLib(accel=(0, -819, 0)))
    seen = {}

    def fake_capture(sensor, output, config, **kwargs):
        seen["config"] = config
        seen["tilt_cb"] = kwargs.get("tilt_cb")

    monkeypatch.setattr(cli, "capture_frames", fake_capture)

    result = CliRunner().invoke(
        cli.app,
        [
            "capture",
            "--output",
            str(tmp_path / "scan"),
            "--capture-preset",
            "face-scan",
            "--no-tilt-sweep",
            "--frames",
            "7",
        ],
    )

    assert result.exit_code == 0, result.output
    assert seen["config"].tilt_sweep is False
    assert seen["tilt_cb"] is None
    assert seen["config"].frames == 7
    # Untyped values still come from the preset.
    assert seen["config"].fps == 20.0
