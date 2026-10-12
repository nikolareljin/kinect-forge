from __future__ import annotations

import ctypes
import ctypes.util
import functools
import time
from dataclasses import dataclass

import numpy as np

from kinect_forge.sensors.base import RGBDFrame

REGISTRATION_FALLBACK_MESSAGE = (
    "freenect has no DEPTH_REGISTERED; depth will not be aligned to colour."
)


@dataclass
class FreenectV1Config:
    depth_format: str = "mm"
    # Ask libfreenect for depth aligned to the RGB image (DEPTH_REGISTERED), using
    # the device's factory registration. The two cameras sit ~25 mm apart.
    depth_registration: bool = True


class FreenectV1Sensor:
    def __init__(self, config: FreenectV1Config | None = None) -> None:
        self._config = config or FreenectV1Config()
        try:
            import freenect
        except ImportError as exc:
            raise RuntimeError(
                "freenect not available. Install libfreenect-dev and freenect Python bindings. "
                "Ubuntu 20.04 to 22.04 usually support python3-freenect via apt. "
                "Ubuntu 24.04+ should rerun ./setup to install freenect==0.1.0."
            ) from exc
        self._freenect = freenect

    @property
    def depth_registered(self) -> bool:
        """True when frames come back aligned to the RGB image.

        Only mm depth can be registered, and only when the bindings expose
        DEPTH_REGISTERED; otherwise frames are unregistered and colour is offset.
        """
        return (
            self._config.depth_registration
            and self._config.depth_format != "11bit"
            and hasattr(self._freenect, "DEPTH_REGISTERED")
        )

    @property
    def depth_scale(self) -> float:
        """Scale factor converting raw depth values to metres.

        DEPTH_MM values are in millimetres (scale = 1000.0).
        DEPTH_11BIT values are raw sensor units and require separate calibration.
        """
        return 1000.0 if self._config.depth_format != "11bit" else 1.0

    def start(self, attempts: int = 3) -> None:
        """Open the device and wait for the first frame, retrying a failed open.

        libfreenect's first open of a Kinect v1 sometimes fails ("Failed to fetch
        registration pad info"), and a retry after sync_stop usually succeeds.
        Inside a running Tk main loop use ProcessSensor instead; see its module.
        """
        for attempt in range(1, attempts + 1):
            try:
                self.get_frame()
                return
            except RuntimeError:
                if attempt == attempts:
                    break
                if hasattr(self._freenect, "sync_stop"):
                    self._freenect.sync_stop()
                time.sleep(0.5)
        raise RuntimeError(
            f"Could not open the Kinect after {attempts} attempts. Check that no other "
            "program is using it, then unplug and replug its USB and power."
        )

    def stop(self) -> None:
        return None

    def get_frame(self) -> RGBDFrame:
        freenect = self._freenect
        # sync_get_* return None, not a tuple, when the device cannot be opened.
        video = freenect.sync_get_video(format=freenect.VIDEO_RGB)
        color = video[0] if video is not None else None
        if color is None:
            raise RuntimeError("Failed to read color frame from Kinect.")

        depth_format = freenect.DEPTH_MM
        if self._config.depth_format == "11bit":
            depth_format = freenect.DEPTH_11BIT
        elif self.depth_registered:
            depth_format = freenect.DEPTH_REGISTERED
        result = freenect.sync_get_depth(format=depth_format)
        depth = result[0] if result is not None else None
        if depth is None:
            raise RuntimeError("Failed to read depth frame from Kinect.")

        color = np.asarray(color, dtype=np.uint8)
        depth = np.asarray(depth, dtype=np.uint16)
        return RGBDFrame(color=color, depth=depth)


def probe_device() -> bool:
    try:
        sensor = FreenectV1Sensor()
    except RuntimeError:
        return False
    try:
        _ = sensor.get_frame()
        return True
    except RuntimeError:
        return False


MOTOR_NOT_RESPONDING_MESSAGE = (
    "The Kinect reports no accelerometer data, so the tilt motor is most likely not "
    "responding. Kinect for Windows and Xbox model 1473 drive the motor through the "
    "audio device; if libfreenect printed 'Could not open audio', its firmware is "
    "usually what is missing. See "
    "https://github.com/nikolareljin/kinect-forge/blob/main/docs/SETUP.md#tilt-control-updown-only"
)


