"""Kinect v1 sensor that runs libfreenect in a child process.

The GUI needs this. When libfreenect's sync thread is started inside a process
whose Tk main loop is running, the Kinect delivers no frames: sync_get_depth
waits forever while the libusb event thread polls with nothing arriving. Outside
Tk the same calls run at 30 fps. Keeping libfreenect in its own process avoids
that, and a stalled device becomes a timeout error instead of a frozen preview.

The child streams frames continuously; the parent keeps only the newest, so the
preview shows the current view rather than a backlog. Tilt commands go to the
child because it holds the device (a second open from the parent fails with
LIBUSB_ERROR_BUSY).
"""

from __future__ import annotations

import multiprocessing as mp
import queue
import threading
from collections.abc import Callable
from multiprocessing.connection import Connection
from typing import Any

from kinect_forge.sensors.base import RGBDFrame
from kinect_forge.sensors.freenect_v1 import FreenectV1Config, FreenectV1Sensor


def _run_child(config: FreenectV1Config, conn: Connection, commands: Any, stop: Any) -> None:
    from kinect_forge.sensors.freenect_v1 import set_tilt_degs, stop_sync

    try:
        sensor = FreenectV1Sensor(config)
        sensor.start()
        while not stop.is_set():
            try:
                command, value = commands.get_nowait()
            except queue.Empty:
                pass
            else:
                if command == "tilt":
                    try:
                        conn.send(("tilt", set_tilt_degs(value), None))
                    except RuntimeError as exc:
                        conn.send(("tilt", False, str(exc)))
            frame = sensor.get_frame()
            conn.send(("frame", frame.color, frame.depth))
    except (BrokenPipeError, EOFError, OSError):
        # The parent closed its end; nothing left to report to.
        pass
    except Exception as exc:  # reported to the parent, which raises it
        try:
            conn.send(("error", str(exc), None))
        except (BrokenPipeError, OSError):
            pass
    finally:
        stop_sync()
        conn.close()


# One open of a Kinect v1 takes about 10 s on the hardware tested, and the child
# retries a failed open up to three times.
_START_TIMEOUT = 45.0


class ProcessSensor:
    """Drop-in for FreenectV1Sensor (start/get_frame/stop) backed by a child process."""

    def __init__(
        self,
        config: FreenectV1Config | None = None,
        timeout: float = 5.0,
        _child: Callable[..., None] = _run_child,
    ) -> None:
        self._config = config or FreenectV1Config()
        # Imports freenect, so a missing binding fails here as it does for
        # FreenectV1Sensor; it does not open the device.
        self._local = FreenectV1Sensor(self._config)
        # The child's entry point; tests replace it with one that needs no Kinect.
        self._child = _child
        self._timeout = timeout
        self._process: Any = None
        self._conn: Connection | None = None
        self._commands: Any = None
        self._stop: Any = None
        self._reader: threading.Thread | None = None
        self._cond = threading.Condition()
        self._frame: RGBDFrame | None = None
        self._seq = 0
        self._seen = 0
        self._error: str | None = None
        # Bumped on every spawn so a reader thread left from an earlier child cannot
        # report that child's exit into the current one.
        self._generation = 0
        self._tilt_results: queue.Queue[tuple[bool, str | None]] = queue.Queue()
        # start() can be reached from a capture thread and from a tilt request at once.
        self._lifecycle = threading.Lock()
        # One tilt request in flight at a time, so replies cannot be swapped.
        self._tilt_lock = threading.Lock()

    @property
    def depth_registered(self) -> bool:
        return self._local.depth_registered

    @property
    def depth_scale(self) -> float:
        return self._local.depth_scale

    def start(self) -> None:
        with self._lifecycle:
            if self._process is not None:
                return
            try:
                self._spawn()
                self._wait_for_frame(_START_TIMEOUT)
            except BaseException:
                # Do not leave a stalled child holding the USB device, and let a
                # later start() try again from scratch.
                self._shutdown()
                raise

    def _spawn(self) -> None:
        with self._cond:
            self._generation += 1
            self._frame = None
            self._seq = 0
            self._seen = 0
            self._error = None
        generation = self._generation
        ctx = mp.get_context("spawn")
        parent_conn, child_conn = ctx.Pipe(duplex=False)
        self._commands = ctx.Queue()
        self._stop = ctx.Event()
        self._process = ctx.Process(
            target=self._child,
            args=(self._config, child_conn, self._commands, self._stop),
            daemon=True,
        )
        self._process.start()
        child_conn.close()
        self._conn = parent_conn
        self._reader = threading.Thread(
            target=self._read, args=(parent_conn, generation), daemon=True
        )
        self._reader.start()

    def _read(self, conn: Connection, generation: int) -> None:
        try:
            while True:
                kind, first, second = conn.recv()
                if kind == "frame":
                    with self._cond:
                        if generation != self._generation:
                            return
                        self._frame = RGBDFrame(color=first, depth=second)
                        self._seq += 1
                        self._cond.notify_all()
                elif kind == "tilt":
                    self._tilt_results.put((bool(first), second))
                else:
                    self._fail(str(first), generation)
                    return
        except (EOFError, OSError):
            self._fail("The Kinect process exited.", generation)

    def _fail(self, message: str, generation: int) -> None:
        with self._cond:
            if generation == self._generation and self._error is None:
                self._error = message
            self._cond.notify_all()

    def _wait_for_frame(self, timeout: float) -> RGBDFrame:
        with self._cond:
            ready = self._cond.wait_for(
                lambda: self._seq > self._seen or self._error is not None, timeout
            )
            if self._error is not None:
                raise RuntimeError(self._error)
            if not ready or self._frame is None:
                raise RuntimeError(
                    f"No frame from the Kinect in {timeout:.0f} s. Unplug and replug its USB "
                    "and power, then try again."
                )
            self._seen = self._seq
            return self._frame

    def get_frame(self) -> RGBDFrame:
        if self._process is None:
            self.start()
        return self._wait_for_frame(self._timeout)

    def set_tilt(self, angle: float) -> bool:
        """Tilt through the child, which holds the device. Same result as set_tilt_degs."""
        if self._process is None:
            self.start()
        with self._tilt_lock:
            # A reply that arrived after an earlier request timed out is stale.
            while not self._tilt_results.empty():
                self._tilt_results.get_nowait()
            self._commands.put(("tilt", float(angle)))
            try:
                responding, error = self._tilt_results.get(timeout=self._timeout)
            except queue.Empty as exc:
                raise RuntimeError("The Kinect process did not answer the tilt request.") from exc
        if error is not None:
            raise RuntimeError(error)
        return responding

    def stop(self) -> None:
        with self._lifecycle:
            self._shutdown()

    def _shutdown(self) -> None:
        if self._process is None:
            return
        self._stop.set()
        # The reader thread keeps draining the pipe, so the child is never stuck
        # sending; it sees the stop event after its current frame and exits, which
        # ends the reader with EOF. Only a child stuck inside libfreenect needs
        # terminating. The pipe is closed after that: closing it under a reader
        # that is still in recv() breaks that thread.
        self._process.join(timeout=3.0)
        if self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=1.0)
        if self._reader is not None:
            self._reader.join(timeout=1.0)
            self._reader = None
        if self._conn is not None:
            self._conn.close()
        # A queue with unread items would otherwise block this process at exit.
        self._commands.cancel_join_thread()
        self._commands.close()
        self._process = None
        self._conn = None
