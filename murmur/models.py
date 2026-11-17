"""Whisper model catalogue + resumable first-run download with progress."""
import os
import threading
import urllib.error
import urllib.request

from . import paths

MODELS = {
    "tiny":   {"repo": "Systran/faster-whisper-tiny",  "mb": 75,   "label": "Tiny",   "note": "Fastest, rough accuracy"},
    "base":   {"repo": "Systran/faster-whisper-base",  "mb": 145,  "label": "Base",   "note": "Fast, decent"},
    "small":  {"repo": "Systran/faster-whisper-small", "mb": 484,  "label": "Small",  "note": "Great balance (recommended)"},
    "medium": {"repo": "Systran/faster-whisper-medium", "mb": 1530, "label": "Medium", "note": "More accurate, slower"},
    "turbo":  {"repo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo", "mb": 1620, "label": "Turbo",
               "note": "Best accuracy, wants a fast PC"},
}
FILES = ["config.json", "model.bin", "tokenizer.json", "vocabulary.json", "vocabulary.txt",
         "preprocessor_config.json"]

_progress = {"name": None, "pct": 0.0, "error": "", "running": False}
_lock = threading.Lock()


_root_override = ""
offline = lambda: False      # set by the controller; True blocks downloads


def set_root(path: str):
    global _root_override
    _root_override = (path or "").strip()


def root() -> str:
    return _root_override or paths.models_dir()


def model_path(name: str) -> str:
    return os.path.join(root(), name)


def is_ready(name: str) -> bool:
    p = model_path(name)
    if os.path.exists(os.path.join(p, ".complete")):
        return True
    # Models copied in by hand (e.g. from a network share) have no marker.
    return all(os.path.exists(os.path.join(p, f)) for f in ("model.bin", "config.json", "tokenizer.json")) \
        and not os.path.exists(os.path.join(p, "model.bin.part"))


def import_model(src: str, name: str = ""):
    """Copy a model folder (or a folder of model folders) into the models directory."""
    src = os.path.abspath(src or "")
    found = []
    if os.path.exists(os.path.join(src, "model.bin")):
        n = name or os.path.basename(src.rstrip("\\/")).lower()
        if n in MODELS:
            found.append((n, src))
    else:
        for n in MODELS:
            if os.path.exists(os.path.join(src, n, "model.bin")):
                found.append((n, os.path.join(src, n)))
    with _lock:
        if _progress["running"]:
            return
        if not found:
            _progress.update(name=None, pct=0.0, running=False,
                             error="No model found in that folder (expected model.bin, or sub-folders like 'small').")
            return
        _progress.update(name=found[0][0], pct=0.0, error="", running=True)
    threading.Thread(target=_copy, args=(found,), daemon=True, name="model-import").start()


def _copy(found):
    try:
        files = [(os.path.join(d, f), n, f) for n, d in found for f in os.listdir(d)
                 if os.path.isfile(os.path.join(d, f)) and not f.endswith(".part")]
        total = sum(os.path.getsize(p) for p, _, _ in files) or 1
        done = 0
        for p, n, f in files:
            dst_dir = model_path(n)
            os.makedirs(dst_dir, exist_ok=True)
            tmp = os.path.join(dst_dir, f + ".part")
            with open(p, "rb") as a, open(tmp, "wb") as b:
                while True:
                    buf = a.read(1 << 20)
                    if not buf:
                        break
                    b.write(buf)
                    done += len(buf)
                    with _lock:
                        _progress["pct"] = round(min(99.0, done / total * 100), 1)
            os.replace(tmp, os.path.join(dst_dir, f))
        for n, _ in found:
            open(os.path.join(model_path(n), ".complete"), "w").close()
        with _lock:
            _progress.update(pct=100.0, error="")
    except Exception as e:
        with _lock:
            _progress["error"] = f"{type(e).__name__}: {e}"
    finally:
        with _lock:
            _progress["running"] = False


def status() -> dict:
    with _lock:
        return dict(_progress)


def download(name: str):
    """Start a background download (no-op if one is already running)."""
    with _lock:
        if _progress["running"] or name not in MODELS:
            return
        if offline():
            _progress.update(name=name, pct=0.0, running=False,
                             error="Offline mode is on: downloads are disabled. Import a model from a folder instead.")
            return
        _progress.update(name=name, pct=0.0, error="", running=True)
    threading.Thread(target=_run, args=(name,), daemon=True, name="model-dl").start()


def _fetch(url, dest, on_bytes):
    """Streaming download with resume support. Returns False if the file doesn't exist (404)."""
    part = dest + ".part"
    have = os.path.getsize(part) if os.path.exists(part) else 0
    req = urllib.request.Request(url, headers={"User-Agent": "Murmur", **({"Range": f"bytes={have}-"} if have else {})})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        if e.code == 416:          # already complete
            os.replace(part, dest)
            return True
        raise
    if resp.status != 206:
        have = 0                   # server ignored Range: start over
    with resp, open(part, "ab" if have else "wb") as f:
        while True:
            buf = resp.read(1 << 20)
            if not buf:
                break
            f.write(buf)
            on_bytes(len(buf))
    os.replace(part, dest)
    return True


def _run(name):
    target = model_path(name)
    os.makedirs(target, exist_ok=True)
    total = MODELS[name]["mb"] * 1024 * 1024
    got = [0]

    def on_bytes(n):
        got[0] += n
        with _lock:
            _progress["pct"] = round(min(99.0, got[0] / total * 100), 1)

    try:
        for fn in FILES:
            dest = os.path.join(target, fn)
            if os.path.exists(dest):
                got[0] += os.path.getsize(dest)
                continue
            url = f"https://huggingface.co/{MODELS[name]['repo']}/resolve/main/{fn}"
            ok = _fetch(url, dest, on_bytes)
            if not ok and fn in ("config.json", "model.bin", "tokenizer.json"):
                raise RuntimeError(f"{fn} not found on the server")
        open(os.path.join(target, ".complete"), "w").close()
        with _lock:
            _progress.update(pct=100.0, error="")
    except Exception as e:
        with _lock:
            _progress["error"] = f"{type(e).__name__}: {e}"
    finally:
        with _lock:
            _progress["running"] = False
