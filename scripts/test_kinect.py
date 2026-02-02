#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time

import cv2
import numpy as np


def _require_freenect() -> object:
    try:
        import freenect  # type: ignore
    except ImportError as exc:
        print("freenect bindings not available.", file=sys.stderr)
        print(
            "Install: libfreenect-dev + python3-freenect (if available) or pip install freenect.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    return freenect


def _list_devices(freenect: object) -> int:
    count = int(freenect.num_devices())
    print(f"Kinect v1 devices detected: {count}")
    if count > 0:
        print("Indices:", ", ".join(str(i) for i in range(count)))
    return 0


def _open_stream(freenect: object, index: int, depth: bool) -> int:
    window_name = "Kinect v1 depth" if depth else "Kinect v1 color"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    last = time.monotonic()
    while True:
        if depth:
            frame, _ = freenect.sync_get_depth(index=index, format=freenect.DEPTH_MM)
            if frame is None:
                print("Failed to read depth frame.", file=sys.stderr)
                return 1
            depth_u16 = np.asarray(frame, dtype=np.uint16)
            depth_vis = cv2.convertScaleAbs(depth_u16, alpha=255.0 / max(depth_u16.max(), 1))
            cv2.imshow(window_name, depth_vis)
        else:
            frame, _ = freenect.sync_get_video(index=index, format=freenect.VIDEO_RGB)
            if frame is None:
                print("Failed to read color frame.", file=sys.stderr)
                return 1
            color = np.asarray(frame, dtype=np.uint8)
            cv2.imshow(window_name, cv2.cvtColor(color, cv2.COLOR_RGB2BGR))

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break

        now = time.monotonic()
        if now - last > 2.0:
            last = now
    cv2.destroyAllWindows()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Kinect v1 devices and preview feed.")
    parser.add_argument("--list", action="store_true", help="List detected Kinect v1 devices")
    parser.add_argument("--index", type=int, default=0, help="Device index to open")
    parser.add_argument(
        "--depth", action="store_true", help="Show depth feed instead of color"
    )
    args = parser.parse_args()

    freenect = _require_freenect()
    if args.list:
        return _list_devices(freenect)
    return _open_stream(freenect, args.index, args.depth)


if __name__ == "__main__":
    raise SystemExit(main())
