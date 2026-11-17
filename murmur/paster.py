import ctypes
import time
from ctypes import wintypes

import keyboard

CF_UNICODETEXT = 13
u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32
u32.OpenClipboard.argtypes = [wintypes.HWND]
u32.GetClipboardData.restype = ctypes.c_void_p
u32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
k32.GlobalAlloc.restype = ctypes.c_void_p
k32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
k32.GlobalLock.restype = ctypes.c_void_p
k32.GlobalLock.argtypes = [ctypes.c_void_p]
k32.GlobalUnlock.argtypes = [ctypes.c_void_p]


def _open():
    for _ in range(20):
        if u32.OpenClipboard(None):
            return True
        time.sleep(0.02)
    return False


def get_clipboard():
    if not _open():
        return None
    try:
        h = u32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return None
        p = k32.GlobalLock(h)
        try:
            return ctypes.wstring_at(p)
        finally:
            k32.GlobalUnlock(h)
    finally:
        u32.CloseClipboard()


def set_clipboard(text: str) -> bool:
    if not _open():
        return False
    try:
        u32.EmptyClipboard()
        data = (text + "\0").encode("utf-16-le")
        h = k32.GlobalAlloc(0x0042, len(data))  # GMEM_MOVEABLE | GMEM_ZEROINIT
        p = k32.GlobalLock(h)
        ctypes.memmove(p, data, len(data))
        k32.GlobalUnlock(h)
        u32.SetClipboardData(CF_UNICODETEXT, h)
        return True
    finally:
        u32.CloseClipboard()


def paste(text: str, restore=True, hotkeys=None):
    """Put text on the clipboard and press Ctrl+V. The text always stays in history regardless."""
    prev = get_clipboard() if restore else None
    if not set_clipboard(text):
        raise RuntimeError("Could not access the clipboard")
    if hotkeys:
        hotkeys.wait_modifiers_released()
    time.sleep(0.05)
    keyboard.send("ctrl+v")
    if restore and prev is not None:
        time.sleep(0.6)
        set_clipboard(prev)
