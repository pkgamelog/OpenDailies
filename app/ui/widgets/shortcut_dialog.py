import os
import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QGroupBox, QFormLayout, QMessageBox, 
                               QScrollArea, QFrame, QWidget)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence

# Path to save the shortcuts config file (in the project root /config folder)
_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "config")
_CONFIG_PATH = os.path.join(_CONFIG_DIR, "shortcuts.json")

DEFAULT_SHORTCUTS = {
    # Annotation Tools
    "Pen": "B",
    "Pencil": "P",
    "Rectangle": "R",
    "Arrow": "A",
    "Circle": "C",
    "Text": "T",
    "Eraser": "E",
    "Undo": "Ctrl+Z",
    "Clear Frame": "Delete",
    "Brush Resize": "F",  
    
    # Playback Tools
    "Play/Pause": "Space",
    "Stop": "Esc",
    "Prev Frame": "Left",
    "Next Frame": "Right",
    "Jump to Prev Annotation": ",",
    "Jump to Next Annotation": ".",
    "Loop": "L",
    "Compare A/B": "Z",
    "Toggle Annotations": "H",
    "Toggle Timecode Overlay": "U"
}

class ShortcutManager:
    @staticmethod
    def load_shortcuts():
        if not os.path.exists(_CONFIG_DIR):
            os.makedirs(_CONFIG_DIR)
        if os.path.exists(_CONFIG_PATH):
            try:
                with open(_CONFIG_PATH, 'r') as f:
                    data = json.load(f)
                    return {**DEFAULT_SHORTCUTS, **data}
            except:
                pass
        return DEFAULT_SHORTCUTS.copy()

    @staticmethod
    def save_shortcuts(shortcuts):
        if not os.path.exists(_CONFIG_DIR):
            os.makedirs(_CONFIG_DIR)
        try:
            with open(_CONFIG_PATH, 'w') as f:
                json.dump(shortcuts, f, indent=4)
        except Exception as e:
            print(f"Error saving shortcuts: {e}")

