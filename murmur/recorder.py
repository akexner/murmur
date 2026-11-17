"""Crash-safe recorder.

Audio is streamed straight to a WAV file in recordings/in-progress while you speak.
The WAV header is rewritten (and fsynced) about once a second, so if the app, the
transcription engine or the whole PC dies mid-recording, the file is still a valid,
playable WAV. On next launch `recover_orphans` rescues anything left in in-progress.
"""
import os
import queue
import struct
import threading
import time
import uuid

import numpy as np
import sounddevice as sd

from . import paths

SR = 16000
HEADER = 44


def wav_header(nbytes: int) -> bytes:
    return struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + nbytes, b"WAVE", b"fmt ", 16, 1, 1,
                       SR, SR * 2, 2, 16, b"data", nbytes)


def fix_header(path: str) -> float:
    """Repair a WAV header from the real file size. Returns duration in seconds."""
    size = os.path.getsize(path)
    n = max(0, size - HEADER)
    n -= n % 2
    with open(path, "r+b") as f:
        if size < HEADER:
            f.write(wav_header(0))
            return 0.0
        f.seek(0)
        f.write(wav_header(n))
        f.flush()
        os.fsync(f.fileno())
    return n / 2 / SR


def read_samples(path: str) -> np.ndarray:
    with open(path, "rb") as f:
        f.seek(HEADER)
        raw = f.read()
    raw = raw[: len(raw) - (len(raw) % 2)]
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def move_to_saved(path: str, rid: str) -> str:
    dest_dir = os.path.join(paths.saved_dir(), time.strftime("%Y-%m"))
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, rid + ".wav")
    os.replace(path, dest)
    return dest


class Recorder:
    def __init__(self):
        self.active = False
        self.level = 0.0
        self.rid = None
        self.path = None
        self._stream = None
        self._q = None
        self._thread = None
        self._file = None
        self._bytes = 0
        self._src_rate = SR
        self._error = None

    # -- capture ---------------------------------------------------------
    def start(self, device=None) -> str:
        if self.active:
            raise RuntimeError("already recording")
        rid = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
        path = os.path.join(paths.inprogress_dir(), rid + ".wav")
        f = open(path, "wb")
        f.write(wav_header(0))
        f.flush()
        self._q = queue.Queue()
        self._bytes = 0
        self._error = None
        try:
            self._stream, self._src_rate = self._open_stream(device)
        except Exception:
            f.close()
            os.remove(path)
            raise
        self._file, self.rid, self.path, self.active = f, rid, path, True
        self._thread = threading.Thread(target=self._writer, daemon=True, name="rec-writer")
        self._thread.start()
        self._stream.start()
        return rid

    def _open_stream(self, device):
        def cb(indata, frames, t, status):
            data = indata[:, 0]
            self.level = float(np.sqrt(np.mean(np.square(data.astype(np.float32) / 32768.0)))) if len(data) else 0.0
            self._q.put(data.copy())

        try:
            s = sd.InputStream(samplerate=SR, channels=1, dtype="int16", device=device,
                               blocksize=1600, callback=cb)
            return s, SR
        except Exception:
            info = sd.query_devices(device, "input")
            rate = int(info["default_samplerate"])
            s = sd.InputStream(samplerate=rate, channels=1, dtype="int16", device=device,
                               blocksize=int(rate / 10), callback=cb)
            return s, rate

    def _writer(self):
        last_patch = time.time()
        f = self._file
        while True:
            try:
                chunk = self._q.get(timeout=0.5)
            except queue.Empty:
                chunk = None
            if chunk is None:
                if not self.active and self._q.empty():
                    break
            else:
                if self._src_rate != SR:
                    n = int(len(chunk) * SR / self._src_rate)
                    chunk = np.interp(np.linspace(0, len(chunk) - 1, max(n, 1)),
                                      np.arange(len(chunk)), chunk).astype(np.int16)
                try:
                    f.write(chunk.tobytes())
                    self._bytes += len(chunk) * 2
                except Exception as e:  # disk full etc.: keep what we have
                    self._error = e
            if time.time() - last_patch >= 1.0:
                self._patch(f)
                last_patch = time.time()
        self._patch(f)

    def _patch(self, f):
        try:
            f.flush()
            pos = f.tell()
            f.seek(0)
            f.write(wav_header(self._bytes))
            f.seek(pos)
            f.flush()
            os.fsync(f.fileno())
        except Exception as e:
            self._error = e

    def stop(self):
        """Finish the recording. Returns (saved_path, duration_s). The file is kept either way."""
        if not self.active:
            raise RuntimeError("not recording")
        try:
            self._stream.stop()
            self._stream.close()
        finally:
            self.active = False
        self._thread.join(timeout=5)
        self._file.close()
        self.level = 0.0
        dur = self._bytes / 2 / SR
        saved = move_to_saved(self.path, self.rid)
        return saved, dur

    def discard_tiny(self, path):
        try:
            os.remove(path)
        except OSError:
            pass


def recover_orphans(store):
    """Rescue recordings interrupted by a crash or power loss. Never deletes audio."""
    n = 0
    folder = paths.inprogress_dir()
    for name in os.listdir(folder):
        if not name.lower().endswith(".wav"):
            continue
        p = os.path.join(folder, name)
        rid = name[:-4]
        try:
            dur = fix_header(p)
            if dur < 0.05 and os.path.getsize(p) <= HEADER:
                os.remove(p)  # nothing but a header: no audio to lose
                store.delete(rid)
                continue
            dest = move_to_saved(p, rid)
            if store.get(rid):
                store.update(rid, path=dest, duration=dur, status="pending",
                             note="Recovered after an interruption")
            else:
                store.create(rid, dest, "pending")
                store.update(rid, duration=dur, note="Recovered after an interruption")
            n += 1
        except Exception:
            pass  # leave the file where it is; try again next launch
    # Rows stuck mid-flight (app died during transcription) go back to pending.
    for row in store.by_status("recording", "transcribing"):
        if row["path"] and os.path.exists(row["path"]):
            store.update(row["id"], status="pending")
    return n
