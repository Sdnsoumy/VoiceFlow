"""gui/tray.py — System-tray icon and context menu.

Builds a pystray Icon with a dynamic right-click menu containing:
  - Status indicator (Idle / Recording / Processing)
  - Task profile and refinement-mode submenus
  - Language selector
  - Quick toggles (LLM, sound feedback, context-aware, wake word, startup)
  - Session statistics
  - Settings, History, Reload, Quit

Menu updates are throttled to avoid UI flicker during rapid state changes.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

import pystray
from PIL import Image, ImageDraw

from modes import list_modes, list_task_profiles
import startup as startup_mgr
import stats as stats_store

# Path to the tray icon image (falls back to a generated icon)
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ICON_PATH = ASSETS_DIR / "icon.png"

QUICK_LANGS = ("auto", "en", "es", "fr", "de", "ja", "zh", "hi")


def _load_or_make_icon() -> Image.Image:
    """Load icon.png from assets, or generate a simple microphone icon."""
    if ICON_PATH.exists():
        try:
            return Image.open(ICON_PATH)
        except Exception:  # noqa: BLE001
            pass
    img = Image.new("RGBA", (64, 64), (30, 30, 30, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((16, 8, 48, 44), fill=(70, 140, 240, 255))
    draw.rectangle((30, 40, 34, 54), fill=(70, 140, 240, 255))
    draw.line((20, 56, 44, 56), fill=(70, 140, 240, 255), width=3)
    return img


class TrayApp:
    """System-tray application controller.

    Provides set_status() to update the displayed state and triggers
    menu refreshes.  Runs the pystray event loop on a daemon thread.
    """

    def __init__(
        self,
        on_reload: Callable[[], None],
        on_quit: Callable[[], None],
        on_open_settings: Callable[[], None],
        on_open_history: Callable[[], None],
        get_config: Callable[[], dict],
        on_toggle_bool: Callable[[str, bool], None],
        on_set_value: Callable[[str, object], None],
    ) -> None:
        self._status = "idle"
        self._on_reload = on_reload
        self._on_quit = on_quit
        self._on_open_settings = on_open_settings
        self._on_open_history = on_open_history
        self._get_config = get_config
        self._on_toggle_bool = on_toggle_bool
        self._on_set_value = on_set_value
        self._icon = pystray.Icon(
            "voiceflow",
            _load_or_make_icon(),
            "Voice Flow",
            menu=self._build_menu(),
        )
        self._thread: threading.Thread | None = None
        self._last_menu_update: float = 0.0
        self._menu_throttle_secs: float = 0.5

    def _checked(self, key: str) -> bool:
        return bool(self._get_config().get(key))

    def _toggle(self, key: str):
        def _handler(_icon, _item) -> None:
            try:
                self._on_toggle_bool(key, not self._checked(key))
                self._icon.update_menu()
            except Exception as exc:  # noqa: BLE001
                print(f"[tray] toggle {key} error: {exc}")

        return _handler

    def _set_value(self, key: str, value):
        def _handler(_icon, _item) -> None:
            try:
                self._on_set_value(key, value)
                self._icon.update_menu()
            except Exception as exc:  # noqa: BLE001
                print(f"[tray] set {key} error: {exc}")

        return _handler

    def _modes_submenu(self) -> pystray.Menu:
        def items():
            cfg = self._get_config()
            for name in list_modes(cfg):
                yield pystray.MenuItem(
                    name,
                    self._set_value("active_mode", name),
                    checked=lambda _i, n=name: self._get_config().get("active_mode", "Default") == n,
                    radio=True,
                )

        return pystray.Menu(*items())

    def _language_submenu(self) -> pystray.Menu:
        def items():
            for code in QUICK_LANGS:
                yield pystray.MenuItem(
                    code,
                    self._set_value("language", code),
                    checked=lambda _i, c=code: (self._get_config().get("language") or "auto") == c,
                    radio=True,
                )

        return pystray.Menu(*items())

    def _task_submenu(self) -> pystray.Menu:
        def items():
            for profile in list_task_profiles():
                tid = profile["id"]
                label = f"{profile.get('icon', '')}  {profile['name']}"
                yield pystray.MenuItem(
                    label,
                    self._set_value("active_task", tid),
                    checked=lambda _i, t=tid: self._get_config().get("active_task") == t,
                    radio=True,
                )

        return pystray.Menu(*items())

    def _stats_label(self) -> str:
        s = stats_store.get()
        return f"Stats: {s.get('total_sessions', 0)} sessions · {s.get('total_words', 0)} words"

    def _task_label(self) -> str:
        cfg = self._get_config()
        task_id = cfg.get("active_task", "")
        for p in list_task_profiles():
            if p["id"] == task_id:
                return f"Task: {p.get('icon', '')}  {p['name']}"
        return "Task: General"

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(lambda _i: f"Status: {self._status}", None, enabled=False),
            pystray.MenuItem(lambda _i: self._task_label(), None, enabled=False),
            pystray.MenuItem(
                lambda _i: f"Mode: {self._get_config().get('active_mode', 'Default')}", None, enabled=False
            ),
            pystray.MenuItem(lambda _i: self._stats_label(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings\u2026", self._handle_settings),
            pystray.MenuItem("History\u2026", self._handle_history),
            pystray.MenuItem("Task", self._task_submenu()),
            pystray.MenuItem("Mode", self._modes_submenu()),
            pystray.MenuItem("Language", self._language_submenu()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Refine with LLM",
                self._toggle("llm_enabled"),
                checked=lambda _i: self._checked("llm_enabled"),
            ),
            pystray.MenuItem(
                "Wake-word listener",
                self._toggle("wake_word_enabled"),
                checked=lambda _i: self._checked("wake_word_enabled"),
            ),
            pystray.MenuItem(
                "Show waveform",
                self._toggle("show_waveform"),
                checked=lambda _i: self._checked("show_waveform"),
            ),
            pystray.MenuItem(
                "Show notifications",
                self._toggle("show_notification"),
                checked=lambda _i: self._checked("show_notification"),
            ),
            pystray.MenuItem(
                "Save history",
                self._toggle("save_history"),
                checked=lambda _i: self._checked("save_history"),
            ),
            pystray.MenuItem(
                "Typing mode",
                self._toggle("typing_mode"),
                checked=lambda _i: self._checked("typing_mode"),
            ),
            pystray.MenuItem(
                "Sound feedback",
                self._toggle("sound_feedback"),
                checked=lambda _i: self._checked("sound_feedback"),
            ),
            pystray.MenuItem(
                "Context-aware refine",
                self._toggle("context_aware"),
                checked=lambda _i: self._checked("context_aware"),
            ),
            pystray.MenuItem(
                "Launch on startup",
                self._handle_startup_toggle,
                checked=lambda _i: self._checked("launch_on_startup"),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Reload config", self._handle_reload),
            pystray.MenuItem("Quit", self._handle_quit),
        )

    def _handle_settings(self, _icon, _item) -> None:
        try:
            self._on_open_settings()
        except Exception as exc:  # noqa: BLE001
            print(f"[tray] settings error: {exc}")

    def _handle_startup_toggle(self, _icon, _item) -> None:
        try:
            new_val = not self._checked("launch_on_startup")
            self._on_toggle_bool("launch_on_startup", new_val)
            startup_mgr.set_enabled(new_val)
            self._icon.update_menu()
        except Exception as exc:  # noqa: BLE001
            print(f"[tray] startup toggle error: {exc}")

    def _handle_history(self, _icon, _item) -> None:
        try:
            self._on_open_history()
        except Exception as exc:  # noqa: BLE001
            print(f"[tray] history error: {exc}")

    def _handle_reload(self, _icon, _item) -> None:
        try:
            self._on_reload()
            self._icon.update_menu()
        except Exception as exc:  # noqa: BLE001
            print(f"[tray] reload error: {exc}")

    def _handle_quit(self, icon, _item) -> None:
        try:
            self._on_quit()
        finally:
            icon.stop()

    def set_status(self, status: str) -> None:
        self._status = status
        now = time.monotonic()
        if now - self._last_menu_update < self._menu_throttle_secs:
            return
        self._last_menu_update = now
        try:
            self._icon.update_menu()
        except Exception:  # noqa: BLE001
            pass

    def start(self) -> None:
        import sys
        if sys.platform == "darwin":
            self._build_mac_control_panel()
        else:
            self._thread = threading.Thread(target=self._icon.run, name="voiceflow-tray", daemon=True)
            self._thread.start()

    def _build_mac_control_panel(self) -> None:
        import tkinter as tk
        from . import ui as gui_ui
        ui = gui_ui.get()
        def build(root: tk.Tk) -> None:
            win = tk.Toplevel(root)
            win.title("VoiceFlow")
            win.attributes("-topmost", True)
            win.geometry("200x250+50+50")
            win.configure(bg="#1a1b23")
            
            tk.Label(win, text="Voice Flow", font=("Segoe UI", 14, "bold"), bg="#1a1b23", fg="#e2e4ed").pack(pady=10)
            
            def btn(text, cmd):
                b = tk.Button(win, text=text, command=cmd, borderwidth=0, cursor="hand2")
                b.pack(fill="x", padx=15, pady=5)
                
            btn("Settings...", lambda: self._handle_settings(None, None))
            btn("History...", lambda: self._handle_history(None, None))
            btn("Reload Config", lambda: self._handle_reload(None, None))
            btn("Quit", self._handle_quit_mac)
            
            win.protocol("WM_DELETE_WINDOW", win.iconify)
            self._mac_win = win
        ui.submit(build)

    def _handle_quit_mac(self) -> None:
        self._on_quit()
        if hasattr(self, "_mac_win"):
            self._mac_win.destroy()
        import os
        os._exit(0)

    def stop(self) -> None:
        import sys
        if sys.platform == "darwin":
            if hasattr(self, "_mac_win"):
                self._mac_win.destroy()
            return
        try:
            self._icon.stop()
        except Exception:  # noqa: BLE001
            pass
