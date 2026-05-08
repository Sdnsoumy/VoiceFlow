"""Register/unregister Voice Flow to launch at system login.

On Windows this uses the HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
registry key (per-user, non-admin).  On other platforms this is a no-op for now.
"""

from __future__ import annotations

import os
import sys


def _exe_path() -> str:
    """Return the path to the currently running executable / script."""
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(sys.argv[0])


def is_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ,
        )
        try:
            winreg.QueryValueEx(key, "VoiceFlow")
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:  # noqa: BLE001
        return False


def enable() -> None:
    if sys.platform != "win32":
        print("[startup] auto-launch is only supported on Windows currently")
        return
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        exe = _exe_path()
        # If running from source, wrap with pythonw to avoid a console window
        if not getattr(sys, "frozen", False):
            exe = f'"{sys.executable}" "{exe}"'
        winreg.SetValueEx(key, "VoiceFlow", 0, winreg.REG_SZ, exe)
        winreg.CloseKey(key)
        print("[startup] registered in HKCU Run")
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] failed to register: {exc}")


def disable() -> None:
    if sys.platform != "win32":
        return
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        try:
            winreg.DeleteValue(key, "VoiceFlow")
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        print("[startup] removed from HKCU Run")
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] failed to unregister: {exc}")


def set_enabled(enabled: bool) -> None:
    if enabled:
        enable()
    else:
        disable()

