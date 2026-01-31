from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class RGBDFrame:
    color: np.ndarray
    depth: np.ndarray


class Sensor(Protocol):
    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def get_frame(self) -> RGBDFrame:
        ...
