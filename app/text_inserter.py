import ctypes
import time
import os
import pyperclip
import pyautogui
from PySide6.QtGui import QGuiApplication, QImage, QPixmap
from PySide6.QtCore import QBuffer, QIODevice

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05

user32 = ctypes.windll.user32

class TextInserter:
    """Safely captures target window and types/pastes text or images into any active Windows application."""

    def __init__(self, restore_clipboard: bool = True, paste_delay_ms: int = 100):
        self.restore_clipboard = restore_clipboard
        self.paste_delay = paste_delay_ms / 1000.0

    @staticmethod
    def get_foreground_window() -> int:
        """Returns the HWND of the currently active window."""
        try:
            return user32.GetForegroundWindow()
        except Exception:
            return 0

    @staticmethod
    def set_foreground_window(hwnd: int) -> bool:
        """Restores focus to the specified window handle."""
        if not hwnd or hwnd == 0:
            return False
        try:
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            cur_tid = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
            target_tid = user32.GetWindowThreadProcessId(hwnd, None)
            if cur_tid != target_tid:
                user32.AttachThreadInput(cur_tid, target_tid, True)
                user32.SetForegroundWindow(hwnd)
                user32.SetFocus(hwnd)
                user32.AttachThreadInput(cur_tid, target_tid, False)
            else:
                user32.SetForegroundWindow(hwnd)
                user32.SetFocus(hwnd)
            return True
        except Exception:
            return False

    def insert_text(self, text: str, target_hwnd: int = 0) -> bool:
        """
        Inserts Unicode text into the target active window using clipboard and Ctrl+V.
        """
        if not text:
            return False

        if target_hwnd and target_hwnd != 0:
            self.set_foreground_window(target_hwnd)
            time.sleep(0.12)

        try:
            pyperclip.copy(text)
            time.sleep(self.paste_delay)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.08)
            return True
        except Exception:
            try:
                pyautogui.write(text)
                return True
            except Exception:
                return False

    def insert_image(self, image_path: str, target_hwnd: int = 0) -> bool:
        """
        Copies image from file to Windows clipboard via PySide6 QClipboard and sends Ctrl+V.
        Supports PNG, BMP, JPEG and preserves original image format.
        """
        if not image_path or not os.path.exists(image_path):
            return False

        if target_hwnd and target_hwnd != 0:
            self.set_foreground_window(target_hwnd)
            time.sleep(0.15)

        try:
            qimg = QImage(image_path)
            if qimg.isNull():
                return False

            cb = QGuiApplication.clipboard()
            if cb:
                cb.setImage(qimg)
                time.sleep(max(self.paste_delay, 0.12))
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.08)
                return True
            return False
        except Exception:
            return False
