"""gui/settings.py — Settings window.

A scrollable Toplevel window that exposes all user-configurable options:
  - Whisper model, language, hotkeys
  - LLM provider, model, API keys, mode prompt editing
  - Wake-word toggle and model
  - History, notification, waveform preferences

Changes are written to config.json when the user clicks Save.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from config import load_config, save_config
from modes import list_modes

from .ui import get as get_ui

# Available choices for dropdown selectors
WHISPER_MODELS = ("tiny", "base", "small", "medium", "large")
LLM_PROVIDERS = ("ollama", "groq", "openai", "openai-compat", "lmstudio")
COMMON_LANGS = ("auto", "en", "es", "fr", "de", "it", "pt", "nl", "ja", "zh", "ko", "hi", "ar", "ru")


def _get_mode_prompt(cfg: dict) -> str:
    """Return the prompt text of the currently active mode."""
    active = cfg.get("active_mode", "Default")
    for m in cfg.get("modes") or []:
        if m.get("name") == active:
            return m.get("prompt", "")
    return ""


def _set_mode_prompt(cfg: dict, active_mode: str, new_prompt: str) -> None:
    """Write *new_prompt* into the modes list for *active_mode*."""
    for m in cfg.get("modes") or []:
        if m.get("name") == active_mode:
            m["prompt"] = new_prompt
            return


def open_settings(on_saved: Callable[[], None]) -> None:
    def _build(root: tk.Tk) -> None:
        cfg = load_config()
        win = tk.Toplevel(root)
        win.title("Voice Flow \u2014 Settings")
        win.geometry("480x740")
        win.attributes("-topmost", True)
        win.after(50, lambda: win.attributes("-topmost", False))

        # Make the window scrollable
        outer = ttk.Frame(win)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        frm = ttk.Frame(canvas, padding=12)

        frm.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frm, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        frm.columnconfigure(1, weight=1)

        row = 0

        def add_row(label: str, widget: tk.Widget) -> None:
            nonlocal row
            ttk.Label(frm, text=label).grid(row=row, column=0, sticky="w", pady=4)
            widget.grid(row=row, column=1, sticky="ew", pady=4)
            row += 1

        hotkey_var = tk.StringVar(value=cfg["hotkey"])
        add_row("Hotkey", ttk.Entry(frm, textvariable=hotkey_var))

        repaste_var = tk.StringVar(value=cfg.get("repaste_hotkey", "ctrl+shift+r"))
        add_row("Re-paste hotkey", ttk.Entry(frm, textvariable=repaste_var))

        model_var = tk.StringVar(value=cfg["whisper_model"])
        add_row("Whisper model", ttk.Combobox(frm, textvariable=model_var, values=WHISPER_MODELS, state="readonly"))

        lang_var = tk.StringVar(value=cfg.get("language", "en") or "auto")
        add_row("Language", ttk.Combobox(frm, textvariable=lang_var, values=COMMON_LANGS))

        auto_paste_var = tk.BooleanVar(value=cfg["auto_paste"])
        add_row("Auto-paste", ttk.Checkbutton(frm, variable=auto_paste_var))

        typing_mode_var = tk.BooleanVar(value=cfg.get("typing_mode", False))
        add_row("Typing mode (type chars)", ttk.Checkbutton(frm, variable=typing_mode_var))

        sound_var = tk.BooleanVar(value=cfg.get("sound_feedback", False))
        add_row("Sound feedback", ttk.Checkbutton(frm, variable=sound_var))

        ttk.Separator(frm, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)
        row += 1

        llm_enabled_var = tk.BooleanVar(value=cfg["llm_enabled"])
        add_row("Refine with LLM", ttk.Checkbutton(frm, variable=llm_enabled_var))

        context_var = tk.BooleanVar(value=cfg.get("context_aware", False))
        add_row("Context-aware refine", ttk.Checkbutton(frm, variable=context_var))

        provider_var = tk.StringVar(value=cfg.get("llm_provider", "ollama"))
        add_row("LLM provider", ttk.Combobox(frm, textvariable=provider_var, values=LLM_PROVIDERS, state="readonly"))

        llm_model_var = tk.StringVar(value=cfg.get("llm_model", "llama3"))
        add_row("LLM model", ttk.Entry(frm, textvariable=llm_model_var))

        ollama_url_var = tk.StringVar(value=cfg.get("ollama_url", "http://localhost:11434"))
        add_row("Ollama URL", ttk.Entry(frm, textvariable=ollama_url_var))

        groq_key_var = tk.StringVar(value=cfg.get("groq_api_key", ""))
        add_row("Groq API key", ttk.Entry(frm, textvariable=groq_key_var, show="\u2022"))

        openai_url_var = tk.StringVar(value=cfg.get("openai_base_url", "https://api.openai.com/v1"))
        add_row("OpenAI / compat URL", ttk.Entry(frm, textvariable=openai_url_var))

        openai_key_var = tk.StringVar(value=cfg.get("openai_api_key", ""))
        add_row("OpenAI API key", ttk.Entry(frm, textvariable=openai_key_var, show="\u2022"))

        active_mode_var = tk.StringVar(value=cfg.get("active_mode", "Default"))
        add_row(
            "Active mode",
            ttk.Combobox(frm, textvariable=active_mode_var, values=list_modes(cfg), state="readonly"),
        )

        # Editable prompt for current mode
        ttk.Label(frm, text="Mode prompt (editable):").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )
        row += 1
        prompt_text = tk.Text(frm, height=4, wrap="word")
        prompt_text.insert("1.0", _get_mode_prompt(cfg))
        prompt_text.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        row += 1

        ttk.Separator(frm, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)
        row += 1

        wake_var = tk.BooleanVar(value=cfg.get("wake_word_enabled", False))
        add_row("Wake word listening", ttk.Checkbutton(frm, variable=wake_var))

        wake_model_var = tk.StringVar(value=cfg.get("wake_word_model", "hey_jarvis"))
        add_row("Wake-word model", ttk.Entry(frm, textvariable=wake_model_var))

        ttk.Separator(frm, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)
        row += 1

        save_history_var = tk.BooleanVar(value=cfg.get("save_history", True))
        add_row("Save history", ttk.Checkbutton(frm, variable=save_history_var))

        notify_var = tk.BooleanVar(value=cfg.get("show_notification", True))
        add_row("Show notifications", ttk.Checkbutton(frm, variable=notify_var))

        notif_dur_var = tk.StringVar(value=str(cfg.get("notification_duration", 4000)))
        add_row("Notification duration (ms)", ttk.Entry(frm, textvariable=notif_dur_var))

        waveform_var = tk.BooleanVar(value=cfg.get("show_waveform", False))
        add_row("Show waveform while recording", ttk.Checkbutton(frm, variable=waveform_var))

        def do_save() -> None:
            # Update mode prompt if changed
            mode_name = active_mode_var.get() or "Default"
            new_prompt = prompt_text.get("1.0", "end").strip()
            if new_prompt:
                _set_mode_prompt(cfg, mode_name, new_prompt)

            try:
                notif_dur = int(notif_dur_var.get().strip() or "4000")
            except ValueError:
                notif_dur = 4000

            cfg.update(
                {
                    "hotkey": hotkey_var.get().strip() or cfg["hotkey"],
                    "repaste_hotkey": repaste_var.get().strip() or "ctrl+shift+r",
                    "whisper_model": model_var.get(),
                    "language": lang_var.get().strip() or "auto",
                    "auto_paste": bool(auto_paste_var.get()),
                    "typing_mode": bool(typing_mode_var.get()),
                    "sound_feedback": bool(sound_var.get()),
                    "llm_enabled": bool(llm_enabled_var.get()),
                    "context_aware": bool(context_var.get()),
                    "llm_provider": provider_var.get(),
                    "llm_model": llm_model_var.get().strip() or "llama3",
                    "ollama_url": ollama_url_var.get().strip() or "http://localhost:11434",
                    "groq_api_key": groq_key_var.get().strip(),
                    "openai_base_url": openai_url_var.get().strip() or "https://api.openai.com/v1",
                    "openai_api_key": openai_key_var.get().strip(),
                    "active_mode": mode_name,
                    "wake_word_enabled": bool(wake_var.get()),
                    "wake_word_model": wake_model_var.get().strip() or "hey_jarvis",
                    "save_history": bool(save_history_var.get()),
                    "show_notification": bool(notify_var.get()),
                    "notification_duration": notif_dur,
                    "show_waveform": bool(waveform_var.get()),
                }
            )
            save_config(cfg)
            on_saved()
            win.destroy()

        btns = ttk.Frame(frm)
        btns.grid(row=row, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="Save", command=do_save).pack(side="right")

    get_ui().submit(_build)
