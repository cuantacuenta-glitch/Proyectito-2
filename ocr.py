from __future__ import annotations

import re

import cv2
import numpy as np

from config import DATA

FONT_DIR = DATA / "font"
FONT_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = list("0123456789") + [",", ".", "K", "M", "B", "€", "$", "£"]

_ALIAS = {".": "dot", ",": "comma", "€": "eur", "$": "usd", "£": "gbp"}
_TPL: dict[str, np.ndarray] = {}
_H, _W = 32, 24
_NUMRE = re.compile(r"\d[\d.,]*")


def sym_file(s: str) -> str:
    return _ALIAS.get(s, s) + ".png"


def _glyph(gray: np.ndarray) -> np.ndarray:
    if gray is None or gray.size == 0:
        return np.zeros((_H, _W), np.uint8)
    up = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    _, th = cv2.threshold(up, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if (th > 0).mean() > 0.5:
        th = cv2.bitwise_not(th)
    ys, xs = np.where(th > 0)
    if len(xs) == 0:
        return np.zeros((_H, _W), np.uint8)
    th = th[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = th.shape[:2]
    s = _H / h
    nw = max(1, min(_W, int(round(w * s))))
    r = cv2.resize(th, (nw, _H), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((_H, _W), np.uint8)
    x0 = (_W - nw) // 2
    canvas[:, x0:x0 + nw] = r
    return canvas


def _feat(mask: np.ndarray) -> np.ndarray:
    return cv2.GaussianBlur(mask, (3, 3), 0).astype(np.float32)


def load_font() -> int:
    _TPL.clear()
    for s in SYMBOLS:
        p = FONT_DIR / sym_file(s)
        if not p.exists():
            continue
        g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if g is None or g.size == 0:
            continue
        _TPL[s] = _feat(_glyph(g))
    return len(_TPL)


def _match(patch: np.ndarray) -> tuple[str, float]:
    if not _TPL:
        return "?", 0.0
    # El '1' es el unico glifo alto y estrecho: atajo geometrico fiable.
    h, w = patch.shape[:2]
    if h >= 18 and w / max(h, 1) < 0.45:
        return "1", 0.95
    p = _feat(_glyph(patch))
    best, bestv = "?", -2.0
    for s, tpl in _TPL.items():
        v = float(cv2.matchTemplate(p, tpl, cv2.TM_CCOEFF_NORMED)[0, 0])
        if v > bestv:
            best, bestv = s, v
    return best, bestv


def _components(gray: np.ndarray):
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if (th > 0).mean() > 0.5:
        th = cv2.bitwise_not(th)
    n, _, stats, _ = cv2.connectedComponentsWithStats(th, 8)
    comps = [(int(stats[i][0]), int(stats[i][1]), int(stats[i][2]),
              int(stats[i][3]), int(stats[i][4])) for i in range(1, n)]
    if not comps:
        return []
    max_h = max(c[3] for c in comps)
    keep = []
    for x, y, w, h, area in comps:
        if area < 2:
            continue
        if h >= max_h * 0.4:
            keep.append((x, y, w, h))
        elif w <= max_h * 0.6 and h <= max_h * 0.5:
            keep.append((x, y, w, h))
    return keep


def _group_lines(comps, tol):
    comps = sorted(comps, key=lambda c: c[1] + c[3] / 2)
    lines: list[list[tuple[int, int, int, int]]] = []
    centers: list[float] = []
    for c in comps:
        cy = c[1] + c[3] / 2
        for i, ref in enumerate(centers):
            if abs(ref - cy) <= tol:
                lines[i].append(c)
                centers[i] = (ref * (len(lines[i]) - 1) + cy) / len(lines[i])
                break
        else:
            lines.append([c]); centers.append(cy)
    for ln in lines:
        ln.sort(key=lambda c: c[0])
    return lines


def read_lines(bgr: np.ndarray, min_conf: float = 0.45) -> list[str]:
    if bgr is None or bgr.size == 0 or not _TPL:
        return []
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    comps = _components(gray)
    if not comps:
        return []
    hs = sorted(c[3] for c in comps)
    med = hs[len(hs) // 2]
    out = []
    for ln in _group_lines(comps, max(3.0, med * 0.6)):
        text, prev = [], None
        for x, y, w, h in ln:
            if prev is not None and (x - prev) > med * 0.6:
                text.append(" ")
            s, conf = _match(gray[y:y + h, x:x + w])
            text.append(s if conf >= min_conf else "?")
            prev = x + w
        t = "".join(text).strip()
        if t:
            out.append(t)
    return out


def debug(bgr: np.ndarray, min_conf: float = 0.45) -> list[tuple]:
    if bgr is None or bgr.size == 0 or not _TPL:
        return []
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    rows = []
    for (x, y, w, h) in _components(gray):
        s, conf = _match(gray[y:y + h, x:x + w])
        rows.append((x, s, round(conf, 2), f"{w}x{h}"))
    return sorted(rows, key=lambda r: r[0])


def parse_amount(text: str) -> float | None:
    t = text.upper().replace(" ", "")
    mult = 1.0
    if "K" in t:
        mult = 1e3
    elif "M" in t:
        mult = 1e6
    t = re.sub(r"[^0-9.,]", "", t)
    if not t:
        return None
    if "," in t and "." in t:
        dec = "," if t.rfind(",") > t.rfind(".") else "."
        thou = "." if dec == "," else ","
        t = t.replace(thou, "").replace(dec, ".")
    elif "," in t:
        t = t.replace(",", ".") if len(t.split(",")[-1]) <= 2 else t.replace(",", "")
    elif "." in t and len(t.split(".")[-1]) == 3:
        t = t.replace(".", "")
    try:
        return float(t) * mult
    except ValueError:
        return None


def read_amount(bgr: np.ndarray, min_conf: float = 0.45) -> float | None:
    # Pre-ampliar recortes pequenos (ej. pot) para dar mas pixeles al OCR.
    if bgr is not None and bgr.shape[0] < 50:
        bgr = cv2.resize(bgr, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    lines = read_lines(bgr, min_conf)
    if not lines:
        return None
    pref = [l for l in lines if "B" in l] or lines
    for l in reversed(pref):
        # Quitar el sufijo de unidad "BB" (a veces mal leido como 8/B)
        l = re.sub(r"\s*[B8]{1,2}\s*$", "", l)
        # Si queda alguna 'B' dentro del numero, es un '8' mal leido.
        l = l.replace("B", "8").replace("b", "8")
        l = re.sub(r"(?<=\d)\?(?=\d)", ",", l)
        vals = [parse_amount(m.group()) for m in _NUMRE.finditer(l)]
        vals = [v for v in vals if v is not None]
        if vals:
            return max(vals)
    return None