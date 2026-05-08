"""transcriber.py — Speech-to-text via OpenAI Whisper.

Lazy-loads the Whisper model on first use (download can take 30+ seconds).
Thread-safe: double-checked locking prevents two threads from loading
the model simultaneously.
"""

from __future__ import annotations

import threading

import numpy as np


class Transcriber:
    """Wraps Whisper's transcribe() in a thread-safe, lazy-loaded interface.

    The model is downloaded and loaded on the first call to transcribe().
    Call reload_model() to switch models (takes effect on the next call).
    """

    def __init__(self, model_name: str = "base") -> None:
        self.model_name = model_name
        self._model = None
        self._load_lock = threading.Lock()

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        with self._load_lock:
            # Double-checked locking: another thread may have loaded while we waited
            if self._model is not None:
                return
            import whisper

            print(f"[transcriber] loading whisper model '{self.model_name}' (first run downloads it)...")
            self._model = whisper.load_model(self.model_name)
            print("[transcriber] model ready")

    def reload_model(self, model_name: str) -> None:
        """Schedule a lazy reload of the Whisper model on the next transcription."""
        with self._load_lock:
            self.model_name = model_name
            self._model = None

    def transcribe(self, audio: np.ndarray, language: str | None = "en") -> str:
        """Transcribe a float32 audio array to text.

        Pass language="auto" or None to let Whisper auto-detect the language.
        Returns an empty string for empty audio.
        """
        if audio.size == 0:
            return ""
        self._ensure_loaded()
        # "auto" / "" / None -> let Whisper auto-detect
        lang = language if language and language.lower() != "auto" else None
        result = self._model.transcribe(audio, language=lang, fp16=False)
        return (result.get("text") or "").strip()

