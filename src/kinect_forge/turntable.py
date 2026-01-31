from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class TurntablePreset:
    name: str
    model: str
    diameter_mm: int
    rotation_seconds: float


_PRESETS: Dict[str, TurntablePreset] = {
    "vxb-8": TurntablePreset(
        name="vxb-8",
        model="VXB 8-inch electric turntable",
        diameter_mm=200,
        rotation_seconds=16.0,
    ),
    "sutekus-5.4": TurntablePreset(
        name="sutekus-5.4",
        model="Sutekus 5.4-inch rotating display stand",
        diameter_mm=137,
        rotation_seconds=15.0,
    ),
}


def get_turntable_preset(name: str) -> TurntablePreset:
    key = name.lower().strip()
    if key not in _PRESETS:
        raise ValueError("turntable preset must be one of: vxb-8, sutekus-5.4")
    return _PRESETS[key]
