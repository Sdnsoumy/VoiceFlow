"""paster.py — Clipboard and auto-paste operations.

After transcription (and optional LLM refinement), the final text is
placed on the clipboard and pasted at the cursor position via a
simulated Ctrl+V / Cmd+V keystroke.

Typing mode:  For apps that intercept Ctrl+V (e.g. terminals), text is
typed character-by-character with pyautogui.  Non-ASCII text falls back
to clipboard paste since pyautogui.typewrite() only handles ASCII.

Thread safety: _last_text is protected by _lock since paste() runs on
the pipeline thread while repaste() can fire from the hotkey thread.
"""

from __future__ import annotations

import platform
import threading
import time

import pyautogui
import pyperclip

_last_text: str = ""        # Most recent pasted text (for re-paste)
_lock = threading.Lock()     # Guards _last_text across threads

# macOS uses Cmd+V, everything else uses Ctrl+V
_PASTE_MOD = "command" if platform.system() == "Darwin" else "ctrl"


def _type_or_paste(text: str) -> None:
    """Type text character-by-character if ASCII, otherwise fall back to
    clipboard-based paste (pyautogui.typewrite only supports ASCII)."""
    if text.isascii():
        pyautogui.typewrite(text, interval=0.01)
    else:
        # Non-ASCII: clipboard paste is the only reliable method
        pyperclip.copy(text)
        pyautogui.hotkey(_PASTE_MOD, "v")


def paste(text: str, auto_paste: bool = True, typing_mode: bool = False) -> None:
    """Copy text to clipboard and optionally paste it at the cursor.

    Args:
        text: The text to paste.
        auto_paste: If True, simulate a Ctrl+V / Cmd+V keystroke.
        typing_mode: If True, type characters individually instead of pasting.
    """
    global _last_text
    if not text or not text.strip():
        return
    with _lock:
        _last_text = text
    pyperclip.copy(text)
    if auto_paste:
        time.sleep(0.05)
        if typing_mode:
            _type_or_paste(text)
        else:
            pyautogui.hotkey(_PASTE_MOD, "v")


def repaste(typing_mode: bool = False) -> bool:
    """Re-paste the last transcribed text. Returns True if something was pasted."""
    with _lock:
        text = _last_text
    if not text:
        return False
    pyperclip.copy(text)
    time.sleep(0.05)
    if typing_mode:
        _type_or_paste(text)
    else:
        pyautogui.hotkey(_PASTE_MOD, "v")
    return True


def get_last() -> str:
    with _lock:
        return _last_text


def apply_clipboard_template(prompt: str) -> str:
    """Replace ``{clipboard}`` placeholders in a prompt with the current
    clipboard content.  Returns the prompt unchanged if no placeholder exists."""
    if "{clipboard}" not in prompt:
        return prompt
    try:
        clip = pyperclip.paste() or ""
    except Exception:  # noqa: BLE001
        clip = ""
    return prompt.replace("{clipboard}", clip)




