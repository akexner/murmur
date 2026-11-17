import os
import threading

from . import models, recorder


class Transcriber:
    def __init__(self):
        self._model = None
        self._name = None
        self._lock = threading.Lock()

    def _ensure(self, name):
        if self._name == name and self._model is not None:
            return
        if not models.is_ready(name):
            raise RuntimeError(f"Model '{name}' is not downloaded yet")
        from faster_whisper import WhisperModel
        self._model = WhisperModel(models.model_path(name), device="cpu", compute_type="int8",
                                   cpu_threads=max(2, (os.cpu_count() or 4) - 1))
        self._name = name

    def preload(self, name):
        with self._lock:
            try:
                self._ensure(name)
            except Exception:
                pass

    def transcribe(self, wav_path, model, language="auto", terms=None):
        samples = recorder.read_samples(wav_path)
        if len(samples) < 1600:
            return "", ""
        prompt = None
        if terms:
            prompt = "Glossary: " + ", ".join(terms)[:400] + "."
        with self._lock:
            self._ensure(model)
            segs, info = self._model.transcribe(
                samples, language=None if language in ("auto", "", None) else language,
                beam_size=3, vad_filter=True, condition_on_previous_text=False,
                initial_prompt=prompt)
            text = " ".join(s.text.strip() for s in segs).strip()
        return text, info.language
