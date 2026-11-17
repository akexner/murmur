"""Small Windows helpers: which app has focus, which apps are open."""
import ctypes
import os
from ctypes import wintypes

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                            ctypes.POINTER(wintypes.DWORD)]
k32.CloseHandle.argtypes = [wintypes.HANDLE]
u32.GetForegroundWindow.restype = wintypes.HWND
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
u32.IsWindowVisible.argtypes = [wintypes.HWND]
u32.GetWindowTextLengthW.argtypes = [wintypes.HWND]


def _exe_of(pid: int) -> str:
    h = k32.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        n = wintypes.DWORD(1024)
        if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
            return os.path.basename(buf.value).lower()
    finally:
        k32.CloseHandle(h)
    return ""


def foreground():
    """(window handle, lower-case exe name) of the window that has focus right now."""
    hwnd = u32.GetForegroundWindow()
    pid = wintypes.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return (hwnd or 0), (_exe_of(pid.value) if pid.value else "")


def open_apps():
    """Sorted exe names of apps that currently have a visible window."""
    found = set()
    PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        if u32.IsWindowVisible(hwnd) and u32.GetWindowTextLengthW(hwnd) > 0:
            pid = wintypes.DWORD()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            exe = _exe_of(pid.value)
            if exe and exe not in ("murmur.exe", "explorer.exe", "textinputhost.exe"):
                found.add(exe)
        return True

    u32.EnumWindows(PROC(cb), 0)
    return sorted(found)
