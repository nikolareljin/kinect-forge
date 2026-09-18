from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy.typing as npt


@dataclass(frozen=True)
class RGBDFrame:
    color: npt.NDArray[Any]
    depth: npt.NDArray[Any]


class Sensor(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def get_frame(self) -> RGBDFrame: ...
