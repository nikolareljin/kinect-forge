"""ProcessSensor lifecycle, with stand-in children so no Kinect is needed.

The children are module-level functions because the spawn start method pickles
the target by reference and imports this module in the child.
"""

import sys
import time
import types

import numpy as np
import pytest

from kinect_forge.sensors import process_sensor
from kinect_forge.sensors.process_sensor import ProcessSensor


def _streaming_child(config, conn, commands, stop):
    color = np.zeros((4, 4, 3), dtype=np.uint8)
    n = 0
    try:
        while not stop.is_set():
            try:
                command, value = commands.get_nowait()
            except Exception:
                pass
            else:
                conn.send(("tilt", value < 20, None))
            n += 1
            conn.send(("frame", color, np.full((4, 4), n, dtype=np.uint16)))
            time.sleep(0.01)
    except OSError:
        pass


def _failing_child(config, conn, commands, stop):
    conn.send(("error", "Could not open the Kinect", None))


def _silent_child(config, conn, commands, stop):
    while not stop.is_set():
        time.sleep(0.05)


@pytest.fixture(autouse=True)
def _fake_freenect(monkeypatch):
    # ProcessSensor builds a FreenectV1Sensor in the parent for its properties,
    # which imports freenect; nothing here opens a device.
    monkeypatch.setitem(sys.modules, "freenect", types.SimpleNamespace(DEPTH_REGISTERED=4))


def test_frames_and_tilt_go_through_the_child():
    sensor = ProcessSensor(_child=_streaming_child)
    try:
        sensor.start()
        first = sensor.get_frame()
        second = sensor.get_frame()
        assert second.depth[0, 0] > first.depth[0, 0]
        assert sensor.set_tilt(10) is True
        assert sensor.set_tilt(25) is False
    finally:
        sensor.stop()
    assert sensor._process is None


def test_start_failure_cleans_up_and_can_retry():
    sensor = ProcessSensor(_child=_failing_child)
    with pytest.raises(RuntimeError, match="Could not open the Kinect"):
        sensor.start()
    assert sensor._process is None

    sensor._child = _streaming_child
    try:
        sensor.start()
        sensor.get_frame()
    finally:
        sensor.stop()


def test_a_child_that_never_sends_a_frame_times_out_and_is_stopped(monkeypatch):
    monkeypatch.setattr(process_sensor, "_START_TIMEOUT", 1.0)
    sensor = ProcessSensor(_child=_silent_child)
    with pytest.raises(RuntimeError, match="No frame from the Kinect"):
        sensor.start()
    assert sensor._process is None


class _StubSensor:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


def test_gui_gives_the_kinect_to_one_user_at_a_time(monkeypatch):
    import threading

    from kinect_forge import gui

    monkeypatch.setattr(gui, "ProcessSensor", _StubSensor)
    logs = []
    app = types.SimpleNamespace(
        _sensor_lock=threading.Lock(), _active_sensor=None, _log=logs.append
    )

    first = gui.App._claim_sensor(app, "live preview")
    assert first is not None
    assert gui.App._claim_sensor(app, "capture") is None
    assert "in use" in logs[-1]

    gui.App._release_sensor(app, first)
    assert first.stopped
    assert app._active_sensor is None
    assert gui.App._claim_sensor(app, "capture") is not None
