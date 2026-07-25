"""
Annotation Overlay Widget for drawing on video frames.
Delegates rendering to BrushEngine. Handles Tablet Events for pressure.
Implements Double Buffering for maximum performance.
"""
import os
import math
from typing import List, Dict, Optional
from PySide6.QtWidgets import QWidget, QInputDialog
from PySide6.QtCore import Qt, Signal, QPoint, QRectF, QEvent
from PySide6.QtGui import (QPainter, QPen, QColor, QBrush, QFont, QMouseEvent, 
                            QPaintEvent, QPolygon, QTabletEvent, QPixmap, QCursor)
from app.ui.widgets.brush_engine import BrushEngine

class AnnotationOverlay(QWidget):
    """Transparent overlay for drawing and displaying annotations."""
    
    annotation_added = Signal(dict)      
    annotation_erased = Signal(dict)     
    size_changed_live = Signal(int)  # NEW: Emit size changes during F-drag
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        self.setMouseTracking(True)
        
        self._tool = "pen"
        self._color = "#4C8DFF"
        self._brush_size = 3
        self._opacity = 1.0
        self._pressure_enabled = True
        
        # NEW: State for interactive F-key resizing
        self._is_adjusting_size = False
        self._adjust_start_x = 0
        self._adjust_start_size = 0
        
        self._current_drawing: Optional[Dict] = None
        self._annotations: List[Dict] = []
        
        self._onion_data: List[tuple] = []
        self._max_onion_opacity: float = 0.5
        
        self._undo_stack: List[List[Dict]] = []
        self._redo_stack: List[List[Dict]] = []

        # Instantiate the BrushEngine
        self._brush_engine = BrushEngine()
        
        # FIX: Static canvas for finished strokes (Double Buffering)
        self._static_canvas = QPixmap(self.size())
        self._static_canvas.fill(Qt.GlobalColor.transparent)

    def set_tool(self, tool: str) -> None:
        self._tool = tool
        # Update cursor when tool changes
        if tool == "eraser":
            self.setCursor(self._create_hollow_cursor(self._brush_size))
        else:
            self.unsetCursor()

    def set_color(self, color: str) -> None: self._color = color
    
    def set_brush_size(self, size: int) -> None:
        self._brush_size = int(size)
        # Update cursor size live if eraser is active
        if self._tool == "eraser":
            self.setCursor(self._create_hollow_cursor(self._brush_size))

    def set_opacity(self, opacity: float) -> None: self._opacity = opacity
    
    def set_pressure_enabled(self, enabled: bool) -> None:
        self._pressure_enabled = enabled
        self.update()

    def _create_hollow_cursor(self, size: int) -> QCursor:
        """Generates a hollow circle cursor matching the eraser size."""
        # Add padding so the cursor isn't clipped at the edges
        pad = 4
        pixmap = QPixmap(size + pad * 2, size + pad * 2)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw a black outline first (for visibility on dark backgrounds)
        painter.setPen(QPen(QColor(0, 0, 0, 255), 2))
        painter.drawEllipse(pad, pad, size, size)
        # Draw a white outline inside (for visibility on light backgrounds)
        painter.setPen(QPen(QColor(255, 255, 255, 255), 1))
        painter.drawEllipse(pad, pad, size, size)
        painter.end()
        
        # Set hotspot exactly in the center
        return QCursor(pixmap, (size + pad * 2) // 2, (size + pad * 2) // 2)

    def load_custom_brush(self, json_path: str) -> None:
        preset_name = self._brush_engine.load_preset(json_path)
        if preset_name:
            self.set_tool(preset_name)
            self.update()

    def resizeEvent(self, event) -> None:
        # Resize the static canvas when the window resizes
        self._static_canvas = QPixmap(self.size())
        self._static_canvas.fill(Qt.GlobalColor.transparent)
        self._redraw_static_canvas()
        super().resizeEvent(event)

    def load_annotations(self, current_anns: List[Dict], onion_data: List[tuple], max_opacity: float = 0.5, clear_history: bool = True) -> None:
        self._annotations = current_anns.copy()
        self._onion_data = onion_data
        self._max_onion_opacity = max_opacity
        if clear_history:
            self._undo_stack.clear()
            self._redo_stack.clear()
        
        # Rebuild the static canvas with the loaded strokes
        self._redraw_static_canvas()
        self.update()

    def clear_annotations(self) -> None:
        self._annotations.clear()
        self._onion_data = []
        self._redraw_static_canvas()
        self.update()

    def undo(self) -> None:
        if self._undo_stack:
            self._redo_stack.append(self._annotations.copy())
            self._annotations = self._undo_stack.pop()
            self._redraw_static_canvas()
            self.update()

    def redo(self) -> None:
        if self._redo_stack:
            self._undo_stack.append(self._annotations.copy())
            self._annotations = self._redo_stack.pop()
            self._redraw_static_canvas()
            self.update()

    # --- Event Handling ---

    def tabletEvent(self, event: QTabletEvent) -> None:
        if event.type() == QEvent.Type.TabletPress:
            self._start_stroke(event.position().x(), event.position().y(), event.pressure())
            event.accept()
        elif event.type() == QEvent.Type.TabletMove:
            if self._current_drawing:
                self._add_point(event.position().x(), event.position().y(), event.pressure())
            event.accept()
        elif event.type() == QEvent.Type.TabletRelease:
            self._end_stroke()
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        # Hold F to adjust brush size dynamically
        if event.key() == Qt.Key.Key_F and not self._is_adjusting_size:
            self._is_adjusting_size = True
            cursor_pos = self.mapFromGlobal(QCursor.pos())
            self._adjust_start_x = cursor_pos.x()
            self._adjust_start_size = self._brush_size
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_F:
            self._is_adjusting_size = False
            event.accept()
            return
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._is_adjusting_size:
            event.accept()
            return # Don't draw while adjusting size
            
        self.setFocus()
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_stroke(event.position().x(), event.position().y(), 1.0)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_adjusting_size:
            if event.buttons() & Qt.MouseButton.LeftButton:
                current_x = event.position().x()
                delta = current_x - self._adjust_start_x
                # Drag right increases, left decreases. Divide by 2 for sensitivity.
                new_size = max(1, int(self._adjust_start_size + delta / 2))
                self.size_changed_live.emit(new_size)
            return
            
        if self._current_drawing:
            self._add_point(event.position().x(), event.position().y(), 1.0)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._is_adjusting_size:
            return
        if self._current_drawing:
            self._end_stroke()

    def _get_pressure(self, raw_pressure: float) -> float:
        if not self._pressure_enabled:
            return 1.0
        return max(0.05, min(1.0, raw_pressure))

    def _start_stroke(self, x: float, y: float, pressure: float) -> None:
        self._undo_stack.append(self._annotations.copy())
        self._redo_stack.clear()
        
        x_ratio = x / self.width()
        y_ratio = y / self.height()
        p = self._get_pressure(pressure)
        
        self._current_drawing = {
            "tool_type": self._tool,
            "color": self._color if self._tool != "eraser" else "#000000", # Color irrelevant for eraser
            "brush_size": self._brush_size,
            "opacity": self._opacity,
            "points": [{"x": x_ratio, "y": y_ratio, "p": p}],
            "text_content": None
        }
        
        if self._tool == "text":
            text, ok = QInputDialog.getText(self, "Add Text", "Enter text:")
            if ok and text:
                self._current_drawing["text_content"] = text
                self._annotations.append(self._current_drawing)
                self.annotation_added.emit(self._current_drawing)
                self._draw_to_static_canvas(self._current_drawing)
                self._current_drawing = None
            else:
                self._current_drawing = None
        self.update()

    def _add_point(self, x: float, y: float, pressure: float) -> None:
        if not self._current_drawing: return
        
        x_ratio = x / self.width()
        y_ratio = y / self.height()
        p = self._get_pressure(pressure)
        
        if self._current_drawing["tool_type"] in ["arrow", "rect", "circle"]:
            if len(self._current_drawing["points"]) > 1:
                self._current_drawing["points"][1] = {"x": x_ratio, "y": y_ratio, "p": p}
            else:
                self._current_drawing["points"].append({"x": x_ratio, "y": y_ratio, "p": p})
        else:
            self._current_drawing["points"].append({"x": x_ratio, "y": y_ratio, "p": p})
            
        self.update()

    def _end_stroke(self) -> None:
        if self._current_drawing:
            self._annotations.append(self._current_drawing)
            # Draw the finished stroke to the static canvas
            self._draw_to_static_canvas(self._current_drawing)
            self.annotation_added.emit(self._current_drawing)
            self._current_drawing = None
            self.update()

    # --- Painting ---

    def _redraw_static_canvas(self) -> None:
        """Clears and redraws all finished strokes and onion skins onto the static canvas."""
        self._static_canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(self._static_canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        for rel_frame, anns in self._onion_data:
            onion_color = self._get_onion_color(rel_frame)
            for ann in anns:
                self._draw_annotation(painter, ann, onion_color)
                
        for ann in self._annotations:
            self._draw_annotation(painter, ann, None)
            
        painter.end()

    def _draw_to_static_canvas(self, ann: Dict) -> None:
        """Draws a single annotation onto the static canvas."""
        painter = QPainter(self._static_canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._draw_annotation(painter, ann, None)
        painter.end()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Draw the cached static canvas (O(1) performance)
        painter.drawPixmap(0, 0, self._static_canvas)
        
        # Draw the live stroke on top (only the current drawing is recalculated)
        if self._current_drawing:
            self._draw_annotation(painter, self._current_drawing, None)
            
        painter.end()

    def _get_onion_color(self, rel_frame: int) -> QColor:
        max_dist = max(abs(rel_frame), 1)
        fade = 1.0 - (max_dist - 1) * 0.2 
        alpha = int(255 * self._max_onion_opacity * max(0.1, fade))
        if rel_frame < 0: return QColor(76, 141, 255, alpha)
        else: return QColor(255, 184, 77, alpha)

    def _draw_annotation(self, painter: QPainter, ann: Dict, onion_color: Optional[QColor]) -> None:
        points = ann["points"]
        if not points: return
        
        abs_points = [{"x": int(p["x"] * self.width()), "y": int(p["y"] * self.height()), "p": p.get("p", 1.0)} for p in points]
        tool = ann.get("tool_type", "pen")
        base_size = ann.get("brush_size", 3)

        # ==========================================
        # PHOTOSHOP-LIKE PIXEL ERASER
        # ==========================================
        if tool == "eraser":
            # Save the current composition mode so we can restore it
            old_mode = painter.compositionMode()
            # DestinationOut makes the drawn pixels erase the canvas (making them transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
            
            # Eraser ignores onion color and opacity settings, relies purely on pressure for strength
            if len(abs_points) == 1:
                p = abs_points[0]
                # Alpha is based on pressure (0.5 pressure = 128 alpha = 50% erased)
                pen = QPen(QColor(0, 0, 0, int(255 * p["p"])), int(base_size))
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawPoint(QPoint(p["x"], p["y"]))
            else:
                for i in range(len(abs_points) - 1):
                    p1, p2 = abs_points[i], abs_points[i+1]
                    avg_p = (p1["p"] + p2["p"]) / 2.0
                    pen = QPen(QColor(0, 0, 0, int(255 * avg_p)), int(base_size))
                    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                    painter.setPen(pen)
                    painter.drawLine(QPoint(p1["x"], p1["y"]), QPoint(p2["x"], p2["y"]))
                    
            # Restore composition mode so subsequent draws aren't erased
            painter.setCompositionMode(old_mode)
            return

        # ==========================================
        # NORMAL DRAWING TOOLS
        # ==========================================
        if onion_color:
            painter.setOpacity(1.0)
            color = onion_color
        else:
            painter.setOpacity(ann.get("opacity", 1.0))
            color = QColor(ann["color"])

        if tool == "pencil":
            if len(abs_points) == 1:
                p = abs_points[0]
                self._brush_engine.draw_point(painter, QPoint(p["x"], p["y"]), tool, color, base_size, p["p"])
            else:
                for i in range(len(abs_points) - 1):
                    p1, p2 = abs_points[i], abs_points[i+1]
                    avg_p = (p1["p"] + p2["p"]) / 2.0
                    self._brush_engine.draw_segment(painter, QPoint(p1["x"], p1["y"]), QPoint(p2["x"], p2["y"]), tool, color, base_size, avg_p)
                    
        elif tool == "pen":
            if len(abs_points) == 1:
                p = abs_points[0]
                pen = QPen(color, int(base_size * p["p"]))
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawPoint(QPoint(p["x"], p["y"]))
            else:
                for i in range(len(abs_points) - 1):
                    p1, p2 = abs_points[i], abs_points[i+1]
                    avg_p = (p1["p"] + p2["p"]) / 2.0
                    pen = QPen(color, int(base_size * avg_p))
                    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                    painter.setPen(pen)
                    painter.drawLine(QPoint(p1["x"], p1["y"]), QPoint(p2["x"], p2["y"]))
                    
        elif tool == "rect" and len(abs_points) >= 2:
            painter.setPen(QPen(color, base_size))
            rect = QRectF(QPoint(abs_points[0]["x"], abs_points[0]["y"]), QPoint(abs_points[1]["x"], abs_points[1]["y"])).normalized()
            painter.drawRect(rect)
        elif tool == "circle" and len(abs_points) >= 2:
            painter.setPen(QPen(color, base_size))
            radius = (abs_points[1]["x"] - abs_points[0]["x"])
            painter.drawEllipse(QPoint(abs_points[0]["x"], abs_points[0]["y"]), radius, radius)
        elif tool == "arrow" and len(abs_points) >= 2:
            painter.setPen(QPen(color, base_size))
            painter.drawLine(QPoint(abs_points[0]["x"], abs_points[0]["y"]), QPoint(abs_points[1]["x"], abs_points[1]["y"]))
            self._draw_arrowhead(painter, QPoint(abs_points[0]["x"], abs_points[0]["y"]), QPoint(abs_points[1]["x"], abs_points[1]["y"]))
        elif tool == "text" and ann.get("text_content"):
            font = QFont("SF Pro Display", base_size * 4)
            painter.setFont(font)
            painter.drawText(abs_points[0]["x"], abs_points[0]["y"], ann["text_content"])

    def _draw_arrowhead(self, painter: QPainter, start: QPoint, end: QPoint) -> None:
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        size = 10 + painter.pen().width()
        p1 = QPoint(end.x() - int(size * math.cos(angle - math.pi/6)), end.y() - int(size * math.sin(angle - math.pi/6)))
        p2 = QPoint(end.x() - int(size * math.cos(angle + math.pi/6)), end.y() - int(size * math.sin(angle + math.pi/6)))
        painter.drawPolygon(QPolygon([end, p1, p2]))