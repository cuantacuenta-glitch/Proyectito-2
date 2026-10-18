from __future__ import annotations

import time

import cv2

import layout
import view
import win
from capture import Grabber
from config import DATA

HELP = {
    "pot": "el texto del bote, tipo 'Pot: 7 BB' (centro de la mesa)",
    "board": "las 5 cartas comunitarias (centro, algo mas arriba que el pot)",
}
SEAT_DESC = ["TU asiento (abajo)", "abajo-izquierda", "arriba-izquierda",
             "arriba", "arriba-derecha", "abajo-derecha"]


def _help(k: str) -> str:
    if k in HELP:
        return HELP[k]
    i = int(k.removeprefix("seat"))
    return f"asiento {i} - {SEAT_DESC[i] if i < len(SEAT_DESC) else '?'}: SOLO el numero del stack"


def main(cfg, table_index: int = 0, zones: list[str] | None = None, zoom: float = 1.0) -> None:
    tables = win.find_tables(cfg)
    if not tables:
        print("No hay mesas abiertas."); return
    t = tables[min(table_index, len(tables) - 1)]

    time.sleep(0.3)
    img = Grabber(cfg.capture_backend).grab(t.rect)
    if img is None:
        print("Sin captura."); return

    out = DATA / "shots"
    out.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out / f"calib_{t.hwnd}_{t.width}x{t.height}.png"), img)

    H, W = img.shape[:2]
    scale = view.fit_scale(W, H, zoom, t.hwnd)
    big = img if abs(scale - 1.0) < 0.01 else cv2.resize(
        img, None, fx=scale, fy=scale,
        interpolation=cv2.INTER_NEAREST if scale > 1 else cv2.INTER_AREA)

    regions = layout.load_regions(cfg.table_seats)
    keys = zones or layout.region_keys(cfg.table_seats)

    print(f"Mesa {W}x{H} -> mostrada a x{scale:.2f} ({big.shape[1]}x{big.shape[0]}).")
    print("Clic IZQUIERDO y arrastra sobre la zona, suelta y ENTER. ESC = dejar la actual.\n")

    for k in keys:
        if k not in regions:
            regions[k] = (0.3, 0.3, 0.2, 0.1)
        vis = big.copy()
        nx, ny, nw, nh = regions[k]
        cv2.rectangle(vis, (int(nx * W * scale), int(ny * H * scale)),
                      (int((nx + nw) * W * scale), int((ny + nh) * H * scale)), (0, 255, 255), 1)
        cv2.putText(vis, k, (int(nx * W * scale), max(14, int(ny * H * scale) - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        print(f"== {k} ==  rodea: {_help(k)}")
        x, y, w, h = view.select(f"calib - {k}", vis, t.hwnd)
        if w > 3 and h > 3:
            regions[k] = (round(x / scale / W, 4), round(y / scale / H, 4),
                          round(w / scale / W, 4), round(h / scale / H, 4))
            print(f"   guardado {k}  (alto real {h / scale:.0f}px)")
        else:
            print(f"   {k}: sin cambios")

    layout.save_regions(regions)
    print("\nGuardado -> data/layout.json  (reinicia run.cmd para verlo en el overlay)")