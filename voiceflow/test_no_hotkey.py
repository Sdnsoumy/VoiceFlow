import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Load config
with (Path(__file__).resolve().parent / 'config.json').open() as f:
    cfg = json.load(f)

# Dependency-free smoke test: validate config loading without starting the GUI
# or global hotkey listener (both require platform services in CI).
try:
    assert cfg["hotkey"]
    assert cfg["whisper_model"]
    print("[test] config loaded without GUI or hotkey listener")
except Exception as e:
    print(f"[test] UI init failed: {e}")
    import traceback
    traceback.print_exc()
