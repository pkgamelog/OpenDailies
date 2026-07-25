from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal, QRect, QPoint, QEvent
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygon, QMouseEvent, QPaintEvent, QWheelEvent
import logging

logger = logging.getLogger(__name__)

class TimelineWidget(QWidget):
    position_changed = Signal(int)
    trim_changed = Signal(int, int)
    scrub_started = Signal()
    scrub_finished = Signal()

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.setMinimumHeight(40) # Smaller height to match container
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self._duration_frames = 0
        self._current_frame = 0
        self._in_point_frame = 0
        self._out_point_frame = 0
        self._markers = []
        self._annotation_keys = []
        
        self._px_per_frame = 2.0
        
        self._dragging_playhead = False
        self._dragging_in = False
        self._dragging_out = False
        
        # NEW: Track if the user has manually zoomed
        self._auto_fit = True

    # --- NEW: Auto-Fit Logic for Window Resizing ---
    
    def showEvent(self, event):
        """Install event filter on parent (QScrollArea viewport) when shown."""
        super().showEvent(event)
        if self.parent():
            self.parent().installEventFilter(self)

    def eventFilter(self, obj, event):
        """Detect when the scroll area resizes (window maximize/minimize) and auto-fit."""
        if obj == self.parent() and event.type() == QEvent.Type.Resize:
            if self._auto_fit and self._duration_frames > 0:
                self._fit_to_parent()
        return super().eventFilter(obj, event)

    def _fit_to_parent(self):
        """Calculates the available width of the parent scroll area and fits the timeline."""
        parent = self.parent()
        if parent:
            w = parent.width() - 20  # 20px padding for margins
            if w > 0:
                self.fit_to_width(w)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Double-clicking the timeline resets the zoom to fit the screen."""
        pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        x = pos.x()
        if self._duration_frames <= 0: return

        in_x = self._frames_to_x(self._in_point_frame)
        out_x = self._frames_to_x(self._out_point_frame)

        # Only trigger reset if we didn't double-click on the trim handles
        if abs(x - in_x) > 8 and abs(x - out_x) > 8:
            self._auto_fit = True
            self._fit_to_parent()
            event.accept()
            return
            
        super().mouseDoubleClickEvent(event)

    # --- Existing Methods ---

    def set_position_frame(self, frame: int) -> None:
        if frame < 0: frame = 0
        if self._duration_frames and frame > self._duration_frames:
            frame = self._duration_frames
        self._current_frame = int(frame)
        self.update()

    def set_duration_frames(self, frames: int) -> None:
        self._duration_frames = max(0, int(frames))
        if self._out_point_frame <= self._in_point_frame:
            self._out_point_frame = self._duration_frames
        if self._out_point_frame > self._duration_frames:
            self._out_point_frame = self._duration_frames
        self._update_min_width()
        
        # Auto-fit when a new video loads
        if self._auto_fit:
            self._fit_to_parent()
            
        self.update()

    def fit_to_width(self, width: int):
        """Scales the timeline to fit exactly into the given width."""
        if self._duration_frames > 0:
            self._px_per_frame = max(1.0, width / self._duration_frames)
            self._update_min_width()
            self.update()

    def add_marker(self, marker: dict) -> None:
        if isinstance(marker, int):
            m = {"id": None, "frame": marker, "color": "#4C8DFF", "name": ""}
        else:
            m = dict(marker)
        self._markers.append(m)
        self.update()

    def clear_markers(self) -> None:
        self._markers.clear()
        self.update()

    def load_markers(self, markers: list) -> None:
        self._markers = []
        for bm in markers:
            try:
                if hasattr(bm, "frame_number"):
                    frame = int(getattr(bm, "frame_number", 0) or 0)
                    self._markers.append({"id": getattr(bm, "id", None), "frame": frame, "color": getattr(bm, "color", "#4C8DFF"), "name": getattr(bm, "name", "")})
                elif isinstance(bm, dict):
                    frame = int(bm.get("frame", 0))
                    self._markers.append({"id": bm.get("id"), "frame": frame, "color": bm.get("color", "#4C8DFF"), "name": bm.get("name", "")})
            except Exception:
                continue
        self.update()

    def set_annotation_keys(self, keys: list):
        self._annotation_keys = []
        for k in keys:
            if isinstance(k, tuple):
                self._annotation_keys.append(k)  # FIX: Changed 't' to 'k'
            else:
                self._annotation_keys.append((k, 1))
        self._annotation_keys.sort(key=lambda x: x[0])
        self.update()

    def set_in_point_frame(self, frame: int) -> None:
        self._in_point_frame = max(0, int(frame))
        if self._out_point_frame < self._in_point_frame:
            self._out_point_frame = self._in_point_frame
        self.trim_changed.emit(self._in_point_frame, self._out_point_frame)
        self.update()

    def set_out_point_frame(self, frame: int) -> None:
        self._out_point_frame = min(max(0, int(frame)), self._duration_frames or frame)
        if self._out_point_frame < self._in_point_frame:
            self._in_point_frame = self._out_point_frame
        self.trim_changed.emit(self._in_point_frame, self._out_point_frame)
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y() / 120
            self._px_per_frame = max(1.0, min(50.0, self._px_per_frame + delta))
            
            # NEW: Disable auto-fit if the user manually zooms
            self._auto_fit = False 
            
            self._update_min_width()
            self.update()
        else:
            super().wheelEvent(event)

    def _update_min_width(self):
        if self._duration_frames > 0:
            self.setMinimumWidth(int(self._duration_frames * self._px_per_frame) + 20)
        else:
            self.setMinimumWidth(0)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        # 1. Background
        painter.fillRect(rect, QColor("#1E1E1E"))

        if self._duration_frames <= 0:
            painter.end()
            return

        # 2. Maya-style Grid (Minor and Major lines)
        target_tick_px = 60
        tick_interval = 1
        while tick_interval * self._px_per_frame < target_tick_px:
            if tick_interval == 1: tick_interval = 2
            elif tick_interval == 2: tick_interval = 5
            elif tick_interval == 5: tick_interval = 10
            elif tick_interval == 10: tick_interval = 20
            elif tick_interval == 20: tick_interval = 50
            else: tick_interval += 10

        # Minor grid lines (every frame if zoomed in enough, otherwise every 1 step)
        if self._px_per_frame > 10:
            painter.setPen(QPen(QColor("#252526"), 1))
            for f in range(0, self._duration_frames + 1, 1):
                x = self._frames_to_x(f)
                painter.drawLine(x, 0, x, rect.height())

        # Major grid lines and text
        painter.setFont(QFont("SF Pro Display", 8))
        for f in range(0, self._duration_frames + 1, tick_interval):
            x = self._frames_to_x(f)
            painter.setPen(QPen(QColor("#3A3B3D"), 1))
            painter.drawLine(x, 0, x, rect.height() - 10)
            
            painter.setPen(QColor("#A9A9A9"))
            text = str(f)
            text_width = painter.fontMetrics().horizontalAdvance(text)
            painter.drawText(x - text_width // 2, rect.height() - 4, text)

        # 3. Trim Region
        in_x = self._frames_to_x(self._in_point_frame)
        out_x = self._frames_to_x(self._out_point_frame)
        trim_rect = QRect(int(in_x), 0, max(1, int(out_x - in_x)), rect.height() - 14)
        painter.fillRect(trim_rect, QColor(76, 141, 255, 30)) 
        
        # 4. Markers (Bookmarks) - Drawn as triangles at the top edge
        for m in self._markers:
            try:
                frame = int(m.get("frame", 0))
            except Exception:
                continue
            x = self._frames_to_x(frame)
            marker_color = QColor(m.get("color", "#4C8DFF"))
            painter.setBrush(marker_color)
            painter.setPen(Qt.PenStyle.NoPen)
            # Draw downward triangle
            tri = QPolygon([QPoint(x - 4, 0), QPoint(x + 4, 0), QPoint(x, 6)])
            painter.drawPolygon(tri)
            # Draw thin line down
            painter.setPen(QPen(marker_color, 1))
            painter.drawLine(x, 6, x, rect.height() - 16)

        # 4.5 Annotation Keyframes
        painter.setBrush(QBrush(QColor("#4C8DFF")))
        painter.setPen(Qt.PenStyle.NoPen)
        for frame, duration in self._annotation_keys:
            x_start = self._frames_to_x(frame)
            if duration <= 1:
                center_y = 12
                diamond = QPolygon([
                    QPoint(x_start, center_y - 4), QPoint(x_start + 4, center_y),
                    QPoint(x_start, center_y + 4), QPoint(x_start - 4, center_y)
                ])
                painter.drawPolygon(diamond)
            else:
                x_end = self._frames_to_x(frame + duration)
                bar_y = 10
                painter.drawRoundedRect(QRect(x_start, bar_y, max(1, x_end - x_start), 4), 2, 2)

        # 5. Trim Handles
        handle_width = 4
        handle_height = rect.height() - 16
        
        painter.setBrush(QBrush(QColor("#4C8DFF")))
        painter.setPen(Qt.PenStyle.NoPen)
        
        in_rect = QRect(int(in_x) - handle_width//2, 2, handle_width, handle_height)
        out_rect = QRect(int(out_x) - handle_width//2, 2, handle_width, handle_height)
        painter.drawRoundedRect(in_rect, 2, 2)
        painter.drawRoundedRect(out_rect,2, 2)

        # 6. Playhead
        ph_x = self._frames_to_x(self._current_frame)
        painter.setPen(QPen(QColor("#FFFFFF"), 1))
        painter.drawLine(ph_x, 0, ph_x, rect.height())
        
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        tri = QPolygon([QPoint(ph_x - 5, 0), QPoint(ph_x + 5, 0), QPoint(ph_x, 6)])
        painter.drawPolygon(tri)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus()
        pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        x = pos.x()
        if self._duration_frames <= 0: return

        in_x = self._frames_to_x(self._in_point_frame)
        out_x = self._frames_to_x(self._out_point_frame)

        if abs(x - in_x) <= 8:
            self._dragging_in = True
            return
        if abs(x - out_x) <= 8:
            self._dragging_out = True
            return

        self._dragging_playhead = True
        self.scrub_started.emit()
        self._set_position_from_x(x, emit_signal=True)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        x = pos.x()
        if self._duration_frames <= 0: return
        
        if self._dragging_playhead:
            self._set_position_from_x(x, emit_signal=True)
        elif self._dragging_in:
            self.set_in_point_frame(self._x_to_frames(x))
        elif self._dragging_out:
            self.set_out_point_frame(self._x_to_frames(x))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._dragging_playhead:
            self._dragging_playhead = False
            self.scrub_finished.emit()
        self._dragging_in = False
        self._dragging_out = False

    def _frames_to_x(self, frame: int) -> int:
        if self._duration_frames <= 0: return 10
        return int(10 + frame * self._px_per_frame)

    def _x_to_frames(self, x: int) -> int:
        if self._duration_frames <= 0: return 0
        return max(0, min(int((x - 10) / self._px_per_frame), self._duration_frames))

    def _set_position_from_x(self, x: int, emit_signal: bool = False) -> None:
        frame = self._x_to_frames(x)
        if frame != self._current_frame:
            self._current_frame = frame
            if emit_signal:
                self.position_changed.emit(int(frame))
            self.update()