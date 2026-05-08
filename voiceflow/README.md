# Voice Flow

Hold a hotkey (or say a wake word), speak, release — your words get transcribed locally with Whisper, optionally rewritten by a local LLM into the mode of your choice (email / code / bullets / meeting notes / custom), and pasted into the focused window. Tray-resident, fully offline.

## Prereqs

- **Python 3.11** (the pinned interpreter for this project — `openai-whisper` and `PyQt6`-free deps have reliable wheels here; 3.14 does not).
- **ffmpeg** on PATH — required by `openai-whisper` for audio decoding.
  - Windows: `winget install Gyan.FFmpeg` or `choco install ffmpeg`
- A working microphone.

## Install

From `voiceflow/`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# optional Phase-4 extras (wake word, packaging):
pip install -r requirements-optional.txt
```

## Run

```powershell
python main.py
```

A tray icon appears. Hold **Ctrl+Shift+Space**, speak a sentence, release. After ~2–5 s (depending on Whisper model size), the transcribed text is pasted into whichever window had focus when you started talking. Press **Escape** while recording to cancel without transcribing.

The first run downloads the Whisper model (~150 MB for `base`).

## Configure

Edit [config.json](config.json) and choose **Reload config** from the tray menu. Notable fields:

- `hotkey` — e.g. `"ctrl+shift+space"`, `"ctrl+alt+v"`, `"f9"`.
- `whisper_model` — `tiny` / `base` / `small` / `medium` / `large` (bigger = better + slower).
- `language` — ISO code, e.g. `"en"`, `"es"`. Use `null`-style auto-detect by removing the field if desired.
- `auto_paste` — if `false`, the transcript is copied to clipboard but not pasted.
- `typing_mode` — if `true`, types text character-by-character instead of using Ctrl+V paste. Useful for apps that block clipboard paste.
- `llm_enabled` — toggle from the tray (**Refine with LLM**) or set here. When on, the transcript is sent to the configured LLM provider before being pasted.
- `llm_provider` — `"ollama"` (local, default) or `"groq"` (cloud, requires API key).
- `llm_model` — for Ollama: any model you've pulled, e.g. `llama3`, `mistral`. For Groq: e.g. `llama3-8b-8192`.
- `groq_api_key` — your Groq API key (only needed when `llm_provider` is `"groq"`).
- `groq_url` — Groq API base URL (defaults to `https://api.groq.com/openai/v1`).
- `llm_prompt` — instruction prepended to the transcript. Default fixes grammar; swap in `"Convert this voice note into concise bullet points:"` or `"Format this as a professional email body:"` for different modes.
- `ollama_url` — defaults to `http://localhost:11434`.
- `ollama_timeout` — seconds to wait for a response (default 60).

## Tray menu

