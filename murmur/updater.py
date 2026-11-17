"""Offline, signed updates from a USB stick or folder.

Trust model: an update is only ever accepted if `manifest.json` carries a valid Ed25519 signature
made with the private key that belongs to the public key compiled into this app, AND the payload
matches the SHA-256 recorded inside that signed manifest. No network access is involved.
"""
import base64
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
import ctypes

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from . import __version__, paths
from .update_pubkey import PUBLIC_KEY_B64

log = logging.getLogger("murmur")
EXT = ".murmurupdate"
MAX_MANIFEST = 64 * 1024


class UpdateError(Exception):
    pass


def vtuple(v: str):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:4]) or (0,)


def _verify_manifest(manifest: bytes, sig: bytes, pub_b64: str = PUBLIC_KEY_B64) -> dict:
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(pub_b64)).verify(sig, manifest)
    except (InvalidSignature, ValueError):
        raise UpdateError("Signature is missing or invalid: this update was not made by the owner of the key.")
    m = json.loads(manifest.decode("utf-8"))
    if m.get("format") != 1 or m.get("app") != "Murmur" or not m.get("version") or not m.get("payload_sha256"):
        raise UpdateError("Unsupported update format.")
    return m


def read_package(path: str, pub_b64: str = PUBLIC_KEY_B64) -> dict:
    """Cheap check used for discovery: verifies the signed manifest only."""
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            if not {"manifest.json", "manifest.sig", "payload.zip"} <= names:
                raise UpdateError("Not a Murmur update package.")
            if z.getinfo("manifest.json").file_size > MAX_MANIFEST:
                raise UpdateError("Manifest too large.")
            manifest, sig = z.read("manifest.json"), z.read("manifest.sig")
    except zipfile.BadZipFile:
        raise UpdateError("Damaged or incomplete file.")
    m = _verify_manifest(manifest, sig, pub_b64)
    return {"path": path, "version": str(m["version"]), "notes": m.get("notes", ""),
            "size": int(m.get("payload_size", 0)), "created": m.get("created", "")}


def verify_and_extract(path: str, dest: str, pub_b64: str = PUBLIC_KEY_B64) -> dict:
    """Full verification (signature + payload hash), then safe extraction into `dest`."""
    info = read_package(path, pub_b64)
    with zipfile.ZipFile(path) as z:
        m = _verify_manifest(z.read("manifest.json"), z.read("manifest.sig"), pub_b64)
        h = hashlib.sha256()
        with z.open("payload.zip") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest() != m["payload_sha256"]:
            raise UpdateError("The update file is damaged or has been tampered with (hash mismatch).")
        os.makedirs(dest, exist_ok=True)
        payload_tmp = os.path.join(dest, "_payload.zip")
        with z.open("payload.zip") as src, open(payload_tmp, "wb") as out:
            for chunk in iter(lambda: src.read(1 << 20), b""):
                out.write(chunk)
    root = os.path.realpath(os.path.join(dest, "new"))
    os.makedirs(root, exist_ok=True)
    with zipfile.ZipFile(payload_tmp) as pz:
        for member in pz.infolist():
            target = os.path.realpath(os.path.join(root, member.filename))
            if not (target == root or target.startswith(root + os.sep)):
                raise UpdateError("Unsafe path inside update package.")      # zip-slip protection
        pz.extractall(root)
    os.remove(payload_tmp)
    if not os.path.exists(os.path.join(root, "Murmur.exe")):
        raise UpdateError("Update does not contain Murmur.exe.")
    return {**info, "staging": root}


def _removable_roots():
    roots = []
    mask = ctypes.windll.kernel32.GetLogicalDrives()
    for i in range(26):
        if mask & (1 << i):
            root = f"{chr(65 + i)}:\\"
            if ctypes.windll.kernel32.GetDriveTypeW(root) == 2:    # DRIVE_REMOVABLE (USB sticks, SD cards)
                roots.append(root)
    return roots


def candidate_files(extra_folder: str = ""):
    dirs = []
    for r in _removable_roots():
        murmur_dir = os.path.join(r, "Murmur")
        dirs += [r, murmur_dir]
        try:                                       # also one level of sub-folders, e.g. X:\Murmur\03_UPDATES
            dirs += [e.path for e in os.scandir(murmur_dir) if e.is_dir()]
        except OSError:
            pass
    if extra_folder:
        dirs.append(extra_folder)
    found = []
    for d in dirs:
        try:
            for fn in os.listdir(d):
                if fn.lower().endswith(EXT):
                    p = os.path.join(d, fn)
                    st = os.stat(p)
                    found.append((p, st.st_size, int(st.st_mtime)))
        except OSError:
            continue
    return found


