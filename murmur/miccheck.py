"""3-second microphone check with a live level meter and a plain verdict."""
import math
import threading
import time

import numpy as np
import sounddevice as sd

SR = 16000


class MicCheck:
    def __init__(self):
        self.state = {"running": False, "level": 0.0, "verdict": "", "peak_db": None, "rms_db": None,
                      "error": "", "seconds_left": 0.0, "has_audio": False}
        self._buf = None
        self._lock = threading.Lock()

    def snapshot(self):
        with self._lock:
            return dict(self.state)

    def start(self, device, seconds=3.0):
        with self._lock:
            if self.state["running"]:
                return
            self.state.update(running=True, level=0.0, verdict="", peak_db=None, rms_db=None, error="",
                              seconds_left=seconds, has_audio=False)
        threading.Thread(target=self._run, args=(device, seconds), daemon=True, name="micheck").start()

    def _run(self, device, seconds):
        chunks = []

        def cb(indata, frames, t, status):
            x = indata[:, 0].astype(np.float32) / 32768.0
            chunks.append(x.copy())
            with self._lock:
                self.state["level"] = float(np.sqrt(np.mean(x * x))) if len(x) else 0.0

        try:
            with sd.InputStream(samplerate=SR, channels=1, dtype="int16", device=device, blocksize=1600, callback=cb):
                end = time.time() + seconds
                while time.time() < end:
                    with self._lock:
                        self.state["seconds_left"] = round(end - time.time(), 1)
                    time.sleep(0.1)
        except Exception as e:
            with self._lock:
                self.state.update(running=False, error=f"{type(e).__name__}: {e}", verdict="error")
            return
        x = np.concatenate(chunks) if chunks else np.zeros(1, dtype=np.float32)
        peak = float(np.max(np.abs(x))) or 1e-9
        rms = float(np.sqrt(np.mean(x * x))) or 1e-9
        peak_db, rms_db = 20 * math.log10(peak), 20 * math.log10(rms)
        if peak_db >= -1.0:
            verdict = "clipping"
        elif rms_db < -60:
            verdict = "silent"
        elif rms_db < -42:
            verdict = "quiet"
        elif rms_db > -12:
            verdict = "loud"
        else:
            verdict = "good"
        with self._lock:
            self._buf = (x * 32767).astype(np.int16)
            self.state.update(running=False, level=0.0, verdict=verdict, peak_db=round(peak_db, 1),
                              rms_db=round(rms_db, 1), seconds_left=0.0, has_audio=True)

    def play(self):
        with self._lock:
            buf = self._buf
        if buf is not None:
            sd.play(buf, SR)
