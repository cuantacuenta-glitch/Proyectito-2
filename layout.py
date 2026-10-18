from __future__ import annotations

import json
import math

from config import LAYOUT_PATH


def _default_seats(n: int) -> dict[str, tuple[float, float, float, float]]:
    rx, ry = 0.40, 0.36
    step = 360.0 / n
    out = {}
    for i in range(n):
        ang = math.radians(90.0 + i * step)
        cx = 0.5 + rx * math.cos(ang)
        cy = 0.5 + ry * math.sin(ang)
        out[f"seat{i}"] = (round(cx - 0.095, 4), round(cy - 0.045, 4), 0.19, 0.09)
    return out


def region_keys(seats: int) -> list[str]:
    return ["pot", "board"] + [f"seat{i}" for i in range(seats)]


def defaults(seats: int) -> dict[str, tuple[float, float, float, float]]:
    d = {"pot": (0.40, 0.415, 0.20, 0.075), "board": (0.28, 0.315, 0.44, 0.09)}
    d.update(_default_seats(seats))
    return d


def load_regions(seats: int) -> dict[str, tuple[float, float, float, float]]:
    base = defaults(seats)
    if LAYOUT_PATH.exists():
        try:
            saved = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
            for k, v in saved.items():
                if len(v) == 4:
                    base[k] = tuple(float(x) for x in v)
        except Exception:
            pass
    return base


def save_regions(regions: dict[str, tuple[float, float, float, float]]) -> None:
    LAYOUT_PATH.write_text(
        json.dumps({k: [round(float(x), 4) for x in v] for k, v in regions.items()}, indent=2),
        encoding="utf-8")