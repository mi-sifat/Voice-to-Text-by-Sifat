import sys
import os
import threading
import time
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot, QTimer, QSize
from PySide6.QtGui import QFont, QAction, QIcon, QPixmap, QCursor, QImage
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QTabWidget, QListWidget,
    QListWidgetItem, QCheckBox, QSpinBox, QLineEdit, QSystemTrayIcon,
    QMenu, QFrame, QMessageBox, QProgressBar, QRadioButton, QButtonGroup,
    QGroupBox, QDialog
)
import pyperclip

from app.settings import SettingsManager
from app.history import HistoryManager
from app.recorder import AudioRecorder
from app.speech_engine import SpeechEngine
from app.text_inserter import TextInserter
from app.hotkeys import GlobalHotkeyManager
from app.key_recorder import KeyRecorderDialog
from app.clipboard_popup import ClipboardPopupDialog
from app.clipboard_helper import extract_clipboard_image, set_windows_clipboard_image
from app.startup import set_start_with_windows, is_start_with_windows_enabled

STYLE = """
QMainWindow, QWidget {
    background-color: #0A0D14;
    color: #E2E8F0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #1A233A;
    background: #0E1321;
    border-radius: 12px;
}
QTabBar::tab {
    background: #111728;
    color: #8DA4C4;
    padding: 12px 28px;
    margin-right: 6px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background: #1B2544;
    color: #60A5FA;
    border-bottom: 3px solid #3B82F6;
}
QGroupBox {
    background-color: #0F162A;
    border: 1px solid #1E294B;
    border-radius: 12px;
    padding: 18px;
    margin-top: 14px;
}
QGroupBox::title {
    color: #60A5FA;
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 10px;
    font-weight: bold;
}
QFrame#card {
    background-color: #0F162A;
    border: 1px solid #1E294B;
    border-radius: 12px;
    padding: 16px;
}
QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: bold;
    font-size: 13px;
}
QPushButton:hover { background-color: #1D4ED8; }
QPushButton:pressed { background-color: #1E40AF; }
QPushButton#recordBtn {
    font-size: 15px;
    padding: 16px 36px;
    border-radius: 28px;
    font-weight: 700;
}
QPushButton#recordBtn.recording { background-color: #DC2626; }
QPushButton.secondary {
    background-color: #18223D;
    color: #93C5FD;
    border: 1px solid #233560;
}
QPushButton.secondary:hover { background-color: #233560; color: #FFFFFF; }
QPushButton.danger { background-color: #991B1B; color: #FEE2E2; }
QPushButton.danger:hover { background-color: #7F1D1D; }
QComboBox, QLineEdit, QSpinBox {
    background-color: #0A0E1A;
    border: 1px solid #1F2A4C;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F1F5F9;
}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus { border: 1px solid #3B82F6; }
QComboBox::drop-down { border: none; }
QTextEdit, QListWidget {
    background-color: #0A0E1A;
    border: 1px solid #1F2A4C;
    border-radius: 10px;
    padding: 12px;
    color: #F8FAFC;
    font-size: 14px;
}
QProgressBar {
    background-color: #151D33;
    border: none;
    border-radius: 4px;
}
QProgressBar::chunk { background-color: #38BDF8; border-radius: 4px; }
QLabel { color: #E2E8F0; }
QLabel.subtext { color: #8899B5; font-size: 12px; }
QCheckBox, QRadioButton { spacing: 10px; color: #E2E8F0; }
QCheckBox::indicator, QRadioButton::indicator {
    width: 18px; height: 18px; border-radius: 4px;
    border: 1px solid #2A3B66; background-color: #0A0E1A;
}
QRadioButton::indicator { border-radius: 9px; }
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #2563EB; border-color: #38BDF8;
}
"""

