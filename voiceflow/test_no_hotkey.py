import json
import sys
sys.path.insert(0, '.')

# Load config
with open('config.json') as f:
    cfg = json.load(f)

# Test: verify the current UI entry point without starting the hotkey listener.
try:
    from gui.ui import UIThread, get
    assert callable(get)
    assert UIThread is not None
    print("[test] UI module loaded without hotkey listener")
except Exception as e:
    print(f"[test] UI init failed: {e}")
    import traceback
    traceback.print_exc()
