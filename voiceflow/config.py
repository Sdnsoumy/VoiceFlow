"""config.py — Configuration loading and saving.

Reads/writes a JSON file (config.json) next to this module.  On first
run the file is created with sensible defaults.  Every load merges saved
values into DEFAULTS so newly added keys are always present.
"""

from __future__ import annotations

import json
from pathlib import Path

from modes import DEFAULT_MODES

# Locate config.json in the same directory as this module
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

DEFAULTS: dict = {
    "hotkey": "ctrl+shift+space",
    "whisper_model": "base",
    "language": "en",
    "llm_enabled": False,
    "llm_provider": "ollama",
    "llm_model": "llama3",
    "llm_prompt": "Fix grammar and clean up the following transcript:",
    "ollama_url": "http://localhost:11434",
    "ollama_timeout": 60,
    "groq_api_key": "",
    "groq_url": "https://api.groq.com/openai/v1",
    "openai_api_key": "",
    "openai_base_url": "https://api.openai.com/v1",
    "active_mode": "Default",
    "active_task": "",
    "skip_launcher": False,
    "modes": DEFAULT_MODES,
    "wake_word_enabled": False,
    "wake_word_model": "hey_jarvis",
    "wake_word_threshold": 0.5,
    "auto_paste": True,
    "typing_mode": False,
    "sound_feedback": False,
    "context_aware": False,
    "repaste_hotkey": "ctrl+shift+r",
    "notification_duration": 4000,
    "launch_on_startup": False,
    "show_notification": True,
    "save_history": True,
    "show_waveform": False,
}


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    # Always carry forward DEFAULT_MODES if the user hasn't customized them
    if "modes" not in cfg:
        cfg["modes"] = DEFAULT_MODES
    return cfg


def save_config(cfg: dict) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