class UpdateWatcher:
    def __init__(self, ctl):
        self.ctl = ctl
        self.available = None          # verified, newer-than-current update (dict) or None
        self.rejected = []             # [{"path","reason"}] shown to the user
        self.result = None             # outcome of the last install attempt (read once at startup)
        self.busy = False
        self.error = ""
        self._seen = {}
        self._lock = threading.Lock()
        self._read_result()
        threading.Thread(target=self._loop, daemon=True, name="updates").start()

    def _read_result(self):
        p = os.path.join(paths.data_dir(), "update-result.json")
        try:
            with open(p, "r", encoding="utf-8-sig") as f:
                self.result = json.load(f)
            os.remove(p)
            if self.result.get("status") == "ok":
                self.ctl.cfg.update({"last_update": str(self.result.get("version", ""))})
        except Exception:
            pass

    def _current(self):
        """Newest version we are known to be at (the app's own, or the last one the updater installed)."""
        last = self.ctl.cfg["last_update"]
        return max(vtuple(__version__), vtuple(last) if last else (0,))

    def dismiss_result(self):
        self.result = None

    def check_now(self):
        with self._lock:
            self._seen.clear()
            self.rejected = []
        self._scan()

    def _loop(self):
        while True:
            try:
                self._scan()
            except Exception:
                log.exception("update scan")
            time.sleep(4)

    def _scan(self):
        files = candidate_files(self.ctl.cfg["update_folder"])
        with self._lock:
            keys = {f"{p}|{s}|{m}" for p, s, m in files}
            self.rejected = [r for r in self.rejected if r["key"] in keys]
            if self.available and not os.path.exists(self.available["path"]):
                self.available = None               # stick was removed
            for p, s, m in files:
                key = f"{p}|{s}|{m}"
                if key in self._seen:
                    continue
                try:
                    info = read_package(p)
                    self._seen[key] = "ok"
                    if vtuple(info["version"]) > self._current():
                        if not self.available or vtuple(info["version"]) > vtuple(self.available["version"]):
                            self.available = info
                            self.ctl.on_update_found(info)
                    else:
                        self._seen[key] = "old"
                except UpdateError as e:
                    self._seen[key] = "bad"
                    self.rejected.append({"key": key, "path": p, "reason": str(e)})
                    log.warning("update rejected %s: %s", p, e)
                except Exception as e:
                    self._seen[key] = "bad"
                    self.rejected.append({"key": key, "path": p, "reason": f"{type(e).__name__}: {e}"})

    # ---- install ----
    def install(self):
        """Verify fully, stage, then hand over to a helper script that swaps files after we exit."""
        info = self.available
        if not info:
            raise UpdateError("No update available.")
        if not getattr(sys, "frozen", False):
            raise UpdateError("Updates can only be installed in the packaged app.")
        app_dir = os.path.dirname(sys.executable)
        try:
            probe = os.path.join(app_dir, ".write-test")
            open(probe, "w").close()
            os.remove(probe)
        except OSError:
            raise UpdateError("The Murmur folder is not writable. Move it somewhere you can write (not Program Files).")
        stage = tempfile.mkdtemp(prefix="murmur-update-")
        self.busy = True
        try:
            staged = verify_and_extract(info["path"], stage)
        except Exception:
            self.busy = False
            raise
        script = os.path.join(stage, "apply.ps1")
        with open(script, "w", encoding="utf-8") as f:
            f.write(APPLY_SCRIPT)
        result = os.path.join(paths.data_dir(), "update-result.json")
        backup = os.path.join(paths.data_dir(), "update-backup")
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
             "-File", script, "-OldPid", str(os.getpid()), "-App", app_dir, "-New", staged["staging"],
             "-Backup", backup, "-Result", result, "-Version", info["version"], "-Stage", stage],
            # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP: hidden, and not tied to this process. (Do NOT add
            # DETACHED_PROCESS: Windows ignores NO_WINDOW then and PowerShell dies without a console.)
            creationflags=0x08000000 | 0x00000200, close_fds=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return info["version"]


APPLY_SCRIPT = r'''
param($OldPid,$App,$New,$Backup,$Result,$Version,$Stage)
$ErrorActionPreference = "Continue"
function Done($status,$msg){ @{status=$status;version=$Version;message=$msg;time=(Get-Date).ToString("s")} | ConvertTo-Json | Set-Content -Path $Result -Encoding UTF8 }
try { Wait-Process -Id $OldPid -Timeout 90 -ErrorAction SilentlyContinue } catch {}
Start-Sleep -Seconds 2
if (Test-Path $Backup) { Remove-Item -Recurse -Force $Backup -ErrorAction SilentlyContinue }
robocopy $App $Backup /E /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { Done "failed" "Could not back up the current version; nothing was changed."; Start-Process "$App\Murmur.exe"; exit }
robocopy $New $App /E /IS /IT /R:3 /W:2 /NFL /NDL /NJH /NJS /NP | Out-Null
$rc = $LASTEXITCODE
if ($rc -ge 8 -or -not (Test-Path "$App\Murmur.exe")) {
  robocopy $Backup $App /E /IS /IT /R:3 /W:2 /NFL /NDL /NJH /NJS /NP | Out-Null
  Done "rolled_back" "Installing failed (code $rc); the previous version was restored."
} else { Done "ok" "Updated." }
Remove-Item -Recurse -Force $Stage -ErrorAction SilentlyContinue
Start-Process "$App\Murmur.exe" -ArgumentList "--show"
'''
