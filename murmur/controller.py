import logging
import os
import queue
import shutil
import sys
import threading
import time

from . import cleanup, i18n, models, netguard, paster, paths, postprocess, recorder
from .config import Config
from .hotkeys import HotkeyManager
from .overlay import Overlay
from .store import Store
from .transcriber import Transcriber

log = logging.getLogger("murmur")
TRASH_DAYS = 14


class Controller:
    def __init__(self):
        self.cfg = Config()
        self.store = Store()
        self.rec = recorder.Recorder()
        self.tr = Transcriber()
        self.overlay = Overlay(lambda: self.rec.level)
        _raw_set = self.overlay.set
        self.overlay.set = lambda st, msg="", hold=0.0: _raw_set(st, self.T(msg) if msg else msg, hold)
        self.jobs = queue.Queue()
        self.busy = 0
        self.paused = False
        self.lock = threading.RLock()
        self.show_ui = lambda: None      # set by app
        models.set_root(self.cfg["models_dir"])
        models.offline = lambda: bool(self.cfg["offline_mode"])
        netguard.install(lambda: bool(self.cfg["offline_mode"]))
        self.recovered = recorder.recover_orphans(self.store)
        self.hotkeys = HotkeyManager(self._on_press, self._on_release)
        self.hotkeys.set_combo(self.cfg["hotkey"])
        threading.Thread(target=self._worker, daemon=True, name="transcribe").start()
        threading.Thread(target=self._maintenance_loop, daemon=True, name="maint").start()
        if models.is_ready(self.cfg["model"]):
            threading.Thread(target=self._warm_and_resume, daemon=True).start()

    @property
    def lang(self):
        return i18n.resolve(self.cfg["ui_language"])

    def T(self, msg):
        return i18n.t(msg, self.lang)

    # ---------- state exposed to UI / tray ----------
    @property
    def state(self):
        if self.paused:
            return "paused"
        if self.rec.active:
            return "listening"
        if self.busy:
            return "thinking"
        return "idle"

    # ---------- hotkey handlers ----------
    def _on_press(self):
        with self.lock:
            if self.paused:
                return
            if self.cfg["mode"] == "toggle" and self.rec.active:
                self.stop_recording()
            elif not self.rec.active:
                self.start_recording()

    def _on_release(self):
        if self.cfg["mode"] == "hold" and self.rec.active:
            with self.lock:
                self.stop_recording()

    def _beep(self, hi):
        if self.cfg["sounds"]:
            import winsound
            threading.Thread(target=lambda: winsound.Beep(900 if hi else 640, 45), daemon=True).start()

    def start_recording(self):
        if not models.is_ready(self.cfg["model"]):
            self.overlay.set("error", "Pick a model first", 3)
            self.show_ui()
            return
        try:
            rid = self.rec.start(self.cfg["mic"])
        except Exception as e:
            log.exception("mic open failed")
            self.overlay.set("error", "Mic problem", 3)
            return
        self.store.create(rid, self.rec.path, "recording")
        self.overlay.set("listening")
        self._beep(True)

    def stop_recording(self):
        rid = self.rec.rid
        try:
            path, dur = self.rec.stop()
        except Exception:
            log.exception("stop failed")
            self.overlay.set("error", "Recording error", 3)
            return
        self._beep(False)
        if dur < 0.3:               # an accidental tap, not speech
            try:
                os.remove(path)
            except OSError:
                pass
            self.store.delete(rid)
            self.overlay.set("hidden")
            return
        self.store.update(rid, status="pending", path=path, duration=dur)
        self._enqueue(rid, paste=True)

    # ---------- transcription ----------
    def _enqueue(self, rid, paste):
        with self.lock:
            self.busy += 1
        self.overlay.set("thinking")
        self.jobs.put((rid, paste))

    def retry(self, rid):
        row = self.store.get(rid)
        if row and row["path"] and os.path.exists(row["path"]):
            self.store.update(rid, status="pending", error="")
            self._enqueue(rid, paste=False)

    def _worker(self):
        while True:
            rid, do_paste = self.jobs.get()
            try:
                self._process(rid, do_paste)
            except Exception:
                log.exception("job crashed")
            finally:
                with self.lock:
                    self.busy -= 1
                    if not self.rec.active and self.busy == 0 and self.overlay.state == "thinking":
                        self.overlay.set("hidden")

    def _process(self, rid, do_paste):
        row = self.store.get(rid)
        if not row or not row["path"] or not os.path.exists(row["path"]):
            return
        self.store.update(rid, status="transcribing")
        cfg = self.cfg
        try:
            raw, lang = self.tr.transcribe(row["path"], cfg["model"], cfg["language"], cfg["terms"])
            final = postprocess.apply(raw, cfg)
            if final and cfg["llm_cleanup"] and cfg["llm_model"]:
                final = cleanup.polish(final, cfg["llm_model"])
        except Exception as e:
            log.exception("transcription failed")
            self.store.update(rid, status="failed", error=f"{type(e).__name__}: {e}")
            self.overlay.set("error", "Saved audio, retry later", 3.5)
            return
        status = "done" if final else "empty"
        self.store.update(rid, status=status, text=final, raw=raw, lang=lang, model=cfg["model"], error="")
        if not final:
            self.overlay.set("error", "Heard nothing", 2.5)
            return
        if do_paste and cfg["auto_paste"]:
            try:
                paster.paste(final, cfg["restore_clipboard"], self.hotkeys)
                if self.busy <= 1 and not self.rec.active:
                    self.overlay.set("done", "Pasted!", 1.2)
            except Exception as e:
                log.exception("paste failed")
                self.store.update(rid, error=f"Paste failed: {e}")
                self.overlay.set("error", "Paste failed, see History", 3.5)
        elif self.busy <= 1 and not self.rec.active:
            self.overlay.set("done", "Done", 1.2)

    def _warm_and_resume(self):
        self.tr.preload(self.cfg["model"])
        # Anything recovered or left pending is transcribed quietly into History (never pasted).
        for row in self.store.by_status("pending", "failed"):
            if row["path"] and os.path.exists(row["path"]) and row["status"] == "pending":
                self._enqueue(row["id"], paste=False)

    # ---------- config side effects ----------
    def apply_config(self, changes):
        old_model = self.cfg["model"]
        self.cfg.update(changes)
        if "models_dir" in changes:
            models.set_root(self.cfg["models_dir"])
            if models.is_ready(self.cfg["model"]):
                threading.Thread(target=self.tr.preload, args=(self.cfg["model"],), daemon=True).start()
        if "hotkey" in changes:
            self.hotkeys.set_combo(self.cfg["hotkey"])
        if "autostart" in changes:
            self._set_autostart(self.cfg["autostart"])
        if "model" in changes and changes["model"] != old_model and models.is_ready(changes["model"]):
            threading.Thread(target=self.tr.preload, args=(changes["model"],), daemon=True).start()

    def _set_autostart(self, on):
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        try:
            if on:
                exe = sys.executable if getattr(sys, "frozen", False) else f'"{sys.executable}" -m murmur'
                winreg.SetValueEx(key, "Murmur", 0, winreg.REG_SZ, exe + " --background")
            else:
                try:
                    winreg.DeleteValue(key, "Murmur")
                except FileNotFoundError:
                    pass
        finally:
            winreg.CloseKey(key)

    # ---------- history actions (nothing is hard-deleted by the UI) ----------
    def trash(self, rid):
        row = self.store.get(rid)
        if not row:
            return
        tp = ""
        if row["path"] and os.path.exists(row["path"]):
            tp = os.path.join(paths.trash_dir(), os.path.basename(row["path"]))
            shutil.move(row["path"], tp)
        self.store.update(rid, trashed=1, trashed_at=time.time(), trash_path=tp, path="")

    def restore(self, rid):
        row = self.store.get(rid)
        if not row:
            return
        p = row["path"]
        if row["trash_path"] and os.path.exists(row["trash_path"]):
            p = recorder.move_to_saved(row["trash_path"], rid)
        self.store.update(rid, trashed=0, trashed_at=0, trash_path="", path=p)

    def maintenance(self):
        days = self.cfg["retention_days"]
        if days and days > 0:
            for row in self.store.expired_candidates(time.time() - days * 86400):
                if row["path"] and os.path.exists(row["path"]):
                    tp = os.path.join(paths.trash_dir(), os.path.basename(row["path"]))
                    shutil.move(row["path"], tp)
                    self.store.update(row["id"], path="", trash_path=tp, trashed_at=time.time(),
                                      note="Audio expired (text kept)")
        for row in self.store.purgeable(time.time() - TRASH_DAYS * 86400):
            try:
                if row["trash_path"] and os.path.exists(row["trash_path"]):
                    os.remove(row["trash_path"])
            except OSError:
                continue
            if row["trashed"]:
                self.store.delete(row["id"])
            else:
                self.store.update(row["id"], trash_path="")

    def _maintenance_loop(self):
        while True:
            try:
                self.maintenance()
            except Exception:
                log.exception("maintenance")
            time.sleep(3600)
