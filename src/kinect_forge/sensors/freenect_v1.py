from __future__ import annotations

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

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def get_frame(self) -> RGBDFrame:
        freenect = self._freenect
        color, _ = freenect.sync_get_video(format=freenect.VIDEO_RGB)
        if color is None:
            raise RuntimeError("Failed to read color frame from Kinect.")

        depth_format = freenect.DEPTH_MM
        if self._config.depth_format == "11bit":
            depth_format = freenect.DEPTH_11BIT
        elif self.depth_registered:
            depth_format = freenect.DEPTH_REGISTERED
        depth, _ = freenect.sync_get_depth(format=depth_format)
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


def set_tilt_degs(angle: float, index: int = 0) -> None:
    try:
        import freenect
    except ImportError as exc:
        raise RuntimeError("freenect not available for tilt control.") from exc

    if hasattr(freenect, "sync_set_tilt_degs"):
        freenect.sync_set_tilt_degs(float(angle), index=index)
        return

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
