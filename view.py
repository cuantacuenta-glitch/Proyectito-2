from __future__ import annotations

import cv2
import win32api
import win32con

MARGIN_W, MARGIN_H = 80, 150


def work_area(hwnd: int | None = None) -> tuple[int, int, int, int]:
    try:
        if hwnd:
            hmon = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
        else:
            hmon = win32api.MonitorFromPoint((0, 0), win32con.MONITOR_DEFAULTTOPRIMARY)
        return tuple(win32api.GetMonitorInfo(hmon)["Work"])
    except Exception:
        return (0, 0, win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1))


def fit_scale(img_w: int, img_h: int, want: float = 1.0, hwnd: int | None = None) -> float:
    """Escala pedida, recortada para que la imagen quepa en el monitor."""
    wl, wt, wr, wb = work_area(hwnd)
    max_w = max(200, (wr - wl) - MARGIN_W)
    max_h = max(200, (wb - wt) - MARGIN_H)
    return max(0.35, min(float(want), max_w / img_w, max_h / img_h))


def select(name: str, img, hwnd: int | None = None):
    """selectROI con la ventana colocada arriba-izquierda. Devuelve coords en la imagen."""
    cv2.namedWindow(name, cv2.WINDOW_AUTOSIZE)
    cv2.imshow(name, img)
    wl, wt, _, _ = work_area(hwnd)
    cv2.moveWindow(name, wl + 20, wt + 20)
    roi = cv2.selectROI(name, img, showCrosshair=True, fromCenter=False)
    try:
        cv2.destroyWindow(name)
    except Exception:
        pass
    return roi