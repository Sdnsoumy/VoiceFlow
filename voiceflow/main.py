"""main.py — Application entry point and orchestrator.

This module wires together all Voice Flow subsystems:
  1. Task launcher  — lets the user pick a task profile on startup
  2. Recorder       — captures microphone audio
  3. Transcriber    — converts audio to text via Whisper
  4. Refiner        — optionally polishes text through an LLM
  5. Paster         — places the final text wherever the cursor is
  6. Tray / GUI     — system-tray icon, settings, history, waveform
  7. Hotkey listener — global push-to-talk and re-paste shortcuts
  8. Wake-word      — optional hands-free activation ("Hey Jarvis")

All heavy work (recording, transcription, LLM calls) runs off the main
thread so the hotkey listener stays responsive.
"""

from __future__ import annotations

import os
import shutil
import sys
import threading
import traceback

# Ensure the voiceflow package directory is on sys.path so sibling
# modules (config, modes, etc.) can be imported by name.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import history as history_store
import hotkey
import paster
import refiner
import sounds
import stats
from config import load_config, save_config
from gui import notify
from gui.history import open_history
from gui.launcher import show_launcher
from gui.settings import open_settings
from gui.tray import TrayApp
from gui.ui import get as get_ui
from gui.waveform import WaveformWindow
from modes import get_task_profile
from recorder import Recorder, auto_stop_on_silence
from transcriber import Transcriber
from wakeword import WakeWordListener


def _apply_task_profile(config: dict, task_id: str) -> dict:
    """Overlay task-profile settings onto the running config.

    When the user selects a task (e.g. "email", "coding") the profile
    overrides active_mode and llm_enabled so the app adapts its behavior.
    """
    profile = get_task_profile(task_id)
    if profile is None:
        return config
    config["active_task"] = task_id
    config["active_mode"] = profile.get("active_mode", config.get("active_mode", "Default"))
    config["llm_enabled"] = profile.get("llm_enabled", config.get("llm_enabled", False))
    return config


