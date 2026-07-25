from __future__ import annotations

from typing import Optional
import logging

from PySide6.QtWidgets import QLabel, QWidget
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QFont, QPen, QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtCore import Qt, QRect, Signal

logger = logging.getLogger(__name__)


class VideoDisplayWidget(QLabel):
    """QLabel-based video display widget.
    
    Draws a custom checkerboard and empty state when no media is loaded.
    Includes a transparent overlay for SMPTE timecode and Subtitles.
    """
    
    # NEW: Signals for drag-drop and double click
    video_dropped = Signal(str)
    open_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #0F0F0F; border-radius: 8px;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 180)
        self.setScaledContents(False)
        self.setText("") 
        
        # NEW: Enable drag and drop and pointing cursor
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._last_image: Optional[QImage] = None
        self._last_pixmap: Optional[QPixmap] = None
        self._overlay: Optional[QWidget] = None
        
        # Timecode Overlay
        self._timecode_label = QLabel(self)
        self._timecode_label.setStyleSheet(
            "background: rgba(0,0,0,160); color: #4C8DFF; "
            "font-family: 'SF Mono', 'Consolas', monospace; font-size: 14px; padding: 6px 10px; "
            "border-radius: 6px; border: 1px solid #2D2E30;"
        )
        self._timecode_label.move(16, 16)
        self._timecode_label.hide()
        
        # Subtitle Overlay (Center Bottom)
        self._subtitle_label = QLabel(self)
        self._subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle_label.setStyleSheet(
            "background: rgba(0,0,0,180); color: #FFFFFF; "
            "font-family: 'SF Pro Display', sans-serif; font-size: 14px; font-weight: 500; "
            "padding: 6px 12px; border-radius: 6px; border: 1px solid #2D2E30;"
        )
        self._subtitle_label.hide()

    def set_overlay(self, overlay: QWidget) -> None:
        self._overlay = overlay

    # --- NEW: Drag and Drop Events ---

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Accepts the drag if it contains a file URL."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Keeps the drag accepted while moving over the widget."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Loads the video file when dropped."""
        if event.mimeData().hasUrls():
            file_url = event.mimeData().urls()[0]
            file_path = file_url.toLocalFile()
            
            # Verify it's a video file
            valid_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.m4v', '.webm', '.wmv', '.flv']
            if any(file_path.lower().endswith(ext) for ext in valid_extensions):
                self.video_dropped.emit(file_path)
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    # --- NEW: Double Click Event ---

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Opens the file browser when double-clicking the video area."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_requested.emit()
        super().mouseDoubleClickEvent(event)

    # --- Existing Methods ---

    def update_frame(self, img: QImage) -> None:
        try:
            if img is None or img.isNull(): return
            self._last_image = img
            pix = QPixmap.fromImage(img)
            w = max(1, self.width())
            h = max(1, self.height())
            scaled = pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._last_pixmap = scaled
            self._update_overlay_geometry()
            self.update()
        except Exception:
            logger.exception("Failed to update VideoDisplayWidget frame")

    def resizeEvent(self, event) -> None:
        try:
            if self._last_image is not None:
                pix = QPixmap.fromImage(self._last_image)
                w = max(1, self.width())
                h = max(1, self.height())
                scaled = pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._last_pixmap = scaled
            self._update_overlay_geometry()
            self._update_subtitle_geometry()
        except Exception:
            logger.exception("Failed to rescale last frame on resize")
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_checkerboard(painter)
        if self._last_pixmap and not self._last_pixmap.isNull():
            x = (self.width() - self._last_pixmap.width()) // 2
            y = (self.height() - self._last_pixmap.height()) // 2
            painter.drawPixmap(x, y, self._last_pixmap)
        else:
            painter.setPen(QColor("#3A3B3D"))
            painter.setFont(QFont("SF Pro Display", 14, QFont.Weight.Medium))
            # Updated text to mention drag & drop / double click
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Media Loaded\n\nDrag & Drop a video file here\nor Go to file menu to browse")
        painter.end()

    def _draw_checkerboard(self, painter: QPainter):
        tile_size = 16
        color1 = QColor("#0F0F0F")
        color2 = QColor("#121212")
        for y in range(0, self.height(), tile_size):
            for x in range(0, self.width(), tile_size):
                if (x // tile_size) % 2 == (y // tile_size) % 2:
                    painter.fillRect(QRect(x, y, tile_size, tile_size), color1)
                else:
                    painter.fillRect(QRect(x, y, tile_size, tile_size), color2)

    def clear_frame(self) -> None:
        self._last_image = None
        self._last_pixmap = None
        self.update()

    def _update_overlay_geometry(self):
        if not self._overlay: return
        if not self._last_pixmap or self._last_pixmap.isNull():
            self._overlay.setGeometry(0, 0, self.width(), self.height())
            return
        widget_w = self.width()
        widget_h = self.height()
        pix_w = self._last_pixmap.width()
        pix_h = self._last_pixmap.height()
        x = (widget_w - pix_w) // 2
        y = (widget_h - pix_h) // 2
        self._overlay.setGeometry(x, y, pix_w, pix_h)
        
        # NEW: Resize Before/After Overlay if it exists
        if hasattr(self, 'before_overlay') and self.before_overlay:
            self.before_overlay.setGeometry(x, y, pix_w, pix_h)

    def _update_subtitle_geometry(self):
        self._subtitle_label.adjustSize()
        x = (self.width() - self._subtitle_label.width()) // 2
        y = self.height() - 50
        self._subtitle_label.move(x, y)

    def set_timecode(self, text: str) -> None:
        self._timecode_label.setText(text)
        self._timecode_label.adjustSize()

    def set_timecode_visible(self, visible: bool) -> None:
        self._timecode_label.setVisible(visible)
        
    def set_subtitle(self, text: str):
        self._subtitle_label.setText(text)
        self._update_subtitle_geometry()

    def set_subtitle_visible(self, visible: bool):
        self._subtitle_label.setVisible(visible)