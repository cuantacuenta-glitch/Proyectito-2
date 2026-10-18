from __future__ import annotations

import time

import cv2
import numpy as np

import view
import win
from capture import Grabber
from ocr import FONT_DIR, SYMBOLS, sym_file

INFO = {
    "0": "un cero de un stack o del pot",
    ",": "la coma decimal (en '0,05')",
    ".": "el punto decimal (en '163.20')",
    "K": "una K si aparece",
    "M": "una M si aparece",
    "B": "una B de 'BB'",
    "€": "el simbolo del euro",
    "$": "el simbolo del dolar",
    "£": "el simbolo de la libra",
}


def main(cfg, table_index: int = 0, zoom: float = 2.0, symbols: list[str] | None = None, region: str | None = None) -> None:
    tables = win.find_tables(cfg)
    if not tables:
        print("Abre una mesa con numeros visibles."); return
    t = tables[min(table_index, len(tables) - 1)]

    time.sleep(0.3)
    img = Grabber(cfg.capture_backend).grab(t.rect)
    if img is None:
        print("Sin captura."); return

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if region:
        import layout
        regs = layout.load_regions(cfg.table_seats)
        if region in regs:
            H0, W0 = gray.shape[:2]
            nx, ny, nw, nh = regs[region]
            x0, y0 = int(nx * W0), int(ny * H0)
            x1, y1 = int((nx + nw) * W0), int((ny + nh) * H0)
            mx, my = int((x1 - x0) * 0.2), int((y1 - y0) * 0.2)
            x0, y0 = max(0, x0 - mx), max(0, y0 - my)
            x1, y1 = min(W0, x1 + mx), min(H0, y1 + my)
            img = img[y0:y1, x0:x1]
            gray = gray[y0:y1, x0:x1]
            print(f"Recorte a region '{region}': {x1-x0}x{y1-y0}")
    H, W = gray.shape[:2]
    scale = view.fit_scale(W, H, zoom, t.hwnd)
    big = img if abs(scale - 1.0) < 0.01 else cv2.resize(
        img, None, fx=scale, fy=scale,
        interpolation=cv2.INTER_NEAREST if scale > 1 else cv2.INTER_AREA)

    syms = symbols or SYMBOLS
    print(f"Mesa {W}x{H} -> mostrada a x{scale:.2f} ({big.shape[1]}x{big.shape[0]}).")
    print("Rodea UN SOLO caracter, lo mas ajustado posible. ENTER guarda / ESC omite.\n")

    saved = 0
    for s in syms:
        print(f"== '{s}' ==  rodea {INFO.get(s, 'el caracter')}")
        x, y, w, h = view.select(f"train - {s}", big, t.hwnd)
        if w <= 2 or h <= 2:
            print(f"   '{s}': omitido"); continue

        x, y, w, h = int(x / scale), int(y / scale), int(w / scale), int(h / scale)
        crop = gray[y:y + h, x:x + w]

        _, th = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if (th > 0).mean() > 0.5:
            th = cv2.bitwise_not(th)
        ys, xs = np.where(th > 0)
        if len(xs):
            crop = crop[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

        ch, cw = crop.shape[:2]
        cv2.imwrite(str(FONT_DIR / sym_file(s)), crop)
        print(f"   '{s}': guardado {cw}x{ch}")
        if cw > ch * 2.5:
            print("   AVISO: parece mas de un caracter, rehazlo.")
        saved += 1

    print(f"\n{saved} glifos guardados.")
    print("\nresumen de data/font/:")
    for s in SYMBOLS:
        p = FONT_DIR / sym_file(s)
        if p.exists():
            g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
            if g is not None:
                print(f"  {s}: {g.shape[1]}x{g.shape[0]}")


if __name__ == "__main__":
    import config
    main(config.Config.load())