- **Status** — shows `idle / recording / transcribing / refining` (informational).
- **Settings…** — full Tkinter settings form (hotkey, model, language, LLM, prompt, etc.).
- **History…** — viewer for past transcripts (stored in `history.jsonl`).
- **Mode** — submenu of refinement modes (Default, Email, Code comment, Bullets, Meeting notes, plus any you've added in `config.json`). The active mode supplies the LLM prompt.
- **Language** — quick switcher: `auto` / `en` / `es` / `fr` / `de` / `ja` / `zh` / `hi`. Edit `config.json` for any other ISO code.
- **Stats** — shows total sessions, words, and characters transcribed (informational).
- **Refine with LLM** / **Wake-word listener** / **Show waveform** / **Show notifications** / **Save history** / **Typing mode** — checkable toggles persisted to `config.json`.
- **Reload config** — re-reads `config.json`; swapping `whisper_model` triggers a lazy reload on the next utterance.
- **Quit** — stops the app.

## Phase 3 — UI polish

- **Settings window** — opens via tray; saves write to `config.json` and trigger a live reload (no restart).
- **Live waveform** — small always-on-top window appears while recording when **Show waveform** is enabled. Renders RMS bars from the mic stream.
- **History log** — every transcript is appended to `history.jsonl` (one JSON object per line) when **Save history** is on. The viewer shows the most recent 200 entries and supports clearing.
- **Toast notification** — bottom-right popup with a preview of the (refined) text after each dictation, plus word and character count. Disabled via **Show notifications**.

## Phase 2 — LLM setup

### Ollama (local, free)

1. Install Ollama from <https://ollama.com> and start it (it runs as a background service on port 11434 by default).
2. Pull a model: `ollama pull llama3` (or whichever model you set in `llm_model`).
3. Either set `"llm_enabled": true` in `config.json` and **Reload config**, or just toggle **Refine with LLM** in the tray.
4. Speak as usual — the transcript is run through Ollama with `llm_prompt` before being pasted. If Ollama is unreachable or times out, the original transcript is pasted instead (logged to stderr).

### Groq (cloud, free tier)

1. Sign up at <https://console.groq.com> and create an API key.
2. Set `"llm_provider": "groq"` and `"groq_api_key": "gsk_..."` in `config.json` (or via the Settings window).
3. Set `"llm_model"` to a Groq-supported model, e.g. `"llama3-8b-8192"`.
4. Toggle **Refine with LLM** in the tray. If the API is unreachable, the original transcript is pasted instead.

## Troubleshooting

- **No tray icon on Windows** — pystray uses the system notification area; check the overflow chevron.
- **`OSError: PortAudio library not found`** — `sounddevice` ships PortAudio binaries via wheels; if you see this, reinstall `sounddevice` inside the venv (`pip install --force-reinstall sounddevice`).
- **`ffmpeg` not found** — install it and reopen your terminal so PATH refreshes.
- **Pasted text appears in the wrong window** — make sure the target window has focus *before* you press the hotkey; the tray menu must not have been clicked just prior.

## Phase 4 — modes, exports, wake word, packaging

### Custom modes

`config.json` carries a `modes` array; each entry is `{name, prompt}`. The **Mode** submenu in the tray (and the **Active mode** field in the settings window) chooses which prompt the refiner uses. To add a mode, append a new object to `modes` in `config.json` and **Reload config**:

```json
{
  "name": "Slack reply",
  "prompt": "Rewrite this voice note as a casual Slack reply, max 2 sentences. Return only the reply."
}
```

### Multi-language

The `language` field accepts any ISO code Whisper supports, plus `"auto"` for language detection. Quick switching: tray → **Language**. Tray defaults expose `auto / en / es / fr / de / ja / zh / hi`; everything else goes via the settings window or `config.json` directly.

### Export transcripts

Open **History…**, optionally select rows, then **Export .txt** or **Export .md**. Markdown export uses the entry timestamp as a heading and embeds the raw transcript as a `<sub>` annotation when refinement changed the text.

### Wake word (optional)

Wake-word listening is built on [openwakeword](https://github.com/dscripka/openWakeWord). Install the optional deps:

```powershell
pip install -r requirements-optional.txt
```

Pick a model in `config.json` (`wake_word_model`). Bundled keywords include `alexa`, `hey_jarvis`, `hey_mycroft` — there is no prebuilt "voice flow" keyword. Set `wake_word_model` to a path of any custom `.onnx` if you've trained one. Toggle the listener via **Wake-word listener** in the tray.

When the wake word fires, recording starts immediately and stops automatically once ~1.2 s of silence is detected (or 12 s elapse). The same transcribe → refine → paste pipeline runs from there.

### Single-file packaging (PyInstaller)

```powershell
pip install -r requirements-optional.txt
pyinstaller voiceflow.spec
```

Output goes to `dist/VoiceFlow/`; launch `dist/VoiceFlow/VoiceFlow.exe`. The Whisper model itself is **not** bundled — it's pulled into the user's home cache on first run, and `ffmpeg` must still be on PATH. The spec auto-includes openwakeword/onnxruntime data files when those packages are present in the venv.

## Files

| Path | Role |
|---|---|
| `main.py` | Orchestration (tray, hotkey, wake-word, pipeline) |
| `recorder.py` | Mic capture + silence-based auto-stop |
| `transcriber.py` | Whisper wrapper (lazy load, `auto` language) |
| `refiner.py` | Ollama call using the active mode's prompt |
| `paster.py` | Clipboard + auto-paste |
| `hotkey.py` | pynput chord listener |
| `wakeword.py` | openwakeword listener (optional) |
| `modes.py` | Mode definitions + lookup |
| `history.py` | JSONL history append/load/clear |
| `gui/ui.py` | Single Tk dispatcher thread |
| `gui/tray.py` | pystray tray icon + menus |
| `gui/settings.py` | Settings form |
| `gui/history.py` | History viewer + exports |
| `gui/notify.py` | Toast popup |
| `gui/waveform.py` | Live RMS waveform overlay |
| `voiceflow.spec` | PyInstaller spec |



\