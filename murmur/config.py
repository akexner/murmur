import json
import os
import threading

from . import paths

DEFAULTS = {
    "hotkey": "ctrl+windows",
    "mode": "hold",              # "hold" (push-to-talk) or "toggle"
    "model": "small",
    "language": "auto",
    "mic": None,                 # sounddevice device index or None for default
    "auto_paste": True,
    "restore_clipboard": True,
    "filler_removal": True,
    "voice_commands": True,
    "sounds": True,
    "autostart": False,
    "retention_days": 30,        # 0 = keep audio forever. Starred clips are never expired.
    "terms": [],                 # words to bias recognition towards (names, jargon)
    "replacements": [],          # [{"from": "...", "to": "..."}]
    "offline_mode": False,       # Kanzlei mode: refuse every non-local network connection
    "models_dir": "",            # custom model folder (e.g. a network share); "" = default
    "ui_language": "auto",       # "auto" (follow Windows), "de" or "en"
    "first_run_done": False,
}


class Config:
    def __init__(self):
        self._lock = threading.RLock()
        self._data = dict(DEFAULTS)
        self.load()

    def load(self):
        try:
            with open(paths.config_path(), "r", encoding="utf-8") as f:
                stored = json.load(f)
            if isinstance(stored, dict):
                self._data.update({k: v for k, v in stored.items() if k in DEFAULTS})
        except FileNotFoundError:
            pass
        except Exception:
            # Corrupt config: keep a copy, fall back to defaults.
            try:
                os.replace(paths.config_path(), paths.config_path() + ".corrupt")
            except OSError:
                pass

    def save(self):
        with self._lock:
            tmp = paths.config_path() + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, paths.config_path())

    def get(self, key):
        with self._lock:
            return self._data[key]

    def __getitem__(self, key):
        return self.get(key)

    def update(self, changes: dict):
        with self._lock:
            for k, v in changes.items():
                if k in DEFAULTS:
                    self._data[k] = v
            self.save()

    def snapshot(self) -> dict:
        with self._lock:
            return json.loads(json.dumps(self._data))
