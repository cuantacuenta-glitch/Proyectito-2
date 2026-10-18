from __future__ import annotations

import time

import win32con
import win32gui
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

import dpi
import layout
import ocr
from capture import Grabber


class TableOverlay(QWidget):
    """Ventana transparente, siempre encima y atravesable por el raton."""

    def __init__(self, table, cfg):
        flags = (Qt.WindowType.FramelessWindowHint
                 | Qt.WindowType.WindowStaysOnTopHint
                 | Qt.WindowType.Tool
                 | Qt.WindowType.WindowTransparentForInput
                 | Qt.WindowType.WindowDoesNotAcceptFocus)
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.hwnd = table.hwnd
        self.cfg = cfg
        self.regions = layout.load_regions(cfg.table_seats)
        self.fps = 0.0
        self._frames = 0
        self._t0 = time.perf_counter()

        # Estado OCR
        self.values: dict[str, float | None] = {}
        self.spr: float | None = None
        self._rect = None  # (l, t, r, b) de la mesa en pixeles de pantalla
        ocr.load_font()
        self._grabber = Grabber(cfg.capture_backend)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._sync)
        self._timer.start(50)

        self._ocr_timer = QTimer(self)
        self._ocr_timer.timeout.connect(self._update_ocr)
        self._ocr_timer.start(2000)  # OCR cada 2 s
        self._sync()

    def _sync(self):
        try:
            if not win32gui.IsWindow(self.hwnd) or not win32gui.IsWindowVisible(self.hwnd):
                self.hide(); return
            if win32gui.IsIconic(self.hwnd):
                self.hide(); return
            l, t, r, b = win32gui.GetWindowRect(self.hwnd)
        except Exception:
            self.hide(); return

        self._rect = (l, t, r, b)
        s = dpi.scale_for_window(self.hwnd)
        self.setGeometry(int(l / s), int(t / s), int((r - l) / s), int((b - t) / s))
        if not self.isVisible():
            self.show()
        win32gui.SetWindowPos(int(self.winId()), win32con.HWND_TOPMOST, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)

    def _update_ocr(self):
        """Lee stacks y pot, calcula SPR."""
        if not self._rect or not self.isVisible():
            return
        l, t, r, b = self._rect
        W, H = r - l, b - t
        vals: dict[str, float | None] = {}
        for k in ["pot"] + [f"seat{i}" for i in range(self.cfg.table_seats)]:
            if k not in self.regions:
                vals[k] = None
                continue
            nx, ny, nw, nh = self.regions[k]
            box = (l + int(nx * W), t + int(ny * H),
                   l + int((nx + nw) * W), t + int((ny + nh) * H))
            try:
                img = self._grabber.grab(box)
            except Exception:
                img = None
            if img is None:
                vals[k] = None
                continue
            try:
                vals[k] = ocr.read_amount(img, self.cfg.ocr_min_conf)
            except Exception:
                vals[k] = None
        self.values = vals

        # SPR = stack efectivo / pot (stack efectivo = menor stack no nulo)
        pot = vals.get("pot")
        stacks = [v for k, v in vals.items()
                  if k.startswith("seat") and v is not None and v > 0]
        if pot and pot > 0 and stacks:
            self.spr = min(stacks) / pot
        else:
            self.spr = None
        self.update()  # repintar

    def bump(self):
        self._frames += 1
        now = time.perf_counter()
        if now - self._t0 >= 1.0:
            self.fps = self._frames / (now - self._t0)
            self._frames = 0
            self._t0 = now

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()

        p.setPen(QPen(QColor(0, 220, 255, 170), 2))
        p.drawRect(1, 1, w - 2, h - 2)

        if self.cfg.debug_grid:
            p.setFont(QFont("Tahoma", 7))
            for name, (nx, ny, nw, nh) in self.regions.items():
                hero = name == f"seat{self.cfg.hero_seat}"
                col = QColor(255, 90, 90, 220) if hero else QColor(255, 196, 0, 190)
                p.setPen(QPen(col, 1))
                x, y, bw, bh = int(nx * w), int(ny * h), int(nw * w), int(nh * h)
                p.drawRect(x, y, bw, bh)
                p.setPen(col)
                p.drawText(x + 3, y + 11, name)

        # --- HUD: SPR ---
        if self.spr is not None and "pot" in self.regions:
            nx, ny, nw, nh = self.regions["pot"]
            cx = int((nx + nw / 2) * w)
            cy = int((ny + nh) * h) + 24
            # color segun SPR: verde deep, amarillo medio, rojo short
            if self.spr >= 10:
                col = QColor(80, 255, 120, 235)
            elif self.spr >= 4:
                col = QColor(255, 210, 60, 235)
            else:
                col = QColor(255, 90, 90, 235)
            p.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
            p.setPen(col)
            txt = f"SPR {self.spr:.1f}"
            tw = p.fontMetrics().horizontalAdvance(txt)
            # fondo semitransparente
            p.fillRect(cx - tw // 2 - 6, cy - 18, tw + 12, 24,
                       QColor(0, 0, 0, 150))
            p.drawText(cx - tw // 2, cy, txt)

        if self.cfg.debug_fps:
            p.setPen(QColor(0, 255, 0, 235))
            p.setFont(QFont("Consolas", 8))
            info = f"{self.width()}x{self.height()}  {self.fps:4.1f} fps"
            if self.values.get("pot") is not None:
                info += f"  pot {self.values['pot']:.1f}"
            p.drawText(6, 16, info)
