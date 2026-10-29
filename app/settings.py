import json
import os
from typing import Any, Dict

DEFAULT_SETTINGS: Dict[str, Any] = {
    # Hotkey trigger mode: 'push_to_talk' (hold to record, release to type) vs 'toggle' (press to start, press to stop)
    "trigger_mode": "push_to_talk",
    
    # Language-specific dedicated hotkeys requested by user:
    # 1. Ctrl + Win: Bengali
    # 2. Shift + Win: English
    # 3. Ctrl + Alt + Win: Mixed (Bangla + English)
    # 4. Ctrl + B: Clipboard History Floating Viewer
    "hotkey_bengali": "<ctrl>+<cmd>",
    "hotkey_english": "<shift>+<cmd>",
    "hotkey_mixed": "<ctrl>+<alt>+<cmd>",
    "hotkey_clipboard": "<ctrl>+b",
    
    # Active default language
    "language": "bn-BD",  # 'bn-BD', 'en-US', 'auto'
    "engine": "google_free",
    "restore_clipboard": True,
    "input_device_index": None,
    "save_history": True,
    "minimize_to_tray": True,
    "start_with_windows": True,
    "paste_delay_ms": 100,
    "sound_feedback": True
}

class SettingsManager:
    """Manages application settings stored in a local JSON file."""

    def __init__(self, config_dir: str = None):
        if config_dir is None:
            app_data = os.environ.get("APPDATA")
            if app_data:
                config_dir = os.path.join(app_data, "SifatVoiceType")
            else:
                config_dir = os.path.join(os.path.expanduser("~"), ".sifat_voice_type")
        self.config_dir = config_dir
        self.config_file = os.path.join(self.config_dir, "settings.json")
        self.settings: Dict[str, Any] = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self) -> None:
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
        except Exception:
            self.settings = DEFAULT_SETTINGS.copy()

    def save(self) -> bool:
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.settings[key] = value
        self.save()

    def reset(self) -> None:
        self.settings = DEFAULT_SETTINGS.copy()
        self.save()
