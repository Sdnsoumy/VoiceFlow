"""recorder.py — Microphone audio capture.

Uses sounddevice (PortAudio) to stream 16 kHz mono float32 audio.
The Recorder class is designed for push-to-talk: call start() when the
user presses the hotkey, stop() when they release.  Audio frames are
collected in a list and concatenated into a single NumPy array on stop().

An RMS-based level is computed in the audio callback and pushed into
a queue that the waveform visualizer reads from.

auto_stop_on_silence() is used for wake-word mode: it watches the
recorder and auto-stops after a configurable period of silence.
"""

from __future__ import annotations

import queue
import threading
import time

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16_000    # Whisper expects 16 kHz audio
CHANNELS = 1            # Mono recording
DTYPE = "float32"       # 32-bit float samples
VOICE_THRESHOLD = 0.05  # RMS level above this counts as voice activity


class Recorder:
    """Push-to-talk audio recorder.

    Thread safety: _lock protects _frames and _stream.  The sounddevice
    callback runs on a PortAudio thread and appends to _frames under the
    lock (short hold — just a list append).
    """

    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        self.sample_rate = sample_rate
        self._stream: sd.InputStream | None = None
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self.levels: queue.Queue[float] = queue.Queue(maxsize=256)
        self.last_voice_at: float = 0.0
        self.started_at: float = 0.0

    def _callback(self, indata, frames, time_info, status) -> None:
        """Sounddevice audio callback — runs on the PortAudio thread.

        Appends raw audio to _frames (under lock) and computes an RMS
        level that gets pushed to self.levels for the waveform display.
        """
        if status:
            print(f"[recorder] stream status: {status}")
        chunk = indata.copy()
        with self._lock:
            self._frames.append(chunk)
        try:
            rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
            level = min(1.0, rms * 4.0)
            if level > VOICE_THRESHOLD:
                self.last_voice_at = time.monotonic()
            if self.levels.full():
                try:
                    self.levels.get_nowait()
                except queue.Empty:
                    pass
            self.levels.put_nowait(level)
        except Exception:  # noqa: BLE001
            pass

    def start(self) -> None:
        """Open the mic stream and begin capturing.  No-op if already recording."""
        with self._lock:
            if self._stream is not None:
                return
            self._frames = []
            # Drain the level queue (avoid private .mutex/.queue internals)
            while not self.levels.empty():
                try:
                    self.levels.get_nowait()
                except queue.Empty:
                    break
            now = time.monotonic()
            self.started_at = now
            self.last_voice_at = now
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=CHANNELS,
                dtype=DTYPE,
                callback=self._callback,
            )
            self._stream.start()

    def stop(self) -> np.ndarray:
        """Stop recording and return the captured audio as a flat float32 array.

        Returns a zero-length array if nothing was recorded.
        """
        with self._lock:
            if self._stream is None:
                return np.zeros(0, dtype=np.float32)
            self._stream.stop()
            self._stream.close()
            self._stream = None
            frames = self._frames
            self._frames = []
        if not frames:
            return np.zeros(0, dtype=np.float32)
        audio = np.concatenate(frames, axis=0).flatten().astype(np.float32)
        return audio

    def is_running(self) -> bool:
        return self._stream is not None


def auto_stop_on_silence(
    recorder: Recorder,
    on_done,
    silence_secs: float = 1.2,
    min_secs: float = 0.6,
    max_secs: float = 12.0,
) -> threading.Thread:
    """Watch the given recorder and stop it once `silence_secs` of silence has
    elapsed (after at least `min_secs`), or after `max_secs`. Calls
    `on_done(audio_np)` from this watcher thread. Recorder must already be started."""

    def _watch() -> None:
        while True:
            time.sleep(0.05)
            if not recorder.is_running():
                # Recorder was stopped externally; still call on_done so
                # callers can release resources (e.g. pipeline_lock).
                try:
                    on_done(np.zeros(0, dtype=np.float32))
                except Exception as exc:  # noqa: BLE001
                    print(f"[recorder] auto-stop on_done error: {exc}")
                return
            now = time.monotonic()
            elapsed = now - recorder.started_at
            silent_for = now - recorder.last_voice_at
            if elapsed >= max_secs:
                break
            if elapsed >= min_secs and silent_for >= silence_secs:
                break
        audio = recorder.stop()
        try:
            on_done(audio)
        except Exception as exc:  # noqa: BLE001
            print(f"[recorder] auto-stop on_done error: {exc}")

    t = threading.Thread(target=_watch, name="voiceflow-vad", daemon=True)
    t.start()
    return t
