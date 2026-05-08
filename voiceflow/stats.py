"""stats.py — Session and lifetime statistics.

Tracks cumulative counts (sessions, words, characters) in a small JSON
file.  An in-memory cache avoids re-reading the file on every tray-menu
update.  All access is guarded by a threading lock for safety.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

# Persist stats alongside the executable / script
STATS_PATH = Path(__file__).resolve().parent / "stats.json"

_DEFAULTS = {
    "total_sessions": 0,
    "total_words": 0,
    "total_chars": 0,
}

_lock = threading.Lock()       # Guards _cache and all file I/O
_cache: dict | None = None     # In-memory copy of stats.json


def _load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    if STATS_PATH.exists():
        try:
            _cache = json.loads(STATS_PATH.read_text(encoding="utf-8"))
            return _cache
        except (json.JSONDecodeError, OSError):
            pass
    _cache = dict(_DEFAULTS)
    return _cache


def _save(data: dict) -> None:
    global _cache
    _cache = data
    STATS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def record(text: str) -> None:
    if not text:
        return
    with _lock:
        data = _load()
        data["total_sessions"] = data.get("total_sessions", 0) + 1
        words = len(text.split())
        data["total_words"] = data.get("total_words", 0) + words
        data["total_chars"] = data.get("total_chars", 0) + len(text)
        _save(data)


def get() -> dict:
    with _lock:
        return dict(_load())


def reset() -> None:
    with _lock:
        _save(dict(_DEFAULTS))

