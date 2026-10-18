from __future__ import annotations

import re
from dataclasses import dataclass

CURRENCIES = {"€": "EUR", "$": "USD", "£": "GBP"}
_SPLIT = re.compile(r"\s*\|\s*")
_NUM = re.compile(r"\d[\d\s.,]*")


@dataclass(frozen=True)
class TableInfo:
    table: str
    game: str
    sb: float
    bb: float
    currency: str
    raw: str


def _to_float(s: str) -> float:
    s = s.replace(" ", "")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse(title: str) -> TableInfo | None:
    parts = _SPLIT.split(title.strip())
    if len(parts) < 3:
        return None
    table, game, stake = parts[0], parts[1], parts[2]
    cur = next((c for c in CURRENCIES if c in stake), "?")
    nums = _NUM.findall(stake)
    if len(nums) < 2:
        return None
    return TableInfo(table=table, game=game, sb=_to_float(nums[0]),
                     bb=_to_float(nums[1]), currency=cur, raw=title)