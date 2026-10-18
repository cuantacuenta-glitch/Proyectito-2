from __future__ import annotations

import ctypes

import win32api
import win32con


def enable_dpi_awareness() -> None:
    """Per-monitor DPI aware v2. Llamar ANTES de crear QApplication."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def monitor_of_window(hwnd: int) -> int:
    return win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)


def scale_for_monitor(hmon: int) -> float:
    dx, dy = ctypes.c_uint(), ctypes.c_uint()
    try:
        ctypes.windll.shcore.GetDpiForMonitor(hmon, 0, ctypes.byref(dx), ctypes.byref(dy))
        return max(dx.value, 1) / 96.0
    except Exception:
        return 1.0


def scale_for_window(hwnd: int) -> float:
    return scale_for_monitor(monitor_of_window(hwnd))