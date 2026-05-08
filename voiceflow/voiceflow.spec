

# PyInstaller spec for Voice Flow.
# Build (from voiceflow/ inside the activated venv):
#     pyinstaller voiceflow.spec
# Output ends up in `dist/VoiceFlow/`. Run `dist/VoiceFlow/VoiceFlow.exe`.
#
# Notes:
# - openai-whisper downloads its model into the user's home cache on first run;
#   the model is NOT bundled into the .exe (it's hundreds of MB and pulled on
#   demand). Whisper's `assets/mel_filters.npz` etc. are bundled via the
#   collect_data_files call below so the exe can run even without site-packages.
# - ffmpeg must still be on the user's PATH at runtime.
# - openwakeword is optional. If the user installed it into the same venv, it
#   gets picked up by collect_all; otherwise it's silently skipped.

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = []
datas += collect_data_files("whisper")
datas += [("config.json", "."), ("assets", "assets")]

hiddenimports = []
hiddenimports += collect_submodules("whisper")
hiddenimports += collect_submodules("sounddevice")
hiddenimports += collect_submodules("pystray")
hiddenimports += ["pyperclip", "pyautogui", "pynput.keyboard._win32"]

try:
    import openwakeword  # noqa: F401
    datas += collect_data_files("openwakeword")
    hiddenimports += collect_submodules("openwakeword")
    hiddenimports += collect_submodules("onnxruntime")
except ImportError:
    pass


a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VoiceFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # silent tray app — no console window
    icon="assets/icon.png",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="VoiceFlow",
)
