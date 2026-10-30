import os
import tempfile
import pytest
from app.settings import SettingsManager, DEFAULT_SETTINGS
from app.history import HistoryManager

def test_settings_load_save():
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SettingsManager(config_dir=tmpdir)
        assert sm.get("trigger_mode") == DEFAULT_SETTINGS["trigger_mode"]
        assert sm.get("hotkey_bengali") == DEFAULT_SETTINGS["hotkey_bengali"]
        assert sm.get("hotkey_english") == DEFAULT_SETTINGS["hotkey_english"]
        assert sm.get("hotkey_mixed") == DEFAULT_SETTINGS["hotkey_mixed"]
        
        # Modify and save
        sm.set("trigger_mode", "toggle")
        sm.set("hotkey_bengali", "<ctrl>+<alt>+b")
        sm.set("language", "en-US")
        assert sm.get("trigger_mode") == "toggle"
        assert sm.get("hotkey_bengali") == "<ctrl>+<alt>+b"
        assert sm.get("language") == "en-US"

        # Reload from same dir
        sm2 = SettingsManager(config_dir=tmpdir)
        assert sm2.get("trigger_mode") == "toggle"
        assert sm2.get("hotkey_bengali") == "<ctrl>+<alt>+b"
        assert sm2.get("language") == "en-US"

def test_history_management():
    with tempfile.TemporaryDirectory() as tmpdir:
        hm = HistoryManager(config_dir=tmpdir)
        assert len(hm.get_entries()) == 0

        # Add Bengali entry
        e1 = hm.add_entry("আমার নাম সিফাত। আমি একটি সফটওয়্যার বানাচ্ছি।", language="bn-BD")
        assert e1["text"] == "আমার নাম সিফাত। আমি একটি সফটওয়্যার বানাচ্ছি।"
        assert len(hm.get_entries()) == 1

        # Add mixed/English entry
        e2 = hm.add_entry("I am testing Python code on Windows 11.", language="en-US")
        assert len(hm.get_entries()) == 2
        assert hm.get_entries()[0]["id"] == e2["id"]

        # Delete single entry
        del_res = hm.delete_entry(e1["id"])
        assert del_res is True
        assert len(hm.get_entries()) == 1
        assert hm.get_entries()[0]["id"] == e2["id"]

        # Clear all
        hm.clear()
        assert len(hm.get_entries()) == 0

def test_history_consecutive_different_images():
    with tempfile.TemporaryDirectory() as tmpdir:
        hm = HistoryManager(config_dir=tmpdir)
        # Add 2 different images
        img1 = os.path.join(tmpdir, "img1.png")
        img2 = os.path.join(tmpdir, "img2.png")
        with open(img1, "w") as f: f.write("dummy1")
        with open(img2, "w") as f: f.write("dummy2")

        e1 = hm.add_entry(text="", item_type="image", image_path=img1)
        e2 = hm.add_entry(text="", item_type="image", image_path=img2)

        # Both should be present (not rejected as duplicates because paths differ)
        entries = hm.get_entries()
        assert len(entries) == 2
        assert entries[0]["image_path"] == img2
        assert entries[1]["image_path"] == img1

        # Adding same image path again should be deduplicated
        e3 = hm.add_entry(text="", item_type="image", image_path=img2)
        assert len(hm.get_entries()) == 2