class MainWindow(QMainWindow):
    sig_status = Signal(str, str)
    sig_transcription = Signal(str)
    sig_error = Signal(str)
    sig_volume = Signal(float)
    sig_start_rec = Signal(str)
    sig_stop_rec = Signal(str)
    sig_toggle_rec = Signal(str)
    sig_show_clipboard = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sifat Voice Type")
        self.resize(860, 720)
        self.setStyleSheet(STYLE)

        icon_path = os.path.join(os.path.dirname(__file__), "..", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.settings = SettingsManager()
        self.history = HistoryManager()
        self.recorder = AudioRecorder()
        self.speech_engine = SpeechEngine()
        self.text_inserter = TextInserter(
            restore_clipboard=self.settings.get("restore_clipboard", True),
            paste_delay_ms=self.settings.get("paste_delay_ms", 100)
        )

        self.target_hwnd = 0
        self.active_lang = self.settings.get("language", "bn-BD")
        self._popup: Optional[ClipboardPopupDialog] = None

        # ── Single HotkeyManager, never re-created ──
        self.hotkey_manager = GlobalHotkeyManager(
            mode=self.settings.get("trigger_mode", "push_to_talk"),
            on_start_recording=lambda lang: self.sig_start_rec.emit(lang),
            on_stop_recording=lambda lang: self.sig_stop_rec.emit(lang),
            on_toggle_recording=lambda lang: self.sig_toggle_rec.emit(lang),
            on_clipboard_triggered=lambda: self.sig_show_clipboard.emit()
        )
        self._apply_saved_hotkeys()
        self.hotkey_manager.start()

        self.recorder.on_volume_callback = lambda v: self.sig_volume.emit(v)

        self.sig_status.connect(self._on_status)
        self.sig_transcription.connect(self._on_transcription)
        self.sig_error.connect(self._on_error)
        self.sig_volume.connect(self._on_volume)
        self.sig_start_rec.connect(self._on_hotkey_start)
        self.sig_stop_rec.connect(self._on_hotkey_stop)
        self.sig_toggle_rec.connect(self._on_hotkey_toggle)
        self.sig_show_clipboard.connect(self._show_clipboard_popup)

        # ── Clipboard Monitor (Auto captures copied texts and images) ──
        self.last_clip_text = ""
        self.last_image_hash = ""
        self._qclip = QApplication.clipboard()
        if self._qclip:
            self._qclip.dataChanged.connect(self._on_clipboard_data_changed)

        self._build_ui()
        self._build_tray()
        self._load_devices()

    # ─── Hotkey helpers (NO start() inside _apply_saved_hotkeys) ───────────

    def _apply_saved_hotkeys(self):
        """Push current settings into the manager without touching the listener."""
        self.hotkey_manager.set_hotkeys(
            bn_hk=self.settings.get("hotkey_bengali", "<ctrl>+<cmd>"),
            en_hk=self.settings.get("hotkey_english", "<shift>+<cmd>"),
            mixed_hk=self.settings.get("hotkey_mixed", "<ctrl>+<alt>+<cmd>"),
            clip_hk=self.settings.get("hotkey_clipboard", "<ctrl>+b"),
            mode=self.settings.get("trigger_mode", "push_to_talk")
        )

    def _restart_hotkeys(self):
        """Fully restart listener after config changes."""
        self.hotkey_manager.stop()
        self._apply_saved_hotkeys()
        self.hotkey_manager.start()
        self._update_badges()

    def _format_hk(self, hk: str) -> str:
        return hk.replace("<cmd>", "Win").replace("<", "").replace(">", "").upper()

    def _update_badges(self):
        bn = self.settings.get("hotkey_bengali", "<ctrl>+<cmd>")
        en = self.settings.get("hotkey_english", "<shift>+<cmd>")
        mx = self.settings.get("hotkey_mixed", "<ctrl>+<alt>+<cmd>")
        cl = self.settings.get("hotkey_clipboard", "<ctrl>+b")
        self.lbl_bn_badge.setText(f"🇧🇩 বাংলা: {self._format_hk(bn)}")
        self.lbl_en_badge.setText(f"🇺🇸 English: {self._format_hk(en)}")
        self.lbl_mix_badge.setText(f"🌐 Mixed: {self._format_hk(mx)}")
        self.lbl_clip_badge.setText(f"📋 Clip: {self._format_hk(cl)}")
        # Also update Settings tab labels
        if hasattr(self, "lbl_s_bn"):
            self.lbl_s_bn.setText(self._format_hk(bn))
            self.lbl_s_en.setText(self._format_hk(en))
            self.lbl_s_mix.setText(self._format_hk(mx))
            self.lbl_s_clip.setText(self._format_hk(cl))

    def _record_shortcut(self, key_setting: str):
        """Open key-capture dialog, save, and restart hotkeys exactly once."""
        self.hotkey_manager.stop()
        dlg = KeyRecorderDialog(title=f"Press new shortcut — {key_setting}", parent=self)
        result = dlg.exec()
        if result == QDialog.Accepted:
            shortcut = dlg.get_shortcut()
            if shortcut:
                self.settings.set(key_setting, shortcut)
        # Always restart exactly once
        self._apply_saved_hotkeys()
        self.hotkey_manager.start()
        self._update_badges()

    # ─── UI Build ─────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(24, 20, 24, 20)
        vbox.setSpacing(14)

        # Header
        hdr = QHBoxLayout()
        icon_path = os.path.join(os.path.dirname(__file__), "..", "app_icon.png")
        if os.path.exists(icon_path):
            pix_lbl = QLabel()
            pix_lbl.setPixmap(QPixmap(icon_path).scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            hdr.addWidget(pix_lbl)

        title_v = QVBoxLayout()
        title_lbl = QLabel("Sifat Voice Type")
        title_lbl.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title_lbl.setStyleSheet("color:#60A5FA;")
        title_v.addWidget(title_lbl)
        sub = QLabel("AI Voice Typing for Windows • Bangla / English / Mixed")
        sub.setProperty("class", "subtext")
        title_v.addWidget(sub)
        hdr.addLayout(title_v)
        hdr.addStretch()

        self.status_badge = QLabel("Ready")
        self.status_badge.setStyleSheet(
            "background:#0E2038;color:#38BDF8;border:1px solid #38BDF8;"
            "border-radius:14px;padding:6px 18px;font-weight:bold;"
        )
        hdr.addWidget(self.status_badge)
        vbox.addLayout(hdr)

        tabs = QTabWidget()
        tabs.addTab(self._tab_voice(), "Voice Typing")
        tabs.addTab(self._tab_history(), "History")
        tabs.addTab(self._tab_settings(), "Settings")
        vbox.addWidget(tabs)

    def _tab_voice(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # Card
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setSpacing(12)

        # Row 1: Language + Mic
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Language:"))
        self.combo_lang = QComboBox()
        self.combo_lang.addItem("বাংলা (Bengali)", "bn-BD")
        self.combo_lang.addItem("English (US)", "en-US")
        self.combo_lang.addItem("Bangla + English (Mixed)", "auto")
        idx = self.combo_lang.findData(self.settings.get("language", "bn-BD"))
        self.combo_lang.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo_lang.currentIndexChanged.connect(
            lambda: self.settings.set("language", self.combo_lang.currentData())
        )
        row1.addWidget(self.combo_lang, 1)
        row1.addSpacing(12)
        row1.addWidget(QLabel("Microphone:"))
        self.combo_mic = QComboBox()
        self.combo_mic.currentIndexChanged.connect(self._on_mic_changed)
        row1.addWidget(self.combo_mic, 2)
        cl.addLayout(row1)

        # Hotkey badges row
        badges = QHBoxLayout()
        badges.setSpacing(8)
        self.lbl_bn_badge = QLabel()
        self.lbl_bn_badge.setStyleSheet("background:#0E2922;color:#34D399;padding:6px 10px;border-radius:6px;font-weight:600;")
        self.lbl_en_badge = QLabel()
        self.lbl_en_badge.setStyleSheet("background:#14224A;color:#60A5FA;padding:6px 10px;border-radius:6px;font-weight:600;")
        self.lbl_mix_badge = QLabel()
        self.lbl_mix_badge.setStyleSheet("background:#251B3D;color:#C084FC;padding:6px 10px;border-radius:6px;font-weight:600;")
        self.lbl_clip_badge = QLabel()
        self.lbl_clip_badge.setStyleSheet("background:#2B2117;color:#FBBF24;padding:6px 10px;border-radius:6px;font-weight:600;")
        for b in [self.lbl_bn_badge, self.lbl_en_badge, self.lbl_mix_badge, self.lbl_clip_badge]:
            badges.addWidget(b)
        cl.addLayout(badges)
        self._update_badges()

        # Record button + hint + volume bar
        btn_area = QVBoxLayout()
        btn_area.setAlignment(Qt.AlignCenter)
        self.btn_record = QPushButton("● Start Recording")
        self.btn_record.setObjectName("recordBtn")
        self.btn_record.setCursor(Qt.PointingHandCursor)
        self.btn_record.clicked.connect(self.toggle_recording)
        btn_area.addWidget(self.btn_record)

        mode = self.settings.get("trigger_mode", "push_to_talk")
        mode_txt = "Hold hotkey → speak → release to type" if mode == "push_to_talk" else "Press hotkey to start/stop"
        self.lbl_hint = QLabel(f"Mode: {mode_txt}")
        self.lbl_hint.setProperty("class", "subtext")
        self.lbl_hint.setAlignment(Qt.AlignCenter)
        btn_area.addWidget(self.lbl_hint)

        self.audio_bar = QProgressBar()
        self.audio_bar.setRange(0, 100)
        self.audio_bar.setValue(0)
        self.audio_bar.setTextVisible(False)
        self.audio_bar.setFixedHeight(8)
        btn_area.addWidget(self.audio_bar)
        cl.addLayout(btn_area)
        lay.addWidget(card)

        # Transcription preview
        lay.addWidget(QLabel("Last Recognized Text:", styleSheet="font-weight:bold;color:#93C5FD;"))
        self.text_preview = QTextEdit()
        self.text_preview.setPlaceholderText("Recognized speech will appear here…")
        lay.addWidget(self.text_preview)

        # Action row
        acts = QHBoxLayout()
        btn_copy = QPushButton("📋 Copy")
        btn_copy.setProperty("class", "secondary")
        btn_copy.clicked.connect(lambda: pyperclip.copy(self.text_preview.toPlainText()) or self._set_status("Copied!", "#34D399"))
        acts.addWidget(btn_copy)

        btn_clr = QPushButton("🗑️ Clear")
        btn_clr.setProperty("class", "secondary")
        btn_clr.clicked.connect(self.text_preview.clear)
        acts.addWidget(btn_clr)
        acts.addStretch()

        btn_clipview = QPushButton("📋 Clipboard Viewer")
        btn_clipview.setProperty("class", "secondary")
        btn_clipview.clicked.connect(self._show_clipboard_popup)
        acts.addWidget(btn_clipview)

        btn_reinsert = QPushButton("↵ Re-Insert")
        btn_reinsert.clicked.connect(self._reinsert)
        acts.addWidget(btn_reinsert)
        lay.addLayout(acts)

        return w

    def _tab_history(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        info = QLabel("Local transcription history — stored only on your PC")
        info.setProperty("class", "subtext")
        lay.addWidget(info)

        self.list_history = QListWidget()
        lay.addWidget(self.list_history)

        acts = QHBoxLayout()
        b1 = QPushButton("📋 Copy Selected")
        b1.setProperty("class", "secondary")
        b1.clicked.connect(self._hist_copy)
        acts.addWidget(b1)
        b2 = QPushButton("Delete Selected")
        b2.setProperty("class", "danger")
        b2.clicked.connect(self._hist_delete)
        acts.addWidget(b2)
        acts.addStretch()
        b3 = QPushButton("Clear All")
        b3.setProperty("class", "danger")
        b3.clicked.connect(self._hist_clear)
        acts.addWidget(b3)
        lay.addLayout(acts)
        self._refresh_history()
        return w

    def _tab_settings(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # ── Mode ──
        grp_mode = QGroupBox("Recording Trigger Mode")
        ml = QVBoxLayout(grp_mode)
        self.btn_grp = QButtonGroup(self)
        self.radio_ptt = QRadioButton("Hold to Speak (Push-to-Talk) [Recommended] — ধরে রাখুন, ছেড়ে দিলে টাইপ হবে")
        self.radio_tog = QRadioButton("Toggle (Press once to start, press again to stop)")
        self.btn_grp.addButton(self.radio_ptt)
        self.btn_grp.addButton(self.radio_tog)
        ml.addWidget(self.radio_ptt)
        ml.addWidget(self.radio_tog)
        # Reflect saved mode
        if self.settings.get("trigger_mode") == "toggle":
            self.radio_tog.setChecked(True)
        else:
            self.radio_ptt.setChecked(True)
        self.radio_ptt.toggled.connect(self._on_mode_changed)
        lay.addWidget(grp_mode)

        # ── Hotkeys — interactive key capture ──
        grp_hk = QGroupBox("Language Hotkeys — Click 'Change' then press your keys")
        hkl = QVBoxLayout(grp_hk)
        hkl.setSpacing(10)

        def hk_row(label_txt, setting_key, color):
            row = QHBoxLayout()
            lbl = QLabel(label_txt)
            lbl.setFixedWidth(175)
            row.addWidget(lbl)
            val_lbl = QLabel(self._format_hk(self.settings.get(setting_key, "")))
            val_lbl.setStyleSheet(f"font-weight:bold;color:{color};min-width:120px;")
            row.addWidget(val_lbl, 1)
            btn = QPushButton("⌨️ Change (Press Keys)")
            btn.setProperty("class", "secondary")
            btn.clicked.connect(lambda checked=False, sk=setting_key: self._record_shortcut(sk))
            row.addWidget(btn)
            return row, val_lbl

        r1, self.lbl_s_bn = hk_row("🇧🇩 বাংলা (Bengali):", "hotkey_bengali", "#34D399")
        r2, self.lbl_s_en = hk_row("🇺🇸 English:", "hotkey_english", "#60A5FA")
        r3, self.lbl_s_mix = hk_row("🌐 Mixed (বাংলা+English):", "hotkey_mixed", "#C084FC")
        r4, self.lbl_s_clip = hk_row("📋 Clipboard Viewer:", "hotkey_clipboard", "#FBBF24")
        for r in [r1, r2, r3, r4]:
            hkl.addLayout(r)
        lay.addWidget(grp_hk)

        # ── Preferences ──
        grp_pref = QGroupBox("System Preferences")
        pl = QVBoxLayout(grp_pref)
        pl.setSpacing(10)

        self.chk_startup = QCheckBox("Start with Windows (auto-launch in system tray on boot)")
        self.chk_startup.setChecked(self.settings.get("start_with_windows", False))
        self.chk_startup.stateChanged.connect(self._on_startup_toggle)
        pl.addWidget(self.chk_startup)

        self.chk_clipboard_restore = QCheckBox("Preserve clipboard content after voice paste")
        self.chk_clipboard_restore.setChecked(self.settings.get("restore_clipboard", True))
        self.chk_clipboard_restore.stateChanged.connect(
            lambda s: self.settings.set("restore_clipboard", s == Qt.Checked)
        )
        pl.addWidget(self.chk_clipboard_restore)

        self.chk_history = QCheckBox("Save transcriptions to local history")
        self.chk_history.setChecked(self.settings.get("save_history", True))
        self.chk_history.stateChanged.connect(
            lambda s: self.settings.set("save_history", s == Qt.Checked)
        )
        pl.addWidget(self.chk_history)

        self.chk_tray = QCheckBox("Minimize to system tray on window close")
        self.chk_tray.setChecked(self.settings.get("minimize_to_tray", True))
        self.chk_tray.stateChanged.connect(
            lambda s: self.settings.set("minimize_to_tray", s == Qt.Checked)
        )
        pl.addWidget(self.chk_tray)

        delay_row = QHBoxLayout()
        delay_row.addWidget(QLabel("Paste Delay (ms):"))
        self.spin_delay = QSpinBox()
        self.spin_delay.setRange(20, 1000)
        self.spin_delay.setValue(self.settings.get("paste_delay_ms", 100))
        self.spin_delay.valueChanged.connect(lambda v: self.settings.set("paste_delay_ms", v))
        delay_row.addWidget(self.spin_delay)
        delay_row.addStretch()
        pl.addLayout(delay_row)
        lay.addWidget(grp_pref)

        # ── Save Settings Button ──
        btn_save_settings = QPushButton("💾 সেটিংস সংরক্ষণ করুন (Save Settings)")
        btn_save_settings.setObjectName("recordBtn")
        btn_save_settings.clicked.connect(self._save_all_settings)
        lay.addWidget(btn_save_settings)

        lay.addStretch()
        return w

    # ─── Tray ──────────────────────────────────────────────────────────────

    def _build_tray(self):
        icon_path = os.path.join(os.path.dirname(__file__), "..", "app_icon.png")
        self.tray = QSystemTrayIcon(self)
        if os.path.exists(icon_path):
            self.tray.setIcon(QIcon(icon_path))
        menu = QMenu()
        menu.addAction("Show", self.showNormal)
        menu.addAction("Clipboard Viewer", self._show_clipboard_popup)
        menu.addSeparator()
        menu.addAction("Exit", QApplication.instance().quit)
        self.tray.setContextMenu(menu)
        self.tray.show()

    # ─── Devices ───────────────────────────────────────────────────────────

    def _load_devices(self):
        self.combo_mic.blockSignals(True)
        self.combo_mic.clear()
        devices = self.recorder.get_input_devices()
        saved = self.settings.get("input_device_index")
        sel = 0
        for i, dev in enumerate(devices):
            self.combo_mic.addItem(dev["name"], dev["index"])
            if saved is not None and dev["index"] == saved:
                sel = i
        self.combo_mic.setCurrentIndex(sel)
        self.combo_mic.blockSignals(False)
        if devices:
            self.recorder.set_device(self.combo_mic.currentData())

    def _on_mic_changed(self):
        idx = self.combo_mic.currentData()
        self.recorder.set_device(idx)
        self.settings.set("input_device_index", idx)

    # ─── Mode toggle ───────────────────────────────────────────────────────

    def _on_mode_changed(self):
        mode = "push_to_talk" if self.radio_ptt.isChecked() else "toggle"
        self.settings.set("trigger_mode", mode)
        mode_txt = "Hold hotkey → speak → release to type" if mode == "push_to_talk" else "Press hotkey to start/stop"
        self.lbl_hint.setText(f"Mode: {mode_txt}")
        self._restart_hotkeys()

    # ─── Settings Save ─────────────────────────────────────────────────────

    def _save_all_settings(self):
        """Explicitly saves all settings and notifies the user."""
        mode = "push_to_talk" if self.radio_ptt.isChecked() else "toggle"
        self.settings.set("trigger_mode", mode)
        self.settings.set("start_with_windows", self.chk_startup.isChecked())
        self.settings.set("restore_clipboard", self.chk_clipboard_restore.isChecked())
        self.settings.set("save_history", self.chk_history.isChecked())
        self.settings.set("minimize_to_tray", self.chk_tray.isChecked())
        self.settings.set("paste_delay_ms", self.spin_delay.value())
        self.settings.save()
        self._restart_hotkeys()
        self._set_status("Settings Saved ✓", "#34D399")
        QMessageBox.information(self, "সেটিংস", "সবগুলো সেটিংস এবং শর্টকাট সফলভাবে সংরক্ষণ করা হয়েছে!")

    # ─── Startup ───────────────────────────────────────────────────────────

    def _on_startup_toggle(self, state):
        enabled = state == Qt.Checked
        self.settings.set("start_with_windows", enabled)
        if not set_start_with_windows(enabled):
            QMessageBox.warning(self, "Startup", "Could not update Windows registry startup entry.")

    # ─── Clipboard monitor & popup ──────────────────────────────────────────

    def _on_clipboard_data_changed(self):
        """Instant event-driven capture for copied text and images (browser, files, apps)."""
        try:
            if not self._qclip:
                return

            mime = self._qclip.mimeData()
            if mime is None:
                return

            # Multi-tier image extraction (handles Chrome 'Copy image', Snipping Tool, CF_DIB, HTML <img>, files)
            qimg, src = extract_clipboard_image(mime=mime, qclip=self._qclip)
            if qimg is not None and not qimg.isNull():
                img_sig = f"{qimg.width()}x{qimg.height()}_{qimg.bytesPerLine()}_{qimg.format().value}"
                if img_sig != self.last_image_hash:
                    self.last_image_hash = img_sig
                    os.makedirs(self.history.images_dir, exist_ok=True)
                    img_path = os.path.join(self.history.images_dir, f"clip_{int(time.time() * 1000)}.png")
                    if qimg.save(img_path, "PNG"):
                        self.history.add_entry(text="", language="", item_type="image", image_path=img_path)
                        self._refresh_history()
                return  # Always return: Never fall through to text handler when clipboard has an image

            # Check if clipboard has text
            if mime.hasText() or self._qclip.text():
                txt = self._qclip.text()
                if txt and txt.strip() and txt != self.last_clip_text:
                    self.last_clip_text = txt
                    entries = self.history.get_entries()
                    if not entries or entries[0].get("text") != txt:
                        self.history.add_entry(text=txt, language="", item_type="text")
                        self._refresh_history()
        except Exception:
            pass

    @Slot()
    def _show_clipboard_popup(self):
        captured_hwnd = self.text_inserter.get_foreground_window()
        entries = self.history.get_entries()

        # If popup exists and is visible, bring it to front
        if self._popup is not None:
            try:
                if self._popup.isVisible():
                    self._popup.activateWindow()
                    self._popup.raise_()
                    return
                else:
                    self._popup.close()
            except Exception:
                pass
            self._popup = None

        self._popup = ClipboardPopupDialog(entries=entries, target_hwnd=captured_hwnd, parent=None)
        self._popup.item_selected.connect(lambda entry: self._paste_entry_from_popup(entry, captured_hwnd))
        self._popup.clear_requested.connect(self._clear_all_clipboard)
        self._popup.show()
        self._popup.raise_()
        self._popup.activateWindow()

    def _paste_entry_from_popup(self, entry: dict, hwnd: int):
        item_type = entry.get("type", "text")
        if item_type == "image":
            img_path = entry.get("image_path")
            threading.Thread(target=lambda: (time.sleep(0.15), self.text_inserter.insert_image(img_path, target_hwnd=hwnd)), daemon=True).start()
        else:
            text = entry.get("text", "")
            threading.Thread(target=lambda: (time.sleep(0.15), self.text_inserter.insert_text(text, target_hwnd=hwnd)), daemon=True).start()

    def _clear_all_clipboard(self):
        self.history.clear()
        self.last_clip_text = ""
        try:
            pyperclip.copy("")
        except Exception:
            pass
        self._refresh_history()

    # ─── Recording ─────────────────────────────────────────────────────────

    @Slot(str)
    def _on_hotkey_start(self, lang: str):
        if not self.recorder.is_recording:
            self.active_lang = lang
            self._start_rec()

    @Slot(str)
    def _on_hotkey_stop(self, lang: str):
        if self.recorder.is_recording:
            self._stop_rec()

    @Slot(str)
    def _on_hotkey_toggle(self, lang: str):
        self.active_lang = lang
        self.toggle_recording()

    def toggle_recording(self):
        if not self.recorder.is_recording:
            self._start_rec()
        else:
            self._stop_rec()

    def _start_rec(self):
        self.target_hwnd = self.text_inserter.get_foreground_window()
        try:
            self.recorder.start_recording()
            lang_name = {"bn-BD": "বাংলা", "en-US": "English"}.get(self.active_lang, "Mixed")
            self._set_status(f"Listening ({lang_name})…", "#EF4444")
            self.btn_record.setText(f"■ Listening ({lang_name})… Release to stop")
            self.btn_record.setProperty("class", "recording")
            self.btn_record.style().unpolish(self.btn_record)
            self.btn_record.style().polish(self.btn_record)
        except Exception as e:
            self.sig_error.emit(f"Microphone Error: {e}")

    def _stop_rec(self):
        self._set_status("Transcribing…", "#F59E0B")
        self.btn_record.setText("Processing…")
        self.btn_record.setEnabled(False)
        self.audio_bar.setValue(0)
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            wav = self.recorder.stop_recording()
            if not wav:
                self._set_status("No audio captured", "#8899B5")
                self._reset_btn()
                return
            text = self.speech_engine.transcribe(wav, language=self.active_lang)
            if text:
                self.sig_transcription.emit(text)
            else:
                self._set_status("Could not recognize speech", "#8899B5")
                self._reset_btn()
        except ConnectionError as e:
            self.sig_error.emit(f"Network Error: {e}")
            self._reset_btn()
        except Exception as e:
            self.sig_error.emit(f"Transcription error: {e}")
            self._reset_btn()

    def _reset_btn(self):
        QTimer.singleShot(0, self._do_reset_btn)

    def _do_reset_btn(self):
        self.btn_record.setText("● Start Recording")
        self.btn_record.setProperty("class", "")
        self.btn_record.setEnabled(True)
        self.btn_record.style().unpolish(self.btn_record)
        self.btn_record.style().polish(self.btn_record)

    # ─── Signal slots ──────────────────────────────────────────────────────

    @Slot(str)
    def _on_transcription(self, text: str):
        self.text_preview.setText(text)
        self._set_status("Pasting into window…", "#3B82F6")
        if self.settings.get("save_history", True):
            self.history.add_entry(text, language=self.active_lang)
            self._refresh_history()
        ok = self.text_inserter.insert_text(text, target_hwnd=self.target_hwnd)
        self._set_status("Pasted ✓" if ok else "Copied to clipboard", "#34D399" if ok else "#F59E0B")
        self._do_reset_btn()

    @Slot(str, str)
    def _on_status(self, msg: str, color: str):
        self._set_status(msg, color)

    def _set_status(self, msg: str, color: str = "#38BDF8"):
        self.status_badge.setText(msg)
        self.status_badge.setStyleSheet(
            f"background:#0E2038;color:{color};border:1px solid {color};"
            "border-radius:14px;padding:6px 18px;font-weight:bold;"
        )

    @Slot(str)
    def _on_error(self, msg: str):
        self._set_status("Error", "#DC2626")
        QMessageBox.warning(self, "Sifat Voice Type", msg)

    @Slot(float)
    def _on_volume(self, vol: float):
        self.audio_bar.setValue(min(100, int(vol / 400 * 100)))

    # ─── History helpers ───────────────────────────────────────────────────

    def _refresh_history(self):
        self.list_history.clear()
        self.list_history.setIconSize(QSize(36, 36))
        for e in self.history.get_entries():
            item_type = e.get("type", "text")
            ts = e.get("timestamp", "")
            img_path = e.get("image_path")
            if item_type == "image" and img_path and os.path.exists(img_path):
                item = QListWidgetItem(f"[{ts}] 🖼️ [Image/ছবি]")
                pix = QPixmap(img_path)
                if not pix.isNull():
                    item.setIcon(QIcon(pix.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            else:
                lang = f"({e.get('language')})" if e.get('language') else ""
                item = QListWidgetItem(f"[{ts}] {lang} {e.get('text', '')}")
            item.setData(Qt.UserRole, e["id"])
            self.list_history.addItem(item)

    def _hist_copy(self):
        item = self.list_history.currentItem()
        if item:
            eid = item.data(Qt.UserRole)
            for e in self.history.get_entries():
                if e["id"] == eid:
                    if e.get("type") == "image" and e.get("image_path"):
                        if set_windows_clipboard_image(e["image_path"], self._qclip):
                            self._set_status("Image Copied to Clipboard!", "#34D399")
                        else:
                            self._set_status("Failed to copy image", "#EF4444")
                    else:
                        pyperclip.copy(e.get("text", ""))
                        self._set_status("Text Copied!", "#34D399")
                    return

    def _hist_delete(self):
        item = self.list_history.currentItem()
        if item:
            self.history.delete_entry(item.data(Qt.UserRole))
            self._refresh_history()

    def _hist_clear(self):
        if QMessageBox.question(self, "Clear History", "Delete all history?") == QMessageBox.Yes:
            self.history.clear()
            self._refresh_history()

    # ─── Re-insert ─────────────────────────────────────────────────────────

    def _reinsert(self):
        text = self.text_preview.toPlainText()
        if text:
            self.hide()
            time.sleep(0.3)
            self.text_inserter.insert_text(text, target_hwnd=0)
            self.showNormal()

    # ─── Close ─────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        if self.settings.get("minimize_to_tray", True):
            event.ignore()
            self.hide()
            self.tray.showMessage("Sifat Voice Type", "Running in tray. Hold hotkey to speak.", QSystemTrayIcon.Information, 2000)
        else:
            self.hotkey_manager.stop()
            self.recorder.stop_recording()
            event.accept()


def launch_app():
    app = QApplication(sys.argv)
    app.setApplicationName("Sifat Voice Type")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