class KeyCaptureButton(QPushButton):
    """A button that captures keyboard input to set a shortcut."""
    def __init__(self, sequence_str, parent=None):
        super().__init__(sequence_str, parent)
        self._sequence = sequence_str
        self.setCheckable(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumWidth(120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self):
        self.setFocus()
        if self.isChecked():
            self.setText("Press keys...")
            self.setStyleSheet("background-color: #4C8DFF; color: #FFFFFF; border: 1px solid #4C8DFF; border-radius: 6px; padding: 6px 12px;")
            # Grab keyboard so global shortcuts (Space, Left, Right) don't trigger the video player
            self.grabKeyboard()
        else:
            self.setText(self._sequence)
            self.setStyleSheet("")
            self.releaseKeyboard()

    def keyPressEvent(self, event):
        if self.isChecked():
            if event.key() == Qt.Key.Key_Escape:
                self.setChecked(False)
                self.setText(self._sequence)
                self.setStyleSheet("")
                self.releaseKeyboard()
                return
            
            # Ignore pure modifier presses so we can capture combos like Ctrl+Z
            if event.key() in [Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta]:
                return

            # FIX: Use literal text for simple punctuation (fixes Comma/Period issues)
            if event.modifiers() == Qt.KeyboardModifier.NoModifier and event.text() != "":
                key_seq = event.text()
            else:
                # Combine keys and modifiers using standard integer bitwise OR
                key_seq = QKeySequence(int(event.key()) | int(event.modifiers())).toString()
            
            # Prevent setting a completely empty shortcut
            if key_seq:
                self._sequence = key_seq
                self.setText(key_seq)
                self.setChecked(False)
                self.setStyleSheet("")
                self.releaseKeyboard()
            return 
            
        super().keyPressEvent(event)

    def get_sequence(self):
        return self._sequence

class ShortcutDialog(QDialog):
    def __init__(self, current_shortcuts, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Shortcuts")
        self.setMinimumWidth(500)
        self.resize(500, 600)
        
        self._shortcuts = current_shortcuts.copy()

        self.setStyleSheet("""
            QDialog { background-color: #171717; color: #FFFFFF; }
            QLabel { color: #FFFFFF; font-size: 13px; }
            QGroupBox { 
                border: 1px solid #2D2E30; 
                border-radius: 8px; 
                margin-top: 16px; 
                color: #FFFFFF; 
                font-weight: bold;
                background-color: #202124;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 12px; 
                padding: 0 8px; 
                background-color: transparent;
            }
            QPushButton { 
                background-color: #252526; 
                color: #FFFFFF; 
                border: 1px solid #2D2E30; 
                padding: 8px 16px; 
                border-radius: 6px; 
                min-width: 80px; 
                font-weight: bold;
            }
            QPushButton:hover { 
                background-color: #2D2E30; 
                border: 1px solid #4C8DFF; 
            }
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { 
                border: none; 
                background: #171717; 
                width: 10px; 
                margin: 0; 
            }
            QScrollBar::handle:vertical { 
                background: #2D2E30; 
                min-height: 30px; 
                border-radius: 5px; 
            }
            QScrollBar::handle:vertical:hover { 
                background: #4C8DFF; 
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { 
                border: none; 
                background: none; 
                height: 0px; 
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { 
                background: transparent; 
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        info_label = QLabel("Click a button, then press the new key combination.\nPress 'Esc' to cancel capturing.")
        info_label.setStyleSheet("color: #A9A9A9; margin-bottom: 4px;")
        main_layout.addWidget(info_label)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 4, 0)
        scroll_layout.setSpacing(12)
        
        anno_group = QGroupBox("Annotation Tools")
        anno_layout = QFormLayout(anno_group)
        anno_layout.setSpacing(12)
        anno_layout.setContentsMargins(16, 24, 16, 16)
        
        pb_group = QGroupBox("Playback Tools")
        pb_layout = QFormLayout(pb_group)
        pb_layout.setSpacing(12)
        pb_layout.setContentsMargins(16, 24, 16, 16)
        
        self.buttons = {}
        
        anno_keys = ["Pen", "Pencil", "Rectangle", "Arrow", "Circle", "Text", "Eraser", "Undo", "Clear Frame", "Brush Resize"]
        pb_keys = ["Play/Pause", "Stop", "Prev Frame", "Next Frame", "Jump to Prev Annotation", "Jump to Next Annotation", "Loop", "Compare A/B", "Toggle Annotations", "Toggle Timecode Overlay"]
        
        for tool in anno_keys:
            seq = self._shortcuts.get(tool, "")
            btn = KeyCaptureButton(seq)
            anno_layout.addRow(tool, btn)
            self.buttons[tool] = btn
            
        for tool in pb_keys:
            seq = self._shortcuts.get(tool, "")
            btn = KeyCaptureButton(seq)
            pb_layout.addRow(tool, btn)
            self.buttons[tool] = btn
            
        scroll_layout.addWidget(anno_group)
        scroll_layout.addWidget(pb_group)
        scroll_layout.addStretch(1)
        
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.btn_reset = QPushButton("Reset to Defaults")
        self.btn_reset.setStyleSheet("background-color: transparent; border: 1px solid #FF5A5F; color: #FF5A5F;")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_save = QPushButton("Save")
        self.btn_save.setStyleSheet("background-color: #4C8DFF; color: #FFFFFF; border: none;")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_reset.clicked.connect(self._reset_defaults)
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

    def _reset_defaults(self):
        for tool, seq in DEFAULT_SHORTCUTS.items():
            if tool in self.buttons:
                self.buttons[tool]._sequence = seq
                self.buttons[tool].setText(seq)
                self.buttons[tool].setChecked(False)
                self.buttons[tool].setStyleSheet("")

    def get_shortcuts(self):
        updated = {}
        for tool, btn in self.buttons.items():
            updated[tool] = btn.get_sequence()
        return updated