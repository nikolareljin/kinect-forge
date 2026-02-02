from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from kinect_forge.sensors.base import RGBDFrame


@dataclass
class FreenectV1Config:
    depth_format: str = "mm"


class FreenectV1Sensor:
    def __init__(self, config: Optional[FreenectV1Config] = None) -> None:
        self._config = config or FreenectV1Config()
        try:
            import freenect  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "freenect not available. Install libfreenect and python3-freenect "
                "(Ubuntu: sudo apt install libfreenect-dev python3-freenect)."
            ) from exc
        self._freenect = freenect

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


def set_tilt_degs(angle: float, index: int = 0) -> None:
    try:
        import freenect  # type: ignore
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
    try:
        _ = sensor.get_frame()
        return True
    except RuntimeError:
        return False
