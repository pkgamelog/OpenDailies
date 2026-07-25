"""
Modern Custom Title Bar for Frameless Window.
Premium Windows 11 / macOS hybrid aesthetic.
"""
import os
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy
from PySide6.QtCore import Qt, Signal, QSize, QRectF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QFont

class CloseButton(QPushButton):
    """Custom close button with Windows 11 style hover."""
    def __init__(self, draw_func, parent=None):
        super().__init__(parent)
        self._draw_func = draw_func
        self.setFixedSize(46, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # FIX: Windows 11 official close color and subtle hover
        self.setStyleSheet("""
            QPushButton { background: transparent; border: none; border-top-right-radius: 6px; }
            QPushButton:hover { background-color: #E81123; }
            QPushButton:pressed { background-color: #F1707A; }
        """)
        self._update_icon(QColor("#FFFFFF")) 

    def _update_icon(self, color: QColor):
        pix = QPixmap(16, 16)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_func(p, color)
        p.end()
        self.setIcon(QIcon(pix))

    def enterEvent(self, event):
        self._update_icon(QColor("#FFFFFF"))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_icon(QColor("#FFFFFF"))
        super().leaveEvent(event)


class CustomTitleBar(QWidget):
    """A modern title bar with window controls, app icon, dynamic file info, and drag functionality."""
    
    close_requested = Signal()
    minimize_requested = Signal()
    maximize_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setObjectName("TitleBar")
        # FIX: Slightly elevated background with a very subtle bottom separator
        self.setStyleSheet("""
            QWidget#TitleBar { 
                background-color: #1A1A1A; 
                border-bottom: 1px solid #2A2A2A; 
                border-top-left-radius: 8px; 
                border-top-right-radius: 8px; 
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0) 
        layout.setSpacing(12)
        
        # FIX: Modern App Icon Space
        self.app_icon_label = QLabel()
        self.app_icon_label.setFixedSize(18, 18)
        self.app_icon_label.setStyleSheet("background: transparent;")
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),"assets", "icons", "OpenDailies.ico")
        if os.path.exists(icon_path):
            self.app_icon_label.setPixmap(QPixmap(icon_path).scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(self.app_icon_label)
        
        # FIX: Modern Typography (Medium weight, slightly muted white)
        self.title_label = QLabel("OpenDailies")
        self.title_label.setStyleSheet("color: #E0E0E0; font-weight: 500; font-size: 12px; background: transparent; font-family: 'Segoe UI Variable', 'Inter', sans-serif;")
        layout.addWidget(self.title_label)
        
        layout.addStretch(1)
        
        # FIX: Sleek Pill Design for Media Info
        self.meta_label = QLabel("")
        self.meta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.meta_label.setStyleSheet("""
            QLabel { 
                color: #909090; 
                font-size: 11px; 
                background: rgba(255, 255, 255, 0.05); 
                padding: 3px 10px; 
                border-radius: 10px; 
                font-family: 'SF Mono', 'Consolas', monospace;
            }
        """)
        self.meta_label.setVisible(False) 
        layout.addWidget(self.meta_label)
        
        layout.addStretch(1)
        
        # FIX: Sleek Window Controls (Translucent hovers)
        self.btn_minimize = self._create_standard_btn()
        self.btn_minimize.clicked.connect(self.minimize_requested.emit)
        self.btn_minimize.setIcon(self._create_icon(self._draw_minimize, QColor("#CCCCCC")))
        
        self.btn_maximize = self._create_standard_btn()
        self.btn_maximize.clicked.connect(self.maximize_requested.emit)
        self.btn_maximize.setIcon(self._create_icon(self._draw_maximize, QColor("#CCCCCC")))
        
        self.btn_close = CloseButton(self._draw_close)
        self.btn_close.clicked.connect(self.close_requested.emit)
        
        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_maximize)
        layout.addWidget(self.btn_close)
        
        self._drag_pos = None

    def _create_standard_btn(self) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(46, 32)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # FIX: Windows 11 style translucent hover
        btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.08); }
            QPushButton:pressed { background-color: rgba(255, 255, 255, 0.04); }
        """)
        return btn

    def _create_icon(self, draw_func, color: QColor) -> QIcon:
        pix = QPixmap(16, 16)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_func(p, color)
        p.end()
        return QIcon(pix)

    # FIX: Thinner, more elegant Windows 11 style icons
    def _draw_minimize(self, p: QPainter, color: QColor):
        p.setPen(QPen(color, 1.2))
        p.drawLine(4, 11, 12, 11)

    def _draw_maximize(self, p: QPainter, color: QColor):
        p.setPen(QPen(color, 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(4.5, 4.5, 7, 7))

    def _draw_close(self, p: QPainter, color: QColor):
        p.setPen(QPen(color, 1.4))
        p.drawLine(4, 4, 11, 11)
        p.drawLine(11, 4, 4, 11)

    def set_file_title(self, filename: str, fmt: str = "", fps: float = 0.0, size: str = ""):
        """Updates the title bar to display the loaded video info dynamically."""
        if filename:
            self.title_label.setText(f"OpenDailies  —  {filename}")
            
            meta_parts = []
            if fmt: meta_parts.append(fmt.upper())
            if fps > 0: meta_parts.append(f"{fps:.3f} FPS")
            if size: meta_parts.append(size)
            
            if meta_parts:
                self.meta_label.setText("  •  ".join(meta_parts))
                self.meta_label.setVisible(True)
            else:
                self.meta_label.setVisible(False)
        else:
            self.title_label.setText("OpenDailies")
            self.meta_label.setText("")
            self.meta_label.setVisible(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            if self.window().isMaximized():
                return
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        self.maximize_requested.emit()