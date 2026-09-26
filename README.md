# VoiceFlow

[![CI](https://github.com/Sdnsoumy/VoiceFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/Sdnsoumy/VoiceFlow/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

VoiceFlow is a desktop voice dictation tool that records speech, transcribes it locally with Whisper, optionally refines the text with a local or cloud LLM, and pastes the result into the active application. It is built for fast dictation workflows with a tray-based UI, configurable hotkeys, optional wake-word activation, and transcript history.

## What it does

- Hold a hotkey or trigger a wake word to start recording.
- Transcribe speech locally with Whisper.
- Optionally rewrite the transcript using an LLM prompt mode.
- Paste or type the final text into the focused window.
- Keep recent transcripts, stats, notifications, and a live waveform overlay.

## Repository Layout

- `voiceflow/main.py` - app orchestration and startup flow.
- `voiceflow/recorder.py` - microphone capture and silence handling.
- `voiceflow/transcriber.py` - Whisper integration.
- `voiceflow/refiner.py` - optional text refinement through an LLM.
- `voiceflow/paster.py` - clipboard and paste/typing output.
- `voiceflow/gui/` - tray icon, settings window, history viewer, notifications, and waveform UI.
- `voiceflow/config.json` - user configuration.
- `voiceflow/README.md` - detailed setup and feature documentation.

## Requirements

- Python 3.11.
- `ffmpeg` on your `PATH` for audio decoding.
- A working microphone.

Optional features may also require extra dependencies from `voiceflow/requirements-optional.txt`.

## Quick Start

From the repository root:

```powershell
cd voiceflow
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Then launch the app:

```powershell
python main.py
```

On first run, Whisper may download a model into your local cache. After the app starts, use the tray menu to open settings, change modes, view history, or toggle optional features.

## Configuration

Most behavior is controlled through `voiceflow/config.json`. Common settings include:

- `hotkey` for the push-to-talk shortcut.
- `whisper_model` for transcription quality and speed.
- `language` for automatic detection or a fixed language code.
- `llm_enabled`, `llm_provider`, and `llm_model` for refinement.
- `auto_paste` and `typing_mode` for output behavior.

## Optional Features

- Wake-word listening via `openwakeword`.
- Exporting transcript history.
- Packaging into a standalone app with PyInstaller.

## More Documentation

The full setup guide, feature list, troubleshooting notes, and packaging instructions live in [voiceflow/README.md](voiceflow/README.md).

## License

VoiceFlow is licensed under the [Apache License 2.0](LICENSE).
