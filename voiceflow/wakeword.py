"""Continuous wake-word listener built on `openwakeword` (optional dep).

`openwakeword` is **not** in the base requirements — install it separately:
    pip install openwakeword onnxruntime
and on first run it will download the small ONNX models (~few MB).

Built-in keyword choices include `alexa`, `hey_jarvis`, `hey_mycroft`. There's
no prebuilt "voice flow" model — point `wake_word_model` at a custom .onnx if
you have one, otherwise pick from the bundled list (default: `hey_jarvis`).
"""

from __future__ import annotations

import threading
import time
from typing import Callable

import numpy as np
import sounddevice as sd

CHUNK_SAMPLES = 1280  # 80 ms at 16 kHz, the canonical openwakeword chunk size
SAMPLE_RATE = 16_000


class WakeWordListener:
    def __init__(
        self,
        model: str,
        on_detect: Callable[[], None],
        threshold: float = 0.5,
        cooldown_secs: float = 2.0,
    ) -> None:
        self.model = model
        self.on_detect = on_detect
        self.threshold = threshold
        self.cooldown_secs = cooldown_secs
        self._stop_evt = threading.Event()
        self._thread: threading.Thread | None = None
        self._stream: sd.InputStream | None = None
        self._oww = None
        self._last_fire = 0.0

    def _load_model(self):
        try:
            from openwakeword.model import Model  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "openwakeword not installed. Run `pip install openwakeword onnxruntime`."
            ) from exc

        # `wakeword_models` accepts a bundled name (e.g. 'hey_jarvis') or a path
        # to a custom .onnx model.
        return Model(wakeword_models=[self.model])

    def _run(self) -> None:
        try:
            self._oww = self._load_model()
        except Exception as exc:  # noqa: BLE001
            print(f"[wakeword] disabled: {exc}")
            return

        print(f"[wakeword] listening for {self.model!r} (threshold={self.threshold})")

        def callback(indata, _frames, _time_info, status) -> None:
            if status:
                print(f"[wakeword] stream status: {status}")
            if self._stop_evt.is_set():
                return
            # openwakeword expects int16 PCM
            samples = (indata[:, 0] * 32767.0).astype(np.int16)
            try:
                scores = self._oww.predict(samples)
            except Exception as exc:  # noqa: BLE001
                print(f"[wakeword] predict failed: {exc}")
                return
            for _name, score in scores.items():
                if score >= self.threshold:
                    now = time.monotonic()
                    if now - self._last_fire < self.cooldown_secs:
                        return
                    self._last_fire = now
                    print(f"[wakeword] detected (score={score:.2f})")
                    try:
                        self.on_detect()
                    except Exception as exc:  # noqa: BLE001
                        print(f"[wakeword] on_detect error: {exc}")
                    return

        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=CHUNK_SAMPLES,
                callback=callback,
            )
            self._stream.start()
            while not self._stop_evt.wait(0.1):
                pass
        except Exception as exc:  # noqa: BLE001
            print(f"[wakeword] stream error: {exc}")
        finally:
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:  # noqa: BLE001
                    pass
                self._stream = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._run, name="voiceflow-wake", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_evt.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

