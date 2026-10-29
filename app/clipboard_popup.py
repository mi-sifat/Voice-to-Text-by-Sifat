"""
ClipboardPopupDialog — centered floating picker with mouse drag support,
full text & image preview, and clean delete/clear management.
"""

from PySide6.QtCore import Qt, Signal, QPoint, QRect, QSize
from PySide6.QtGui import QKeySequence, QCursor, QFont, QIcon, QMouseEvent, QPixmap, QImage
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QApplication, QSizePolicy,
    QFrame, QWidget
)
import os
import pyperclip


_STYLE = """
QDialog {
    background-color: #0D1526;
    border: 2px solid #3B82F6;
    border-radius: 14px;
}
QLabel#header {
    color: #60A5FA;
    font-size: 14px;
    font-weight: bold;
    padding: 4px 0px;
}
QListWidget {
    background-color: #0A0E1A;
    border: 1px solid #1F2A4C;
    border-radius: 8px;
    padding: 6px;
    color: #E2E8F0;
    font-size: 13px;
    outline: none;
}
QListWidget::item {
    padding: 10px 12px;
    border-radius: 6px;
    margin: 2px 0;
}
QListWidget::item:selected {
    background-color: #1D4ED8;
    color: #FFFFFF;
}
QListWidget::item:hover {
    background-color: #1E3A5F;
    color: #FFFFFF;
}
QPushButton#closeBtn {
    background-color: transparent;
    color: #8899B5;
    border: 1px solid #1E2A4A;
    border-radius: 6px;
    font-size: 16px;
    font-weight: bold;
    padding: 2px 8px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
}
QPushButton#closeBtn:hover {
    background-color: #7F1D1D;
    color: #FEE2E2;
    border-color: #DC2626;
}
QPushButton#actionBtn {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: bold;
    font-size: 13px;
}
QPushButton#actionBtn:hover { background-color: #1D4ED8; }
QPushButton#dangerBtn {
    background-color: #991B1B;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 13px;
}
QPushButton#dangerBtn:hover { background-color: #7F1D1D; }
"""


class ClipboardPopupDialog(QDialog):
    item_selected = Signal(dict)
    clear_requested = Signal()

    def __init__(self, entries: list, target_hwnd: int = 0, parent=None):
        super().__init__(parent, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.target_hwnd = target_hwnd
        self.entries = entries
        self.setStyleSheet(_STYLE)
        self.setMinimumWidth(580)
        self.setMaximumWidth(750)
        self.setMinimumHeight(420)
        self.setMaximumHeight(580)

        self._drag_pos = None

        self._build_ui()
        self._center_on_screen()
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    # ─── Build UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 16)
        root.setSpacing(10)

        # Title bar row (Draggable)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        lbl = QLabel("📋 Clipboard & Voice History (কপি করা টেক্সট ও ছবি সংরক্ষিত থাকে)")
        lbl.setObjectName("header")
        lbl.setCursor(Qt.SizeAllCursor)
        title_row.addWidget(lbl, 1)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        title_row.addWidget(close_btn)
        root.addLayout(title_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#1E2A4A;")
        root.addWidget(sep)

        # Hint
        hint = QLabel("মাউস দিয়ে উইন্ডোটি যেকোনো জায়গায় সরানো যাবে • Enter/ডাবল ক্লিকে পেস্ট • Ctrl+C করা সবকিছু এখানে জমা থাকে")
        hint.setStyleSheet("color:#64748B;font-size:11px;")
        root.addWidget(hint)

        # List
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(48, 48))
        self.list_widget.setAlternatingRowColors(False)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.itemDoubleClicked.connect(self._on_select)
        root.addWidget(self.list_widget)

        # Populate
        if not self.entries:
            placeholder = QListWidgetItem("(এখনো কোনো আইটেম নেই — কিছু কপি বা রেকর্ড করুন)")
            placeholder.setFlags(Qt.NoItemFlags)
            placeholder.setForeground(Qt.gray)
            self.list_widget.addItem(placeholder)
        else:
            for e in self.entries:
                item_type = e.get("type", "text")
                text = e.get("text", "")
                ts = e.get("timestamp", "")
                img_path = e.get("image_path")

                if item_type == "image" and img_path and os.path.exists(img_path):
                    item = QListWidgetItem(f"🖼️ [Image/ছবি]   [{ts}]")
                    pix = QPixmap(img_path)
                    if not pix.isNull():
                        item.setIcon(QIcon(pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
                else:
                    preview = text[:80] + ("…" if len(text) > 80 else "")
                    prefix = "🎙️" if item_type == "voice" else "📋"
                    item = QListWidgetItem(f"{prefix} {preview}   [{ts}]")

                item.setData(Qt.UserRole, e)
                self.list_widget.addItem(item)

        # Action buttons row
        btn_row = QHBoxLayout()

        clear_btn = QPushButton("🗑️ ক্লিপবোর্ড খালি করুন (Clear All)")
        clear_btn.setObjectName("dangerBtn")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._on_clear_all)
        btn_row.addWidget(clear_btn)

        btn_row.addStretch()

        paste_btn = QPushButton("↵ পেস্ট করুন (Paste)")
        paste_btn.setObjectName("actionBtn")
        paste_btn.setCursor(Qt.PointingHandCursor)
        paste_btn.clicked.connect(self._on_select)
        btn_row.addWidget(paste_btn)

        cancel_btn = QPushButton("বন্ধ করুন")
        cancel_btn.setObjectName("closeBtn")
        cancel_btn.setMinimumWidth(80)
        cancel_btn.setMaximumWidth(80)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(
            "background-color:#151D33;color:#8899B5;border:1px solid #1E2A4A;"
            "border-radius:8px;padding:8px 16px;font-weight:bold;"
        )
        cancel_btn.clicked.connect(self.close)
        btn_row.addWidget(cancel_btn)
        root.addLayout(btn_row)

    # ─── Center on Screen ──────────────────────────────────────────────────

    def _center_on_screen(self):
        """Always places the popup in the exact center of the active screen."""
        self.adjustSize()
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if not screen:
            screen = QApplication.primaryScreen()
        
        geom = screen.availableGeometry()
        w = max(self.width(), 600)
        h = max(self.height(), 440)
        
        x = geom.x() + (geom.width() - w) // 2
        y = geom.y() + (geom.height() - h) // 2
        
        self.setGeometry(x, y, w, h)

    # ─── Drag to Move Window ───────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None

    # ─── Keyboard Events ───────────────────────────────────────────────────

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.close()
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            self._on_select()
        elif key == Qt.Key_Up:
            row = self.list_widget.currentRow()
            if row > 0:
                self.list_widget.setCurrentRow(row - 1)
        elif key == Qt.Key_Down:
            row = self.list_widget.currentRow()
            if row < self.list_widget.count() - 1:
                self.list_widget.setCurrentRow(row + 1)
        else:
            super().keyPressEvent(event)

    def _on_select(self, _item=None):
        item = self.list_widget.currentItem()
        if item:
            entry = item.data(Qt.UserRole)
            if entry:
                self.item_selected.emit(entry)
                self.close()

    def _on_clear_all(self):
        self.clear_requested.emit()
        self.list_widget.clear()
        placeholder = QListWidgetItem("(ক্লিপবোর্ড খালি করা হয়েছে)")
        placeholder.setFlags(Qt.NoItemFlags)
        placeholder.setForeground(Qt.gray)
        self.list_widget.addItem(placeholder)
