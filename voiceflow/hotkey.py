"""hotkey.py — Global keyboard shortcut listener.

Built on pynput.keyboard.Listener.  Supports:
  - A primary chord (e.g. "ctrl+shift+space") with press/release callbacks
    for push-to-talk recording.
  - A cancel key (default: Escape) to abort while the chord is held.
  - Extra chords (e.g. "ctrl+shift+r") for tap-style actions like re-paste.

The listener runs on its own thread; run() blocks the calling thread by
joining the listener so the main process stays alive.

Modifier handling: pynput delivers left/right variants inconsistently
across platforms, so _MOD_VARIANTS maps each generic modifier to all
its physical forms for reliable matching.
"""

from __future__ import annotations

from typing import Callable

from pynput import keyboard

# Map config token -> pynput Key (modifiers + common named keys).
# Plain printable characters are matched by KeyCode.from_char() at parse time.
_NAMED_KEYS: dict[str, keyboard.Key] = {
    "ctrl": keyboard.Key.ctrl,
    "control": keyboard.Key.ctrl,
    "shift": keyboard.Key.shift,
    "alt": keyboard.Key.alt,
    "cmd": keyboard.Key.cmd,
    "win": keyboard.Key.cmd,
    "meta": keyboard.Key.cmd,
    "space": keyboard.Key.space,
    "enter": keyboard.Key.enter,
    "tab": keyboard.Key.tab,
    "esc": keyboard.Key.esc,
    "escape": keyboard.Key.esc,
    "backspace": keyboard.Key.backspace,
    "delete": keyboard.Key.delete,
    "up": keyboard.Key.up,
    "down": keyboard.Key.down,
    "left": keyboard.Key.left,
    "right": keyboard.Key.right,
    "home": keyboard.Key.home,
    "end": keyboard.Key.end,
    "pageup": keyboard.Key.page_up,
    "pagedown": keyboard.Key.page_down,
}
for _i in range(1, 13):
    _NAMED_KEYS[f"f{_i}"] = getattr(keyboard.Key, f"f{_i}")

# Modifier key -> its left/right physical variants. pynput delivers the L/R
# variant on press but the generic Key on release (and vice versa, depending
# on platform), so we match either form.
_MOD_VARIANTS: dict[keyboard.Key, set] = {
    keyboard.Key.ctrl: {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r},
    keyboard.Key.shift: {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r},
    keyboard.Key.alt: {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr},
    keyboard.Key.cmd: {keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r},
}


def _parse_chord(chord: str) -> list:
    """Parse a chord string like 'ctrl+shift+space' into a list of pynput keys."""
    tokens = [t.strip().lower() for t in chord.split("+") if t.strip()]
    parsed = []
    for t in tokens:
        if t in _NAMED_KEYS:
            parsed.append(_NAMED_KEYS[t])
        elif len(t) == 1:
            parsed.append(keyboard.KeyCode.from_char(t))
        else:
            raise ValueError(f"Unknown hotkey token: {t!r}")
    return parsed


def _matches(target, pressed_set: set) -> bool:
    """True iff target key (or any of its modifier variants) is currently held."""
    if target in _MOD_VARIANTS:
        return bool(_MOD_VARIANTS[target] & pressed_set)
    return target in pressed_set


def run(
    chord: str,
    on_press: Callable[[], None],
    on_release: Callable[[], None],
    on_cancel: Callable[[], None] | None = None,
    cancel_key: str = "esc",
    extra_chords: dict[str, Callable[[], None]] | None = None,
) -> None:
    """Block on a pynput listener that fires on_press once when the chord is fully
    held, and on_release once when any chord key goes up after that.
    If *on_cancel* is provided, pressing *cancel_key* while armed aborts the
    recording and calls on_cancel instead of on_release.
    *extra_chords* maps chord strings (e.g. ``"ctrl+shift+r"``) to tap callbacks
    — they fire once on key-down when the full chord is held."""
    targets = _parse_chord(chord)
    cancel_target = _parse_chord(cancel_key)[0] if on_cancel else None

    # Parse extra chords (for re-paste etc.)
    extras: list[tuple[list, Callable[[], None]]] = []
    for ch, cb in (extra_chords or {}).items():
        extras.append((_parse_chord(ch), cb))

    held: set = set()
    armed = False  # True between full-chord press and corresponding release

    def fully_held() -> bool:
        return all(_matches(t, held) for t in targets)

    def _extra_matches() -> Callable[[], None] | None:
        for tgts, cb in extras:
            if all(_matches(t, held) for t in tgts):
                return cb
        return None

    def _on_press(key):
        nonlocal armed
        held.add(key)
        if armed and on_cancel and cancel_target is not None and _matches(cancel_target, {key}):
            armed = False
            try:
                on_cancel()
            except Exception as exc:  # noqa: BLE001
                print(f"[hotkey] on_cancel error: {exc}")
            return
        if not armed and fully_held():
            armed = True
            try:
                on_press()
            except Exception as exc:  # noqa: BLE001
                print(f"[hotkey] on_press error: {exc}")
            return
        # Check extra chords (tap-style, not hold)
        if not armed:
            extra_cb = _extra_matches()
            if extra_cb is not None:
                try:
                    extra_cb()
                except Exception as exc:  # noqa: BLE001
                    print(f"[hotkey] extra chord error: {exc}")

    def _on_release(key):
        nonlocal armed
        was_armed = armed
        held.discard(key)
        if was_armed and not fully_held():
            armed = False
            try:
                on_release()
            except Exception as exc:  # noqa: BLE001
                print(f"[hotkey] on_release error: {exc}")

    listener = keyboard.Listener(on_press=_on_press, on_release=_on_release)
    listener.start()
    return listener