class _RawTiltState(ctypes.Structure):
    # freenect_raw_tilt_state from libfreenect.h
    _fields_ = [
        ("accelerometer_x", ctypes.c_int16),
        ("accelerometer_y", ctypes.c_int16),
        ("accelerometer_z", ctypes.c_int16),
        ("tilt_angle", ctypes.c_int8),
        ("tilt_status", ctypes.c_int),
    ]


def _mapped_sync_library() -> str | None:
    """Path of the libfreenect_sync already loaded into this process, if any."""
    try:
        with open("/proc/self/maps") as maps:
            for line in maps:
                path = line.split()[-1]
                if "libfreenect_sync" in path and path.startswith("/"):
                    return path
    except OSError:
        pass
    return None


@functools.cache
def _sync_library() -> ctypes.CDLL | None:
    """libfreenect_sync, the copy the freenect bindings use. Call after importing freenect.

    Only that copy shares the bindings' open device. That is the point: while
    sync_get_video/sync_get_depth are streaming, the device is claimed and a
    second freenect_open_device fails with LIBUSB_ERROR_BUSY. Opening the path
    that is already mapped returns that same copy; a name lookup could load a
    different libfreenect installed alongside it, so it is only the fallback.
    """
    candidates = (
        _mapped_sync_library(),
        ctypes.util.find_library("freenect_sync"),
        "libfreenect_sync.so.0.5",
    )
    for name in candidates:
        if not name:
            continue
        try:
            lib = ctypes.CDLL(name)
            lib.freenect_sync_set_tilt_degs.argtypes = [ctypes.c_int, ctypes.c_int]
            lib.freenect_sync_set_tilt_degs.restype = ctypes.c_int
            lib.freenect_sync_get_tilt_state.argtypes = [
                ctypes.POINTER(ctypes.POINTER(_RawTiltState)),
                ctypes.c_int,
            ]
            lib.freenect_sync_get_tilt_state.restype = ctypes.c_int
        except (OSError, AttributeError):
            continue
        return lib
    return None


def _motor_responding(lib: ctypes.CDLL, index: int) -> bool:
    state = ctypes.POINTER(_RawTiltState)()
    if lib.freenect_sync_get_tilt_state(ctypes.byref(state), index) != 0 or not state:
        # No reading at all; do not claim the motor is dead on that basis.
        return True
    raw = state.contents
    # A working motor board always reports gravity on at least one axis.
    return (raw.accelerometer_x, raw.accelerometer_y, raw.accelerometer_z) != (0, 0, 0)


def set_tilt_degs(angle: float, index: int = 0) -> bool:
    """Tilt the Kinect v1 to ``angle`` degrees.

    Safe to call while frames are streaming. Returns False when the device gives
    no motor feedback, which in practice means the motor did not move; the
    caller should tell the user (see MOTOR_NOT_RESPONDING_MESSAGE).
    """
    try:
        import freenect
    except ImportError as exc:
        raise RuntimeError("freenect not available for tilt control.") from exc

    lib = _sync_library()
    if hasattr(freenect, "sync_set_tilt_degs"):
        freenect.sync_set_tilt_degs(float(angle), index=index)
        return _motor_responding(lib, index) if lib is not None else True

    if lib is not None:
        if lib.freenect_sync_set_tilt_degs(round(angle), index) != 0:
            raise RuntimeError(f"Failed to set tilt on Kinect {index}.")
        return _motor_responding(lib, index)

    ctx = freenect.init()
    if ctx is None:
        raise RuntimeError("Failed to init freenect context for tilt.")
    try:
        dev = freenect.open_device(ctx, index)
        if dev is None:
            raise RuntimeError("Failed to open freenect device for tilt.")
        freenect.set_tilt_degs(dev, float(angle))
        freenect.close_device(dev)
    finally:
        freenect.shutdown(ctx)
    return True


def stop_sync() -> None:
    """Release the device held by libfreenect's sync thread, if the bindings allow."""
    try:
        import freenect
    except ImportError:
        return
    if hasattr(freenect, "sync_stop"):
        freenect.sync_stop()
