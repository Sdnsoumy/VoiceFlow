# 🎙️ Voice Flow — Implementation Plan

> A lightweight desktop app that lets you **speak → transcribe → refine → paste** anywhere, triggered by a hotkey — completely free and mostly local.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [App Architecture](#app-architecture)
- [Features by Phase](#features-by-phase)
- [Folder Structure](#folder-structure)
- [Implementation Timeline](#implementation-timeline)
- [Key Dependencies](#key-dependencies)
- [Config Schema](#config-schema)
- [Deliverable](#deliverable)

---

## Overview

**Voice Flow** is a SuperWhisper-inspired voice-to-text desktop app built entirely on free and open-source tools. Press a hotkey, speak, and your words are transcribed and pasted directly into any active window — optionally refined by an AI language model.

### Core Flow

```
Hotkey Press → Record Audio → Whisper STT → LLM Refine → Auto Paste
```

---

## Tech Stack

| Layer | Tool | Cost |
|---|---|---|
| Language | Python 3.10+ | Free |
| Speech-to-Text | `openai-whisper` (local) | Free |
| Audio Capture | `sounddevice` + `scipy` | Free |
| Hotkey Listener | `pynput` | Free |
| LLM Refinement | `Ollama` (local) or `Groq API` | Free |
| Clipboard | `pyperclip` | Free |
| Auto-Paste | `pyautogui` | Free |
| GUI | `PyQt6` or `Tkinter` | Free |

---

## App Architecture

```
┌─────────────────────────────────────────┐
│             Voice Flow App              │
│                                         │
│  ┌─────────┐     ┌──────────────────┐   │
│  │ Hotkey  │────▶│  Audio Recorder  │   │
│  │Listener │     │  (sounddevice)   │   │
│  └─────────┘     └────────┬─────────┘   │
│                           │             │
│                  ┌────────▼─────────┐   │
│                  │   Whisper STT    │   │
│                  │  (local model)   │   │
│                  └────────┬─────────┘   │
│                           │             │
│                  ┌────────▼─────────┐   │
│                  │   LLM Refiner    │   │
│                  │ (Ollama / Groq)  │   │
│                  └────────┬─────────┘   │
│                           │             │
│                  ┌────────▼─────────┐   │
│                  │   Auto Paste     │   │
│                  │  (pyautogui)     │   │
│                  └──────────────────┘   │
└─────────────────────────────────────────┘
```

---

## Features by Phase

### ✅ Phase 1 — Core MVP
- Hold hotkey → record audio
- Release hotkey → transcribe with Whisper
- Auto-copy and paste result into active window
- System tray icon (runs silently in background)

### ✅ Phase 2 — Refinement
- Optional LLM post-processing (fix grammar, summarize, convert to bullet points)
- Choose Whisper model size: `tiny` / `base` / `small` / `medium` / `large`
- Language selection support
- Groq API support (cloud LLM alternative to local Ollama)

### ✅ Phase 3 — UI & Polish
- Settings panel (hotkey config, model selection, LLM toggle)
- Live audio waveform while recording
- Transcription history log
- Desktop notification popup with result preview and word/char count

### ✅ Phase 4 — Advanced
- Custom AI modes: `Email mode`, `Code mode`, `Meeting Notes mode`
- Multi-language support
- Export transcripts to `.txt` or `.md`
- Wake-word detection (optional, uses `openwakeword`)

### ✅ Phase 5 — Enhancements (New)
- **Groq API integration** — cloud-based LLM refinement via Groq as alternative to Ollama; select provider in settings
- **Typing mode** — type text character-by-character instead of Ctrl+V paste, for apps that block clipboard paste
- **Cancel recording** — press Escape while recording to abort without transcribing
- **Statistics tracking** — tracks total sessions, words, and characters; displayed in tray menu
- **Word/char count in notifications** — toast shows word and character count after each transcription

### ✅ Phase 6 — Task Workspaces
- **Task launcher on startup** — choose what you're doing (Prompt Writing, Coding, Email, Notes, Meeting, General) before the app starts; the app adapts its entire behavior
- **Task-specific LLM prompts** — each task has a specialized prompt (e.g. Prompt Writing preserves technical terms, Coding outputs docstring-style text, Email adds greetings)
- **Auto-configure per task** — selecting a task auto-sets the LLM mode, enables/disables refinement, and picks the right prompt
- **Task switching via tray** — change task from the tray menu at any time without restarting
- **Skip launcher option** — "Don't show again" checkbox remembers last task and skips the chooser on next launch
- **Double-click to start** — double-click any task card to instantly launch

### ✅ Phase 7 — Smarter UX
- **Re-paste last result** — Ctrl+Shift+R (configurable) re-pastes the last transcription without re-recording
- **Sound feedback** — audio beeps on record start, stop, cancel, and paste (uses built-in `winsound`, no new deps)
- **Clipboard-aware templates** — use `{clipboard}` in any mode prompt to inject current clipboard content as context

### ✅ Phase 8 — Search & Productivity
- **Full-text search** in history viewer — live filter as you type
- **Date range filter** — All / Today / Last 7 days / Last 30 days / Favorites
- **Favorites** — star/unstar transcripts; filter to show only favorites

### ✅ Phase 9 — Polish & Cross-Platform
- **macOS Cmd+V paste** — auto-detects platform and uses Cmd+V on macOS
- **Launch on startup** — toggle in tray; registers in Windows HKCU\Run (non-admin)
- **Configurable notification duration** — set in Settings (milliseconds)
- **Scrollable settings window** — settings panel now scrolls to fit all options

### ✅ Phase 10 — Advanced AI
- **Context-aware refinement** — toggle sends previous transcript as context so the LLM produces coherent follow-up text
- **OpenAI-compatible provider** — works with OpenAI, LM Studio, text-generation-webui, or any OpenAI-compatible API
- **Editable mode prompts in Settings** — edit the active mode's prompt directly in the Settings window (no config.json needed)
- **5 LLM providers** — Ollama, Groq, OpenAI, OpenAI-compat, LM Studio

### 🐛 Bug Fixes Applied
- Fixed deadlock in wake-word auto-stop: if recorder was stopped externally, `pipeline_lock` was never released
- Replaced direct access to `Transcriber._model` with proper `reload_model()` API
- Removed unused `current` variable in tray mode submenu

---

## Folder Structure

```
voiceflow/
├── main.py               # Entry point — launcher + app loop
├── recorder.py           # Audio capture logic (sounddevice)
├── transcriber.py        # Whisper STT integration
├── refiner.py            # LLM post-processing (Ollama / Groq)
├── paster.py             # Clipboard + auto-paste logic
├── hotkey.py             # Global hotkey listener (pynput)
├── modes.py              # LLM modes + task profiles
├── config.py             # Config load/save + defaults
├── history.py            # JSONL history store
├── stats.py              # Session/word statistics
├── wakeword.py           # Wake-word listener (openwakeword)
├── gui/
│   ├── ui.py             # Tk thread dispatcher
│   ├── tray.py           # System tray icon & menu
│   ├── launcher.py       # Task chooser on startup
│   ├── settings.py       # Settings window (Tkinter)
│   ├── history.py        # Transcript history panel
│   ├── waveform.py       # Live waveform window
│   └── notify.py         # Toast notifications
├── assets/
│   └── icon.png          # Tray icon
├── config.json           # User preferences
├── requirements.txt      # Core dependencies
├── requirements-optional.txt  # Wake-word + packaging
└── README.md             # Setup & usage guide
```

---

## Implementation Timeline

| Week | Tasks |
|---|---|
| **Week 1** | `recorder.py` + `transcriber.py` — get STT working end-to-end |
| **Week 1** | `paster.py` + `hotkey.py` — full hotkey → paste pipeline |
| **Week 2** | `refiner.py` — LLM integration (Ollama local + Groq fallback) |
| **Week 2** | `tray.py` — app runs silently in system tray |
| **Week 3** | Settings UI + transcription history log |
| **Week 4** | Polish, packaging, README, and optional wake word |

---

## Key Dependencies

```txt
openai-whisper       # Local Whisper STT model
sounddevice          # Microphone audio capture
scipy                # Save audio as .wav
pyautogui            # Simulate keyboard paste
pyperclip            # Clipboard management
pynput               # Global hotkey listener
requests             # HTTP calls to Groq API
PyQt6                # GUI (settings window + tray)
ollama               # Local LLM runtime (optional)
```

Install all at once:

```bash
pip install openai-whisper sounddevice scipy pyautogui pyperclip pynput requests PyQt6
```

---

## Config Schema

```json
{
  "hotkey": "ctrl+shift+space",
  "whisper_model": "base",
  "language": "en",
  "llm_enabled": true,
  "llm_provider": "ollama",
  "llm_model": "llama3",
  "llm_prompt": "Fix grammar and clean up the following transcript:",
  "auto_paste": true,
  "show_notification": true,
  "save_history": true
}
```

---

## Deliverable

A **single installable Python app** that:

- Runs silently in the **system tray**
- Activates instantly on a **custom hotkey**
- **Transcribes** speech using local Whisper (no internet required)
- Optionally **refines** text using a local or free cloud LLM
- **Auto-pastes** result into any focused window in under 2 seconds
- Works **100% offline** with Whisper + Ollama

---

*Built with 💙 using open-source tools — no subscriptions, no cloud lock-in.*