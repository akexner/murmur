"""Filesystem locations. Everything user-owned lives under %APPDATA%\\Murmur."""
import os
import sys

APP = "Murmur"


def data_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, APP)
    os.makedirs(d, exist_ok=True)
    return d


def sub(*parts: str) -> str:
    d = os.path.join(data_dir(), *parts)
    os.makedirs(d, exist_ok=True)
    return d


def inprogress_dir() -> str:
    return sub("recordings", "in-progress")


def saved_dir() -> str:
    return sub("recordings", "saved")


def trash_dir() -> str:
    return sub("recordings", "trash")


def models_dir() -> str:
    return sub("models")


def config_path() -> str:
    return os.path.join(data_dir(), "config.json")


def db_path() -> str:
    return os.path.join(data_dir(), "murmur.db")


def log_path() -> str:
    return os.path.join(data_dir(), "murmur.log")


def resource(*parts: str) -> str:
    """Path to a bundled file (works in dev and inside the PyInstaller build)."""
    if getattr(sys, "frozen", False):
        base = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), "murmur")
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)
