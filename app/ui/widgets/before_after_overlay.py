from PySide6.QtWidgets import QWidget, QMenu
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import QPainter, QPixmap, QColor, QPen, QFont, QMouseEvent

class BeforeAfterOverlay(QWidget):
    """A slider overlay that wipes between the old playblast and the new one."""
    closed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: transparent;")
        self._before_pixmap = None
        self._slider_x = 0
        self._dragging = False
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        
    def _show_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #202124; border: 1px solid #2D2E30; border-radius: 8px; padding: 4px; } QMenu::item { padding: 8px 24px; border-radius: 4px; color: #FFFFFF; } QMenu::item:selected { background-color: #4C8DFF; }")
        menu.addAction("Exit Before/After", self._do_close)
        menu.exec(self.mapToGlobal(pos))
        
    def _do_close(self):
        self.hide()
        self.closed.emit()
        
    def update_before_frame(self, img):
        if img and not img.isNull():
            pix = QPixmap.fromImage(img)
            self._before_pixmap = pix.scaled(self.width(), self.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.update()
            
    def resizeEvent(self, event):
        if self._slider_x == 0 or self._slider_x > self.width():
            self._slider_x = self.width() // 2
        super().resizeEvent(event)
        
    def paintEvent(self, event):
        if not self._before_pixmap: return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pix_w = self._before_pixmap.width()
        pix_h = self._before_pixmap.height()
        x = (self.width() - pix_w) // 2
        y = (self.height() - pix_h) // 2
        video_rect = QRect(x, y, pix_w, pix_h)
        
        # Clip and draw ONLY the left side (Before)
        clip_rect = QRect(video_rect.x(), video_rect.y(), self._slider_x - video_rect.x(), video_rect.height())
        painter.setClipRect(clip_rect)
        painter.drawPixmap(video_rect, self._before_pixmap)
        painter.setClipping(False)
        
        # Draw Slider Line
        pen = QPen(QColor("#FFFFFF"), 2)
        painter.setPen(pen)
        painter.drawLine(self._slider_x, video_rect.y(), self._slider_x, video_rect.bottom())
        
        # Draw Handle
        handle_y = video_rect.center().y()
        painter.setBrush(QColor("#4C8DFF"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPoint(self._slider_x, handle_y), 12, 12)
        
        # Arrows on Handle
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.drawLine(self._slider_x - 5, handle_y, self._slider_x - 1, handle_y - 3)
        painter.drawLine(self._slider_x - 5, handle_y, self._slider_x - 1, handle_y + 3)
        painter.drawLine(self._slider_x + 5, handle_y, self._slider_x + 1, handle_y - 3)
        painter.drawLine(self._slider_x + 5, handle_y, self._slider_x + 1, handle_y + 3)
        
        # Labels
        font = QFont("SF Pro Display", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#FFFFFF"))
        
        painter.fillRect(QRect(video_rect.x() + 10, video_rect.y() + 10, 60, 24), QColor(0, 0, 0, 160))
        painter.drawText(QRect(video_rect.x() + 10, video_rect.y() + 10, 60, 24), Qt.AlignmentFlag.AlignCenter, "BEFORE")
        
        painter.fillRect(QRect(video_rect.right() - 70, video_rect.y() + 10, 60, 24), QColor(0, 0, 0, 160))
        painter.drawText(QRect(video_rect.right() - 70, video_rect.y() + 10, 60, 24), Qt.AlignmentFlag.AlignCenter, "AFTER")
        
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if abs(event.position().x() - self._slider_x) < 20:
                self._dragging = True
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self._slider_x = int(event.position().x())
                self._dragging = True
                self.setCursor(Qt.CursorShape.SizeHorCursor)
                self.update()
                
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self._slider_x = max(0, min(int(event.position().x()), self.width()))
            self.update()
            
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging = False
        self.setCursor(Qt.CursorShape.ArrowCursor)