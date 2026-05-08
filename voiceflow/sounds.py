
"""Cross-platform audio feedback beeps.  Uses winsound on Windows (built-in),
falls back to a no-op on other platforms.  No external dependencies."""

from __future__ import annotations

import sys
import threading


def _beep(freq: int, duration_ms: int) -> None:
    if sys.platform == "win32":
        try:
            import winsound
            winsound.Beep(freq, duration_ms)
        except (ImportError, OSError):
            pass


def _play(freq: int, duration_ms: int) -> None:
    threading.Thread(target=_beep, args=(freq, duration_ms), daemon=True).start()


"""sounds.py — Audio feedback beeps.

Plays short beep tones via Windows' built-in winsound module to give
the user audible cues for record-start, record-stop, cancel, and paste.
Silently does nothing on non-Windows platforms or if winsound is unavailable.
"""

def on_record_start() -> None:
    """High-pitched beep (880 Hz) indicating recording has started."""
    _play(880, 120)


def on_record_stop() -> None:
    """Mid-tone beep (660 Hz) indicating recording has stopped."""
    _play(660, 120)


def on_cancel() -> None:
    """Low-tone beep (330 Hz) indicating the recording was cancelled."""
    _play(330, 200)


def on_paste() -> None:
    """Short high beep (1100 Hz) confirming text was pasted."""
    _play(1100, 60)