def main() -> None:
    """Boot sequence: load config → show launcher → init subsystems → run hotkey loop."""
    config = load_config()

    # Fail early with an actionable message instead of waiting for Whisper to
    # fail later while decoding the first recording.
    if shutil.which("ffmpeg") is None:
        print("[main] ERROR: Whisper requires ffmpeg, but it was not found on PATH.")
        print("[main] Install ffmpeg using one of these commands:")
        print("[main]   Windows: winget install Gyan.FFmpeg")
        print("[main]   macOS: brew install ffmpeg")
        print("[main] Then restart VoiceFlow after your PATH is refreshed.")
        return

    # --- Task launcher (skip if config says so) ---
    if not config.get("skip_launcher"):
        chosen_task = [None]

        def on_task_chosen(task_id: str, skip: bool) -> None:
            chosen_task[0] = task_id
            if skip:
                config["skip_launcher"] = True

        show_launcher(on_task_chosen)

        task_id = chosen_task[0] or "general"
        config = _apply_task_profile(config, task_id)
        save_config(config)
        print(f"[main] task: {task_id}")
    else:
        task_id = config.get("active_task", "general")
        config = _apply_task_profile(config, task_id)
        print(f"[main] task (from config): {task_id}")

    print(
        f"[main] config: hotkey={config['hotkey']} model={config['whisper_model']} "
        f"mode={config.get('active_mode')} lang={config.get('language')} "
        f"llm={config['llm_enabled']} wake={config.get('wake_word_enabled')}"
    )

    # ---- Initialise core subsystems ----
    get_ui()  # Start the shared Tk UI thread (must happen before any GUI calls)
    recorder = Recorder()
    transcriber = Transcriber(config["whisper_model"])
    waveform = WaveformWindow(get_levels=lambda: recorder.levels)

    # Shared mutable state accessible from multiple callbacks/threads.
    # Only _prev_transcript is written cross-thread; other fields are
    # written from the pynput callback thread (single writer).
    state = {"config": config, "wake_listener": None}

    # Prevents two recordings from overlapping (hotkey vs wake-word).
    pipeline_lock = threading.Lock()

    def get_config() -> dict:
        """Callback given to TrayApp so it can read the current config."""
        return state["config"]

    def process_audio(audio) -> None:
        """Pipeline: transcribe → (optionally) refine → paste → history/stats/notify."""
        if audio is None or audio.size == 0:
            tray.set_status("idle")
            return
        try:
            cfg = state["config"]
            tray.set_status("transcribing")
            raw = transcriber.transcribe(audio, cfg.get("language", "en"))
            text = raw
            if raw and cfg.get("llm_enabled"):
                tray.set_status("refining")
                # Inject previous transcript for context-aware refinement
                cfg["_last_transcript"] = state.get("_prev_transcript", "")
                text = refiner.refine(raw, cfg)

            paster.paste(text, cfg["auto_paste"], typing_mode=cfg.get("typing_mode", False))
            if text and cfg.get("sound_feedback"):
                sounds.on_paste()

            if text:
                state["_prev_transcript"] = text
                if cfg.get("save_history", True):
                    try:
                        history_store.append(raw, refined=text if text != raw else None)
                    except Exception as exc:  # noqa: BLE001
                        print(f"[main] history append failed: {exc}")
                try:
                    stats.record(text)
                except Exception as exc:  # noqa: BLE001
                    print(f"[main] stats record failed: {exc}")
                if cfg.get("show_notification", True):
                    word_count = len(text.split())
                    char_count = len(text)
                    suffix = f"\n\n[{word_count} words · {char_count} chars]"
                    notify.show_toast(text + suffix, duration_ms=cfg.get("notification_duration", 4000))
            print(f"[main] -> {text!r}")
        except Exception:  # noqa: BLE001
            traceback.print_exc()
        finally:
            tray.set_status("idle")

    def start_wake_listener_if_needed() -> None:
        """Start or stop the wake-word listener based on the current config.

        The listener runs on its own daemon thread and fires on_wake_detected()
        when it hears the trigger phrase (e.g. "Hey Jarvis").
        """
        cfg = state["config"]
        existing = state["wake_listener"]
        if cfg.get("wake_word_enabled"):
            if existing is None:
                listener = WakeWordListener(
                    model=cfg.get("wake_word_model", "hey_jarvis"),
                    on_detect=on_wake_detected,
                    threshold=float(cfg.get("wake_word_threshold", 0.5)),
                )
                listener.start()
                state["wake_listener"] = listener
        else:
            if existing is not None:
                existing.stop()
                state["wake_listener"] = None

    def reload_config() -> None:
        """Re-read config.json from disk and apply changes live."""
        new_cfg = load_config()
        state["config"] = new_cfg
        if new_cfg["whisper_model"] != transcriber.model_name:
            print(f"[main] whisper model changed -> {new_cfg['whisper_model']}; will reload on next utterance")
            transcriber.reload_model(new_cfg["whisper_model"])
        start_wake_listener_if_needed()
        print("[main] config reloaded")

    def toggle_bool(key: str, enabled: bool) -> None:
        """Toggle a boolean config key (called from tray menu checkboxes)."""
        state["config"][key] = enabled
        save_config(state["config"])
        print(f"[main] {key} -> {enabled}")
        if key == "wake_word_enabled":
            start_wake_listener_if_needed()

    def set_value(key: str, value) -> None:
        """Set an arbitrary config key to a value (called from tray submenus)."""
        state["config"][key] = value
        if key == "active_task" and isinstance(value, str):
            state["config"] = _apply_task_profile(state["config"], value)
            print(f"[main] switched task -> {value}")
        else:
            print(f"[main] {key} -> {value}")
        save_config(state["config"])
        if key == "wake_word_model":
            # restart listener if running
            if state["wake_listener"] is not None:
                state["wake_listener"].stop()
                state["wake_listener"] = None
                start_wake_listener_if_needed()

    def quit_app() -> None:
        print("[main] quitting")
        if state["wake_listener"] is not None:
            state["wake_listener"].stop()
        sys.exit(0)

    tray = TrayApp(
        on_reload=reload_config,
        on_quit=quit_app,
        on_open_settings=lambda: open_settings(on_saved=reload_config),
        on_open_history=open_history,
        get_config=get_config,
        on_toggle_bool=toggle_bool,
        on_set_value=set_value,
    )
    tray.start()

    # ---------- hotkey path (push-to-talk) ----------
    # The user holds a chord (e.g. Ctrl+Shift+Space) to record, and
    # releases it to stop + process.  Pressing Escape while held cancels.
    cancel_flag = threading.Event()
    _lock_held = threading.Event()  # tracks whether we own pipeline_lock

    def _release_pipeline() -> None:
        """Release pipeline_lock only if we currently hold it."""
        if _lock_held.is_set():
            _lock_held.clear()
            pipeline_lock.release()

    def on_press_chord() -> None:
        if not pipeline_lock.acquire(blocking=False):
            return
        _lock_held.set()
        try:
            cancel_flag.clear()
            tray.set_status("recording")
            if state["config"].get("sound_feedback"):
                sounds.on_record_start()
            recorder.start()
            if state["config"].get("show_waveform"):
                waveform.show()
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            tray.set_status("idle")
            _release_pipeline()

    def on_release_chord() -> None:
        try:
            audio = recorder.stop()
            waveform.hide()
            if cancel_flag.is_set():
                print("[main] recording cancelled")
                tray.set_status("idle")
            else:
                if state["config"].get("sound_feedback"):
                    sounds.on_record_stop()
                process_audio(audio)
        finally:
            _release_pipeline()

    def on_cancel() -> None:
        if recorder.is_running():
            cancel_flag.set()
            audio = recorder.stop()
            waveform.hide()
            tray.set_status("idle")
            if state["config"].get("sound_feedback"):
                sounds.on_cancel()
            print("[main] recording cancelled via Escape")
            _release_pipeline()

    # ---------- wake-word path (auto-stop on silence) ----------
    # When the wake word fires, recording starts automatically and a
    # background watcher thread stops it after silence_secs of silence
    # or after max_secs have elapsed.
    def on_wake_detected() -> None:
        if not pipeline_lock.acquire(blocking=False):
            return
        _lock_held.set()
        try:
            tray.set_status("recording")
            recorder.start()
            if state["config"].get("show_waveform"):
                waveform.show()
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            tray.set_status("idle")
            _release_pipeline()
            return

        def _on_done(audio) -> None:
            try:
                waveform.hide()
                process_audio(audio)
            finally:
                _release_pipeline()

        auto_stop_on_silence(recorder, _on_done)

    # ---------- re-paste last result ----------
    def on_repaste() -> None:
        cfg = state["config"]
        if paster.repaste(typing_mode=cfg.get("typing_mode", False)):
            print("[main] re-pasted last result")
        else:
            print("[main] nothing to re-paste")

    start_wake_listener_if_needed()
    repaste_chord = config.get("repaste_hotkey", "ctrl+shift+r")
    print("[main] hold the hotkey to dictate; press Escape to cancel; tray menu has Settings / History / Mode / Language / toggles / Quit")
    
    # Start hotkey listener on a background thread to avoid blocking the main thread
    # (which must run the Tk mainloop on macOS).
    def _start_hotkey_listener():
        try:
            hotkey.run(config["hotkey"], on_press_chord, on_release_chord, on_cancel, "esc", {repaste_chord: on_repaste})
        except PermissionError as e:
            if "not trusted" in str(e) or "accessibility" in str(e).lower():
                print("[main] ERROR: VoiceFlow needs Accessibility permissions to listen for the global hotkey.")
                print("[main] On macOS, go to System Preferences > Security & Privacy > Accessibility")
                print("[main] and add Terminal (or Python) to the list of allowed apps.")
            else:
                print(f"[main] hotkey permission error: {e}")
        except Exception as exc:  # noqa: BLE001
            print(f"[main] hotkey listener failed: {exc}")
            traceback.print_exc()
    
    listener_thread = threading.Thread(target=_start_hotkey_listener, daemon=True)
    listener_thread.start()

    # Tk mainloop must run on the main thread on macOS
    get_ui()._root.mainloop()


if __name__ == "__main__":
    main()
