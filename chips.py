from __future__ import annotations


def to_bb(amount: float, bb: float) -> float:
    return amount / bb if bb else 0.0


def fmt_bb(amount: float, bb: float, decimals: int = 1) -> str:
    v = to_bb(amount, bb)
    return f"{v:.{decimals}f}".rstrip("0").rstrip(".") if v else "0"