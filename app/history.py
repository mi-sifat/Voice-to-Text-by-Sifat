import json
import os
import time
from typing import List, Dict, Any, Optional

class HistoryManager:
    """
    Manages local clipboard and transcription history.
    Stores text transcriptions, copied clipboard texts, and image paths securely.
    """

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            app_data = os.environ.get("APPDATA")
            if app_data:
                config_dir = os.path.join(app_data, "SifatVoiceType")
            else:
                config_dir = os.path.join(os.path.expanduser("~"), ".sifat_voice_type")
        self.config_dir = config_dir
        self.history_file = os.path.join(self.config_dir, "history.json")
        self.images_dir = os.path.join(self.config_dir, "clipboard_images")
        self.entries: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.entries = json.load(f)
                    if not isinstance(self.entries, list):
                        self.entries = []
            else:
                self.entries = []
        except Exception:
            self.entries = []

    def save(self) -> bool:
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def add_entry(self, text: str, language: str = "bn-BD", item_type: str = "text", image_path: Optional[str] = None) -> Dict[str, Any]:
        text = text.strip() if text else ""
        if not text and not image_path:
            return {}

        # Don't add duplicate if the newest entry is identical
        if self.entries and self.entries[0].get("text") == text and self.entries[0].get("type") == item_type:
            return self.entries[0]

        entry_id = int(time.time() * 1000)
        existing_ids = {e.get("id") for e in self.entries}
        while entry_id in existing_ids:
            entry_id += 1

        entry = {
            "id": entry_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "text": text,
            "language": language,
            "type": item_type,  # 'text', 'voice', or 'image'
            "image_path": image_path
        }
        self.entries.insert(0, entry)
        if len(self.entries) > 300:
            self.entries = self.entries[:300]
        self.save()
        return entry

    def save_clipboard_image(self, pil_image) -> Optional[str]:
        """Saves a PIL image from clipboard to disk and returns its file path."""
        try:
            os.makedirs(self.images_dir, exist_ok=True)
            filename = f"clip_{int(time.time() * 1000)}.png"
            filepath = os.path.join(self.images_dir, filename)
            pil_image.save(filepath, format="PNG")
            return filepath
        except Exception:
            return None

    def get_entries(self) -> List[Dict[str, Any]]:
        return list(self.entries)

    def delete_entry(self, entry_id: int) -> bool:
        initial_len = len(self.entries)
        # Also clean up image file if present
        for e in self.entries:
            if e.get("id") == entry_id and e.get("image_path"):
                try:
                    if os.path.exists(e["image_path"]):
                        os.remove(e["image_path"])
                except Exception:
                    pass
        self.entries = [e for e in self.entries if e.get("id") != entry_id]
        if len(self.entries) != initial_len:
            self.save()
            return True
        return False

    def clear(self) -> bool:
        self.entries.clear()
        # Clean up cached clipboard images
        if os.path.exists(self.images_dir):
            try:
                for f in os.listdir(self.images_dir):
                    os.remove(os.path.join(self.images_dir, f))
            except Exception:
                pass
        return self.save()
