"""history.py — Persistent transcription history stored as JSONL.

Each line in the history file is a JSON object with fields:
  ts       — ISO timestamp
  text     — raw Whisper transcript
  refined  — LLM-refined version (may equal text)
  fav      — boolean favourite flag

Thread safety: all disk I/O is serialized through _file_lock to avoid
corrupt writes when multiple pipeline threads finish simultaneously.

Performance: load() uses a tail-read optimization for large files,
reading backwards in 8 KB chunks so only the last N entries are parsed.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

# Store history alongside the executable / script
HISTORY_PATH = Path(__file__).resolve().parent / "history.jsonl"

_file_lock = threading.Lock()  # Serialises all file I/O


def append(text: str, refined: str | None = None) -> None:
    if not text or not text.strip():
        return
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "text": text,
        "fav": False,
    }
    if refined is not None and refined != text:
        entry["refined"] = refined
    with _file_lock:
        with HISTORY_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load(limit: int = 200) -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    file_size = HISTORY_PATH.stat().st_size
    if file_size == 0:
        return []

    # For small files (< 16 KB) or very large limits, just read everything
    if file_size < 16_384 or limit >= 50_000:
        lines = HISTORY_PATH.read_text(encoding="utf-8").splitlines()
        tail = lines[-limit:] if limit < len(lines) else lines
    else:
        # Read backwards in chunks to find the last *limit* lines
        chunk_size = 8192
        tail_lines: list[str] = []
        with HISTORY_PATH.open("rb") as f:
            f.seek(0, 2)  # seek to end
            remaining = f.tell()
            while remaining > 0 and len(tail_lines) <= limit:
                read_size = min(chunk_size, remaining)
                remaining -= read_size
                f.seek(remaining)
                chunk = f.read(read_size).decode("utf-8", errors="replace")
                tail_lines = chunk.splitlines() + tail_lines
        tail = tail_lines[-limit:]

    out: list[dict] = []
    for line in tail:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def search(query: str, limit: int = 200) -> list[dict]:
    """Return entries whose text or refined text contains *query* (case-insensitive)."""
    q = query.lower()
    return [
        e for e in load(limit)
        if q in (e.get("text") or "").lower() or q in (e.get("refined") or "").lower()
    ]


def toggle_favorite(ts: str) -> None:
    """Toggle the 'fav' flag on the entry with the given timestamp, then
    rewrite the file.  If called on a non-existent ts, it's a no-op."""
    with _file_lock:
        if not HISTORY_PATH.exists():
            return
        lines = HISTORY_PATH.read_text(encoding="utf-8").splitlines()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                new_lines.append(line)
                continue
            try:
                entry = json.loads(stripped)
            except json.JSONDecodeError:
                new_lines.append(line)
                continue
            if entry.get("ts") == ts:
                entry["fav"] = not entry.get("fav", False)
                new_lines.append(json.dumps(entry, ensure_ascii=False))
            else:
                # Copy unchanged lines as-is (avoid re-serializing every line)
                new_lines.append(stripped)
        HISTORY_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def clear() -> None:
    if HISTORY_PATH.exists():
        HISTORY_PATH.unlink()

