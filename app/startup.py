import os
import sys
import winreg

APP_NAME = "SifatVoiceType"
REG_RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

def set_start_with_windows(enable: bool) -> bool:
    """Configures Windows registry to launch SifatVoiceType on system startup."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REG_RUN_PATH,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
        )
    except Exception:
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH)
        except Exception:
            return False

    try:
        if enable:
            # Determine path to executable or script
            if getattr(sys, 'frozen', False):
                exe_path = f'"{sys.executable}"'
            else:
                exe_path = f'"{sys.executable}" "{os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))}"'
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception:
        if key:
            winreg.CloseKey(key)
        return False

def is_start_with_windows_enabled() -> bool:
    """Checks whether startup entry exists in HKCU registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return bool(val)
    except Exception:
        return False
