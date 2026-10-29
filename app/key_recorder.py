from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

class KeyRecorderDialog(QDialog):
    """
    Robust Interactive modal dialog that captures keypresses directly from keyboard.
    Allows capturing combinations with Ctrl, Shift, Alt, Windows key, or any single key.
    """
    
    key_recorded = Signal(str)

    def __init__(self, title="Record Shortcut", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(400, 220)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #0A0E1A;
                color: #E2E8F0;
                border: 2px solid #2563EB;
                border-radius: 12px;
            }
            QLabel#titleLbl {
                color: #60A5FA;
                font-size: 15px;
                font-weight: bold;
            }
            QLabel#keyDisplay {
                background-color: #121829;
                border: 2px dashed #3B82F6;
                border-radius: 8px;
                padding: 16px;
                font-size: 18px;
                font-weight: bold;
                color: #38BDF8;
            }
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton#cancelBtn {
                background-color: #1F293D;
                color: #94A3B8;
                border: 1px solid #2D3D5E;
            }
            QPushButton#cancelBtn:hover {
                background-color: #2D3D5E;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("titleLbl")
        title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_lbl)

        sub_lbl = QLabel("Press the keys on your keyboard together (e.g. Ctrl + Shift + B, or F8)...")
        sub_lbl.setStyleSheet("color: #8899B5; font-size: 12px;")
        sub_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub_lbl)

        self.key_display = QLabel("Waiting for keypress...")
        self.key_display.setObjectName("keyDisplay")
        self.key_display.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.key_display)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Shortcut")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_save)

        layout.addLayout(btn_box)

        self.recorded_string = ""
        self._held_modifiers = set()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        modifiers = event.modifiers()

        parts = []
        if modifiers & Qt.ControlModifier or key in (Qt.Key_Control,):
            parts.append("<ctrl>")
        if modifiers & Qt.AltModifier or key in (Qt.Key_Alt,):
            parts.append("<alt>")
        if modifiers & Qt.ShiftModifier or key in (Qt.Key_Shift,):
            parts.append("<shift>")
        if modifiers & Qt.MetaModifier or key in (Qt.Key_Meta,):
            parts.append("<cmd>")

        main_key = ""
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            pass  # Only modifier pressed
        elif key == Qt.Key_Space:
            main_key = "<space>"
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            main_key = "<enter>"
        elif key == Qt.Key_Tab:
            main_key = "<tab>"
        elif Qt.Key_A <= key <= Qt.Key_Z:
            main_key = chr(key).lower()
        elif Qt.Key_0 <= key <= Qt.Key_9:
            main_key = chr(key)
        elif key >= Qt.Key_F1 and key <= Qt.Key_F12:
            main_key = f"f{key - Qt.Key_F1 + 1}"

        if main_key and main_key not in parts:
            parts.append(main_key)

        # Allow saving even if modifier + key, or standalone F-key / letter
        if parts:
            # Deduplicate preserving order
            unique_parts = []
            for p in parts:
                if p not in unique_parts:
                    unique_parts.append(p)

            res = "+".join(unique_parts)
            self.recorded_string = res
            display_text = res.replace("<cmd>", "WIN").replace("<", "").replace(">", "").upper()
            self.key_display.setText(display_text)
            self.btn_save.setEnabled(True)

        event.accept()

    def get_shortcut(self) -> str:
        return self.recorded_string
