# Contributing to VoiceFlow

Thanks for helping improve VoiceFlow.

## Development setup

1. Install Python 3.11 and `ffmpeg`.
2. Create an environment in `voiceflow/`:

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Run checks before opening a pull request:

   ```bash
   python -m compileall -q voiceflow
   python voiceflow/test_no_hotkey.py
   ```

## Pull requests

- Explain the user-visible change and link the related issue.
- Keep changes focused and update documentation when behavior changes.
- Do not commit API keys, local history, model files, or generated build output.
- Include platform details for macOS, Windows, or Linux-specific changes.

## Commit messages

Use a short imperative subject, for example `Fix macOS hotkey startup`.
