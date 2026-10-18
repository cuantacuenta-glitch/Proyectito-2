from __future__ import annotations

import os
import re
from dataclasses import dataclass

import psutil
import win32con
import win32gui
import win32process


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    pid: int
    process: str
    cls: str
    title: str
    rect: tuple[int, int, int, int]

    @property
    def width(self) -> int:
        return self.rect[2] - self.rect[0]

    @property
    def height(self) -> int:
        return self.rect[3] - self.rect[1]


def _process_name(pid: int) -> str:
    try:
        return psutil.Process(pid).name()
    except Exception:
        return "?"


def _iter_top_level() -> list[WindowInfo]:
    items: list[WindowInfo] = []

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd) or win32gui.GetParent(hwnd):
            return
        rect = win32gui.GetWindowRect(hwnd)
        if rect[2] - rect[0] < 40 or rect[3] - rect[1] < 40:
            return
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        items.append(WindowInfo(
            hwnd=hwnd, pid=pid, process=_process_name(pid),
            cls=win32gui.GetClassName(hwnd),
            title=win32gui.GetWindowText(hwnd),
            rect=rect,
        ))

    win32gui.EnumWindows(cb, None)
    return items


def find_tables(cfg) -> list[WindowInfo]:
    me = os.getpid()
    procs = {p.lower().removesuffix(".exe") for p in cfg.client_process}
    classes = {c.lower() for c in cfg.window_classes}
    rx = re.compile(cfg.title_regex) if cfg.title_regex else None
    min_w, min_h = cfg.min_table_size

    out = []
    for w in _iter_top_level():
        if w.pid == me or not w.title:
            continue
        if w.process.lower().removesuffix(".exe") not in procs:
            continue
        if classes and w.cls.lower() not in classes:
            continue
        if rx and not rx.search(w.title):
            continue
        if w.width < min_w or w.height < min_h:
            continue
        out.append(w)
    return out


def activate(hwnd: int) -> None:
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass


def foreground_hwnd() -> int:
    return win32gui.GetForegroundWindow()


def dump_all() -> None:
    me = os.getpid()
    rows = sorted((w for w in _iter_top_level() if w.pid != me and w.title),
                  key=lambda w: (w.process.lower(), w.title.lower()))
    print(f"{'HWND':>10}  {'PID':>7}  {'PROCESO':<26} {'CLASE':<28} {'TAM':>11}  TITULO")
    print("-" * 120)
    for w in rows:
        print(f"{w.hwnd:>10}  {w.pid:>7}  {w.process[:26]:<26} {w.cls[:28]:<28} "
              f"{w.width:>5}x{w.height:<5}  {w.title[:55]}")