"""
Windows signal helpers to gather lightweight activity context.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
from typing import Dict, List

try:
    import win32gui
    import win32process
    import win32con
except Exception:  # pragma: no cover - environment fallback
    win32gui = None
    win32process = None
    win32con = None

try:
    import psutil
except Exception:  # pragma: no cover - environment fallback
    psutil = None


def _get_process_name(pid: int) -> str:
    if pid <= 0:
        return "unknown"
    if psutil:
        try:
            return psutil.Process(pid).name()
        except Exception:
            pass
    return str(pid)


def get_active_window() -> Dict[str, object]:
    """Return best-effort details about the active window."""
    if not win32gui or not win32process:
        return {"process": "unknown", "title": "", "hwnd": 0}

    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process_name = _get_process_name(pid)
        title = win32gui.GetWindowText(hwnd)
        return {"process": process_name, "title": title or "", "hwnd": int(hwnd)}
    except Exception:
        return {"process": "unknown", "title": "", "hwnd": 0}


def list_top_level_windows(limit: int = 30) -> List[Dict[str, str]]:
    """Return a sample of visible top-level windows."""
    if not win32gui or not win32process:
        return []

    windows: List[Dict[str, str]] = []

    def _callback(hwnd, _extra):
        if len(windows) >= limit:
            return False
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process_name = _get_process_name(pid)
        except Exception:
            process_name = "unknown"
        windows.append({"process": process_name, "title": title})
        return True

    try:
        win32gui.EnumWindows(_callback, None)
    except Exception:
        return windows[:limit]
    return windows[:limit]


def get_idle_seconds() -> float:
    """Return seconds since last input using GetLastInputInfo."""
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.wintypes.UINT), ("dwTime", ctypes.wintypes.DWORD)]

    user32 = ctypes.windll.user32 if os.name == "nt" else None
    if not user32:
        return 0.0

    last_input_info = LASTINPUTINFO()
    last_input_info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    try:
        if not user32.GetLastInputInfo(ctypes.byref(last_input_info)):
            return 0.0
        millis = user32.GetTickCount() - last_input_info.dwTime
        return max(0.0, millis / 1000.0)
    except Exception:
        return 0.0