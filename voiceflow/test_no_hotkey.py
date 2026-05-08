import json
import sys
sys.path.insert(0, '.')

# Load config
with open('config.json') as f:
    cfg = json.load(f)

# Test: create the GUI without starting the hotkey listener
try:
    from gui.ui import init_ui
    root = init_ui(cfg)
    print("[test] UI initialized without hotkey listener")
    # Don't call mainloop yet; just see if init worked
except Exception as e:
    print(f"[test] UI init failed: {e}")
    import traceback
    traceback.print_exc()
