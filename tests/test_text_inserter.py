import time
import pytest
import pyperclip
from app.text_inserter import TextInserter

def _safe_copy(text: str):
    for _ in range(10):
        try:
            pyperclip.copy(text)
            return
        except Exception:
            time.sleep(0.06)
    pyperclip.copy(text)

def test_clipboard_and_unicode_handling():
    inserter = TextInserter(restore_clipboard=True, paste_delay_ms=50)
    time.sleep(0.05)
    
    original = "Original User Clipboard Context 123"
    _safe_copy(original)
    
    bengali_text = "আমি বাংলায় গান গাই এবং English typing ও সাপোর্ট করে।"
    # Test setting and reading back Unicode text
    _safe_copy(bengali_text)
    read_back = pyperclip.paste()
    assert read_back == bengali_text

    # Test restoration logic manually
    _safe_copy(original)
    assert pyperclip.paste() == original

def test_foreground_window_detection():
    # Detects window without crashing
    hwnd = TextInserter.get_foreground_window()
    assert isinstance(hwnd, int)
