import signal
import sys

import dpi
dpi.enable_dpi_awareness()

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

import win
from config import Config
from overlay import TableOverlay

signal.signal(signal.SIGINT, signal.default_int_handler)


class Manager:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.overlays: dict[int, TableOverlay] = {}
        self._timer = QTimer()
        self._timer.timeout.connect(self.tick)
        self._timer.start(250)

    def tick(self):
        found = win.find_tables(self.cfg)
        alive = set()
        for t in found:
            alive.add(t.hwnd)
            if t.hwnd not in self.overlays:
                self.overlays[t.hwnd] = TableOverlay(t, self.cfg)
                print(f"[+] mesa {t.hwnd}  {t.width}x{t.height}  {t.title[:40]}")
        for hwnd in list(self.overlays):
            if hwnd not in alive:
                self.overlays.pop(hwnd).close()
                print(f"[-] mesa {hwnd} cerrada")


def _arg(name):
    argv = sys.argv
    if name not in argv:
        return None
    i = argv.index(name)
    if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
        return argv[i + 1]
    return ""


def main():
    cfg = Config.load()

    if "--list" in sys.argv:
        win.dump_all(); return

    if "--calib" in sys.argv:
        import calib
        z = _arg("--calib") or None
        calib.main(cfg, zones=z.split(",") if z else None,
                   zoom=float(_arg("--zoom") or 1)); return

    if "--train" in sys.argv:
        import train_font
        syms = _arg("--train") or None
        train_font.main(cfg, zoom=float(_arg("--zoom") or 2),
                        symbols=syms.split(",") if syms else None,
                        region=_arg("--region")); return

    if "--read" in sys.argv:
        read_test(cfg); return

    if "--shot" in sys.argv:
        save_shots(cfg); return

    if "--process" in sys.argv:
        cfg.client_process = sys.argv[sys.argv.index("--process") + 1].split(",")
        cfg.save()
    if "--seats" in sys.argv:
        cfg.table_seats = int(sys.argv[sys.argv.index("--seats") + 1])
        cfg.save()

    app = QApplication(sys.argv)
    mgr = Manager(cfg)  # mantener referencia viva
    print(f"Vigilando {cfg.client_process} | {cfg.table_seats} asientos | {cfg.capture_backend}")
    print("Ctrl+C en esta consola para salir.")
    sys.exit(app.exec())


def read_test(cfg):
    import time

    import cv2

    import layout
    import ocr
    from capture import Grabber
    from config import DATA

    n = ocr.load_font()
    print(f"plantillas cargadas: {n}")
    if n < 3:
        print("Entrena primero con:  run.cmd --train"); return

    tables = win.find_tables(cfg)
    if not tables:
        print("No hay mesas abiertas."); return

    t = tables[0]
    time.sleep(0.3)
    g = Grabber(cfg.capture_backend)
    regs = layout.load_regions(cfg.table_seats)
    out = DATA / "shots"
    out.mkdir(parents=True, exist_ok=True)

    l, tp, W, H = t.rect[0], t.rect[1], t.width, t.height
    for k in ["pot"] + [f"seat{i}" for i in range(cfg.table_seats)]:
        nx, ny, nw, nh = regs[k]
        box = (l + int(nx * W), tp + int(ny * H),
               l + int((nx + nw) * W), tp + int((ny + nh) * H))
        box = (max(l, box[0]), max(tp, box[1]),
               min(l + W, box[2]), min(tp + H, box[3]))
        img = g.grab(box)
        if img is None:
            print(f"{k}: sin captura"); continue
        cv2.imwrite(str(out / f"read_{k}.png"), img)
        lines = ocr.read_lines(img, cfg.ocr_min_conf)
        val = ocr.read_amount(img, cfg.ocr_min_conf)
        print(f"{k}: {lines}  ->  {val}")
        for x, s, conf, size in ocr.debug(img, cfg.ocr_min_conf):
            print(f"     x={x:<4} '{s}' conf={conf} {size}")
    print(f"\nrecortes guardados en {out}")


def save_shots(cfg):
    import time
    from pathlib import Path

    import cv2

    from capture import Grabber

    out = Path(__file__).resolve().parent / "data" / "shots"
    out.mkdir(parents=True, exist_ok=True)
    g = Grabber(cfg.capture_backend)

    tables = win.find_tables(cfg)
    if not tables:
        print("No hay mesas abiertas.")
        return

    for t in tables:
        time.sleep(0.3)
        img = g.grab(t.rect)
        if img is None:
            print(f"sin captura para {t.hwnd}")
            continue
        fn = out / f"{t.hwnd}_{t.width}x{t.height}.png"
        cv2.imwrite(str(fn), img)
        print(f"guardado -> {fn}  ({img.shape[1]}x{img.shape[0]})")


if __name__ == "__main__":
    main()