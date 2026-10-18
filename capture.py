from __future__ import annotations

import time

import numpy as np
import win32api
import win32con


def list_monitors():
    """Devuelve una lista de tuplas con las coordenadas (left, top, right, bottom) de los monitores."""
    mons = []
    for i in range(16):
        try:
            hmon = win32api.EnumDisplayMonitors(None, None)[i][0]
            info = win32api.GetMonitorInfo(hmon)
            rect = info['Monitor']  # Es una tupla (left, top, right, bottom)
            mons.append(rect)
        except Exception:
            break
    if not mons:
        mons.append((0, 0, win32api.GetSystemMetrics(win32con.SM_CXSCREEN), win32api.GetSystemMetrics(win32con.SM_CYSCREEN)))
    return mons

def monitor_for(box):
    l, t, r, b = box
    cx = (l + r) // 2
    cy = (t + b) // 2
    
    mons = list_monitors()
    for idx, m in enumerate(mons):
        # m es una tupla: (left, top, right, bottom) -> m[0], m[1], m[2], m[3]
        if m[0] <= cx <= m[2] and m[1] <= cy <= m[3]:
            return idx, m
            
    return 0, mons[0]


class Grabber:
    """Captura regiones de pantalla. DXGI por monitor, con reserva a BitBlt."""

    def __init__(self, backend: str = "dxcam"):
        self.backend = backend
        self._cameras: dict[int, object] = {}
        self._sct = None
        self._dxcam = None

        if backend == "dxcam":
            try:
                import dxcam
                self._dxcam = dxcam
            except Exception:
                self.backend = "mss"

        if self.backend == "mss":
            import mss
            self._sct = mss.mss()

    def _camera(self, idx: int):
        if idx not in self._cameras:
            cam = self._dxcam.create(output_idx=idx, output_color="BGR")
            if cam is None:
                raise RuntimeError(f"sin salida DXGI {idx}")
            self._cameras[idx] = cam
        return self._cameras[idx]

    def grab(self, rect, retries: int = 6):
        l, t, r, b = (int(v) for v in rect)
        if r - l <= 0 or b - t <= 0:
            return None

        if self.backend == "dxcam":
            idx, mon = monitor_for((l, t, r, b))
            cam = self._camera(idx)
            local = (l - mon[0], t - mon[1], r - mon[0], b - mon[1])
            for _ in range(retries):
                frame = cam.grab(region=local)
                if frame is not None:
                    return frame
                time.sleep(0.05)
            full = cam.get_latest_frame()
            if full is None:
                return None
            x0, y0, x1, y1 = local
            return full[y0:y1, x0:x1].copy()

        shot = self._sct.grab({"left": l, "top": t, "width": r - l, "height": b - t})
        return np.asarray(shot)[:, :, :3].copy()