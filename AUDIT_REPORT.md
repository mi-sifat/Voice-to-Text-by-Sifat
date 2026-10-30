# Project Audit Report — Sifat Voice Type (v1.1.0)

## 1. What Currently Works
- **Bangla & English Speech Recognition**: Free Google Speech Recognition API integration works reliably with WAV streaming.
- **Natural Punctuation**: Sentence-end forced '।' and ',' logic has been removed; explicit keywords ('দাঁড়ি', 'কমা') and questions ('?') work naturally.
- **Dual-Channel Mixed Mode**: Speech engine processes dual-channel English vs Bengali recognition to output proper Latin English script when English is spoken.
- **Global Hotkey Listening**: Pynput listener with RLock synchronization prevents deadlocks.
- **Single Instance Control**: Win32 Mutex `Global\SifatVoiceType_SingleInstance_Mutex` ensures single running instance.
- **Vercel Landing Page**: Clean static site with Google Drive installer link and feedback form.

## 2. What Needs Improvement & Fixes
- **Uninstallation Bug**: When uninstalling, if the app or background process is running, files could be locked, and child processes might stay active in Task Manager. The Inno Setup uninstaller needs a robust PreUninstall step using taskkill to guarantee no orphaned process remains.
- **Image Clipboard Support**: 
  - Standard clipboard paste (Ctrl+V) directly on the main application preview was limited to plain text.
  - Image copying from Chrome/Edge/Explorer must support multiple formats (DIB, PNG, HTML image src) and allow visual preview in both History tab and Clipboard popup.
  - Re-inserting image or pasting image into any active target window must be reliable.
- **Version Number Consistency**: Bump version to `1.1.0` across settings, UI, Inno Setup script, spec file, and documentation.
- **Production Build Sequence**: Rebuild fresh `SifatVoiceType.exe` using PyInstaller, test executable, then compile clean installer `SifatVoiceType_Setup_v1.1.0.exe` using Inno Setup 6 (`ISCC.exe`).

## 3. Implementation Plan
1. Update `app/text_inserter.py` and `app/clipboard_popup.py` to support full image preview, DIB/PNG extraction, and safe window paste.
2. Update `app/ui.py` with custom Ctrl+V event filter to handle pasted images directly in main UI window.
3. Enhance Inno Setup script (`installer/setup.iss`) to automatically kill running `SifatVoiceType.exe` processes during both install and uninstall.
4. Clean build directories, generate fresh `dist/SifatVoiceType.exe`, verify build timestamp, and compile `installer_output/SifatVoiceType_Setup_v1.1.0.exe`.
## 6. Image Clipboard Fix (v1.1.1)
- **Problem**: When copying images from browsers (Chrome/Edge) or File Explorer, text (such as URLs, HTML tags `<img src="...">`, or local paths) was captured in clipboard history instead of the actual image data.
- **Root Cause**: Chromium puts custom registered formats (`image/png`, `text/html`, `CF_DIB`) on the clipboard. PySide6 `QMimeData.hasImage()` returns `False` for `image/png` (it only checks Qt's internal `application/x-qt-image`), and `QClipboard.image()` returns null. This caused the clipboard listener to fall through to `mime.hasText()`, saving raw text/HTML instead of the image.
- **Solution**:
  - Implemented `app/clipboard_helper.py` with multi-tier image extraction:
    1. Direct MIME formats (`image/png`, `image/jpeg`, `image/bmp`).
    2. Qt `QClipboard.image()`.
    3. Windows native `CF_DIB` / `CF_DIBV5` via PIL `ImageGrab.grabclipboard()`.
    4. Local file URLs (`CF_HDROP` / `text/uri-list`) from Windows File Explorer.
    5. HTML data URIs (`data:image/...;base64,...`) and web image URLs (`<img src="...">`).
    6. Local file paths in text clipboard.
  - Implemented `set_windows_clipboard_image()` using native Win32 `CF_DIB` (with 64-bit safe pointers) and `QClipboard` for 100% paste compatibility in MS Office, Paint, browsers, Discord, WhatsApp, and Telegram.
  - Integrated with `TextInserter.insert_image()` and `MainWindow._on_clipboard_data_changed()`.
  - Added full test suite in `tests/test_clipboard_helper.py` (all 16 tests passing).


