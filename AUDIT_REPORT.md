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
5. Run full test suite, commit changes to GitHub, and push.
