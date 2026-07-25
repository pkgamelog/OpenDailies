"""
Custom Annotation Toolbar (Premium Vertical Floating Panel).
Ultra-compact, icon-only, with custom icon support and popup menus.
"""
import os
from PySide6.QtWidgets import (QApplication, QToolBar, QSpinBox, QPushButton, QLabel, 
                               QColorDialog, QSlider, QWidget, 
                               QVBoxLayout, QMenu, QToolButton, QWidgetAction,
                               QGridLayout, QFrame, QFileDialog)
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QSize, QRectF, QByteArray
from PySide6.QtGui import QPalette, QAction, QIcon, QPixmap, QPainter, QPen, QColor, QFont, QPolygon
from PySide6.QtSvg import QSvgRenderer

class AnnotationToolBar(QToolBar):
    """A self-contained, minimal vertical toolbar for annotation drawing tools."""
    
    tool_changed = Signal(str)
    color_changed = Signal(str)
    size_changed = Signal(int)
    undo_clicked = Signal()
    clear_clicked = Signal()
    onion_changed = Signal()
    custom_brush_requested = Signal(str)

    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    _ICONS_DIR = os.path.join(_BASE_DIR, "assets", "icons", "annotation_toolbar")

    ICON_PATHS = {
        "pen": os.path.join(_ICONS_DIR, "pen.svg"),
        "pencil": os.path.join(_ICONS_DIR, "pencil.svg"), 
        "rect": os.path.join(_ICONS_DIR, "square.svg"),
        "arrow": os.path.join(_ICONS_DIR, "arrow.svg"),
        "circle": os.path.join(_ICONS_DIR, "circle.svg"),
        "text": os.path.join(_ICONS_DIR, "text.svg"),
        "eraser": os.path.join(_ICONS_DIR, "eraser.svg"),
        "undo": os.path.join(_ICONS_DIR, "undo.svg"),
        "clear": os.path.join(_ICONS_DIR, "trash.svg"),
        "onion": os.path.join(_ICONS_DIR, "onion.svg")
    }

    def __init__(self, parent=None):
        super().__init__("Annotations", parent)
        self.setMovable(False)
        self.setFixedWidth(80)
        self.setIconSize(QSize(52, 52))
        self._current_color = "#4C8DFF"
        self._color_menu = None  
        
        # NEW: Per-tool size memory
        self._current_tool = "pen"
        self._tool_sizes = {
            "pen": 3, "pencil": 3, "rect": 5, "arrow": 5, 
            "circle": 5, "text": 12, "eraser": 20
        }
        self._brush_size = self._tool_sizes["pen"]
        
        self._init_ui()

    def _get_icon(self, icon_name: str, fallback_draw_func) -> QIcon:
        icon_path = self.ICON_PATHS.get(icon_name)
        if icon_path and os.path.exists(icon_path):
            try:
                with open(icon_path, 'r', encoding='utf-8') as f:
                    svg_data = f.read()
                
                svg_data = svg_data.replace('currentColor', '#FFFFFF')
                svg_data = svg_data.replace('#000000', '#FFFFFF')
                svg_data = svg_data.replace('#000', '#FFFFFF')
                svg_data = svg_data.replace('black', '#FFFFFF')
                svg_data = svg_data.replace('fill="none"', 'fill="transparent"')
                svg_data = svg_data.replace('stroke="none"', 'stroke="transparent"')
                
                renderer = QSvgRenderer(QByteArray(svg_data.encode('utf-8')))
                if renderer.isValid():
                    pix = QPixmap(48, 48)
                    pix.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pix)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    renderer.render(painter, QRectF(0, 0, 48, 48))
                    painter.end()
                    return QIcon(pix)
            except Exception as e:
                print(f"Error loading SVG {icon_path}: {e}")
                
        pix = QPixmap(48, 48)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(2.0, 2.0)
        fallback_draw_func(p)
        p.end()
        return QIcon(pix)

    def _init_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 8, 2, 8) 
        layout.setSpacing(6) 
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.setStyleSheet("""
            QToolBar { background: transparent; border: none; }
            QToolButton { background: transparent; border: none; padding: 4px; border-radius: 6px; margin: 0; }
            QToolButton:hover { background-color: #2D2E30; }
            QToolButton:pressed { background-color: #3B82F6; color: #FFFFFF; }
            QToolButton:checked { background-color: #252526; color: #4C8DFF; border: 1px solid #2D2E30; }
            QSpinBox { background-color: #252526; border: 1px solid #2D2E30; border-radius: 6px; padding: 4px; min-height: 20px; }
        """)

        # 1. Drawing Tools
        icon_pen = self._get_icon("pen", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 2)), p.drawLine(4, 20, 20, 4)))
        self.tool_pen = QAction(icon_pen, "Pen", self, checkable=True)
        self.tool_pen.triggered.connect(lambda: self._set_tool("pen"))
        btn_pen = QToolButton(); btn_pen.setDefaultAction(self.tool_pen); layout.addWidget(btn_pen)

        icon_pencil = self._get_icon("pencil", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 2)), p.drawLine(4, 20, 20, 4), p.drawLine(16, 4, 20, 8), p.drawLine(20, 8, 16, 12)))
        self.tool_pencil = QAction(icon_pencil, "Pencil", self, checkable=True)
        self.tool_pencil.triggered.connect(lambda: self._set_tool("pencil"))
        btn_pencil = QToolButton(); btn_pencil.setDefaultAction(self.tool_pencil); layout.addWidget(btn_pencil)

        icon_rect = self._get_icon("rect", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 2)), p.drawRect(4, 4, 16, 16)))
        self.tool_rect = QAction(icon_rect, "Rectangle", self, checkable=True)
        self.tool_rect.triggered.connect(lambda: self._set_tool("rect"))
        btn_rect = QToolButton(); btn_rect.setDefaultAction(self.tool_rect); layout.addWidget(btn_rect)

        icon_arrow = self._get_icon("arrow", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 2)), p.drawLine(4, 20, 20, 4), p.drawPolygon(QPolygon([QPoint(20,4), QPoint(14,4), QPoint(20,10)]))))
        self.tool_arrow = QAction(icon_arrow, "Arrow", self, checkable=True)
        self.tool_arrow.triggered.connect(lambda: self._set_tool("arrow"))
        btn_arrow = QToolButton(); btn_arrow.setDefaultAction(self.tool_arrow); layout.addWidget(btn_arrow)

        icon_circle = self._get_icon("circle", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 2)), p.drawEllipse(4, 4, 16, 16)))
        self.tool_circle = QAction(icon_circle, "Circle", self, checkable=True)
        self.tool_circle.triggered.connect(lambda: self._set_tool("circle"))
        btn_circle = QToolButton(); btn_circle.setDefaultAction(self.tool_circle); layout.addWidget(btn_circle)

        icon_text = self._get_icon("text", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 2)), p.setFont(QFont("SF Pro", 14, QFont.Bold)), p.drawText(QRect(4, 4, 16, 16), Qt.AlignmentFlag.AlignCenter, "T")))
        self.tool_text = QAction(icon_text, "Text", self, checkable=True)
        self.tool_text.triggered.connect(lambda: self._set_tool("text"))
        btn_text = QToolButton(); btn_text.setDefaultAction(self.tool_text); layout.addWidget(btn_text)

        icon_eraser = self._get_icon("eraser", lambda p: (p.setPen(QPen(QColor("#FF5A5F"), 2)), p.drawRect(4, 4, 16, 16), p.drawLine(4, 4, 20, 20)))
        self.tool_eraser = QAction(icon_eraser, "Eraser", self, checkable=True)
        self.tool_eraser.triggered.connect(lambda: self._set_tool("eraser"))
        btn_eraser = QToolButton(); btn_eraser.setDefaultAction(self.tool_eraser); layout.addWidget(btn_eraser)
        
        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.HLine); sep1.setStyleSheet("background-color: #2D2E30; max-height: 1px; margin: 4px 0;")
        layout.addWidget(sep1)

        # 2. Actions (Undo/Clear)
        icon_undo = self._get_icon("undo", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 2)), p.drawArc(QRect(4, 4, 16, 16), 0, 270 * 16), p.drawLine(QPoint(14, 4), QPoint(20, 4)), p.drawLine(QPoint(20, 4), QPoint(20, 10))))
        self.undo_act = QAction(icon_undo, "Undo", self)
        self.undo_act.triggered.connect(self.undo_clicked.emit)
        btn_undo = QToolButton(); btn_undo.setDefaultAction(self.undo_act); layout.addWidget(btn_undo)

        icon_clear = self._get_icon("clear", lambda p: (p.setPen(QPen(QColor("#FF5A5F"), 2)), p.drawLine(4, 4, 20, 20), p.drawLine(20, 4, 4, 20)))
        self.clear_act = QAction(icon_clear, "Clear Frame", self)
        self.clear_act.triggered.connect(self.clear_clicked.emit)
        btn_clear = QToolButton(); btn_clear.setDefaultAction(self.clear_act); layout.addWidget(btn_clear)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine); sep2.setStyleSheet("background-color: #2D2E30; max-height: 1px; margin: 4px 0;")
        layout.addWidget(sep2)

        # 3. Brush Settings
        self.size_btn = QToolButton(self)
        self.size_btn.setText(str(self._brush_size)) 
        self.size_btn.setToolTip("Brush Size")
        self.size_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.size_btn.setStyleSheet("QToolButton { color: #FFFFFF; font-weight: bold; font-size: 11px; }")
        
        size_menu = QMenu(self)
        size_widget = QWidget()
        size_layout = QVBoxLayout(size_widget)
        size_layout.setContentsMargins(8, 8, 8, 8)
        self.thickness_spin = QSpinBox()
        self.thickness_spin.setRange(1, 150) # Increased max size for eraser
        self.thickness_spin.setValue(self._brush_size)
        self.thickness_spin.setSuffix("px")
        self.thickness_spin.valueChanged.connect(self.size_changed.emit)
        self.thickness_spin.valueChanged.connect(lambda v: self.size_btn.setText(f"{v}"))
        size_layout.addWidget(self.thickness_spin)
        
        size_action = QWidgetAction(self)
        size_action.setDefaultWidget(size_widget)
        size_menu.addAction(size_action)
        self.size_btn.setMenu(size_menu)
        layout.addWidget(self.size_btn)

        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(28, 28) 
        self.color_btn.setToolTip("Annotation Color")
        self.color_btn.setStyleSheet(f"background-color: {self._current_color}; border: 1px solid #2D2E30; border-radius: 6px;")
        self.color_btn.clicked.connect(self._show_color_popup)
        self.color_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.color_btn)

        # 4. Onion Skin
        self.onion_btn = QToolButton(self)
        self.onion_btn.setToolTip("Onion Skin Settings")
        self.onion_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.onion_btn.setIcon(self._get_icon("onion", lambda p: (p.setRenderHint(QPainter.RenderHint.Antialiasing), p.setPen(Qt.PenStyle.NoPen), p.setBrush(QColor("#FFFFFF")), p.drawEllipse(7, 7, 12, 12), p.setBrush(QColor("#808080")), p.drawEllipse(14, 14, 12, 12))))
        layout.addWidget(self.onion_btn)
        
        onion_menu = QMenu(self)
        onion_widget = QWidget()
        onion_layout = QGridLayout(onion_widget)
        onion_layout.setContentsMargins(8, 8, 8, 8)
        onion_layout.setSpacing(8)
        
        onion_layout.addWidget(QLabel("Before:"), 0, 0)
        self.onion_before_spin = QSpinBox()
        self.onion_before_spin.setRange(0, 10)
        self.onion_before_spin.setValue(1)
        self.onion_before_spin.valueChanged.connect(self.onion_changed.emit)
        onion_layout.addWidget(self.onion_before_spin, 0, 1)
        
        onion_layout.addWidget(QLabel("After:"), 1, 0)
        self.onion_after_spin = QSpinBox()
        self.onion_after_spin.setRange(0, 10)
        self.onion_after_spin.setValue(1)
        self.onion_after_spin.valueChanged.connect(self.onion_changed.emit)
        onion_layout.addWidget(self.onion_after_spin, 1, 1)
        
        onion_layout.addWidget(QLabel("Opacity:"), 2, 0)
        self.onion_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.onion_opacity_slider.setRange(0, 100)
        self.onion_opacity_slider.setValue(50)
        self.onion_opacity_slider.setFixedWidth(100)
        self.onion_opacity_slider.valueChanged.connect(self.onion_changed.emit)
        onion_layout.addWidget(self.onion_opacity_slider, 2, 1)
        
        onion_action = QWidgetAction(self)
        onion_action.setDefaultWidget(onion_widget)
        onion_menu.addAction(onion_action)
        self.onion_btn.setMenu(onion_menu)

        # Custom Brush Import Button
        self.import_brush_btn = QToolButton(self)
        self.import_brush_btn.setText("+")
        self.import_brush_btn.setToolTip("Import Custom Brush (.odbrush)")
        self.import_brush_btn.setStyleSheet("QToolButton { color: #FFFFFF; font-weight: bold; font-size: 14px; } QToolButton:hover { background-color: #2D2E30; }")
        self.import_brush_btn.clicked.connect(self._import_custom_brush)
        layout.addWidget(self.import_brush_btn)

        self.tool_pen.setChecked(True)
        self.addWidget(container)

        # FIX: Prevent tool buttons from stealing keyboard focus (so Spacebar plays video instead of clicking the button)
        for btn in self.findChildren(QToolButton):
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for btn in self.findChildren(QPushButton):
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _import_custom_brush(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Custom Brush", "", "OpenDailies Brush (*.odbrush)")
        if file_path:
            self.custom_brush_requested.emit(file_path)

    def set_brush_size(self, size: int) -> None:
        size = max(1, int(size)) # Ensure it's never below 1
        self._brush_size = size
        # Save the size for the currently active tool
        self._tool_sizes[self._current_tool] = size
        
        # Update UI safely without triggering infinite loops
        self.thickness_spin.blockSignals(True)
        self.thickness_spin.setValue(size)
        self.thickness_spin.blockSignals(False)
        self.size_btn.setText(f"{size}")
        
        self.size_changed.emit(size)

    def _show_color_popup(self):
        self._color_menu = QMenu(self)
        self._color_menu.setStyleSheet("""
            QMenu { background-color: #202124; border: 1px solid #2D2E30; border-radius: 8px; padding: 8px; }
            QMenu::item { background-color: transparent; padding: 4px; border-radius: 4px; }
            QMenu::item:selected { background-color: #2D2E30; }
            QPushButton#swatchBtn { border: 1px solid #2D2E30; border-radius: 6px; }
            QPushButton#swatchBtn:hover { border: 2px solid #4C8DFF; }
            QPushButton#customBtn { background-color: transparent; color: #FFFFFF; border: 1px solid #2D2E30; text-align: center; border-radius: 6px; }
            QPushButton#customBtn:hover { background-color: #2D2E30; }
        """)
        
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        colors = [
            "#FFFFFF", "#000000", "#FF5A5F", "#4CAF50", "#4C8DFF", "#FFB84D",
            "#A9A9A9", "#3B82F6", "#FF00FF", "#00FFFF", "#8B008B", "#008B8B"
        ]
        
        for i, color in enumerate(colors):
            btn = QPushButton()
            btn.setObjectName("swatchBtn")
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(f"background-color: {color};")
            btn.clicked.connect(lambda checked=False, c=color: self._select_color(c))
            layout.addWidget(btn, i // 4, i % 4)
            
        custom_btn = QPushButton("Custom Color...")
        custom_btn.setObjectName("customBtn")
        custom_btn.setFixedHeight(32)
        custom_btn.clicked.connect(self._open_native_picker)
        layout.addWidget(custom_btn, 3, 0, 1, 4)
        
        action = QWidgetAction(self)
        action.setDefaultWidget(widget)
        self._color_menu.addAction(action)
        
        point = self.color_btn.mapToGlobal(QPoint(0, self.color_btn.height()))
        self._color_menu.exec(point)

    def _select_color(self, color: str):
        self._current_color = color
        self.color_btn.setStyleSheet(f"background-color: {color}; border: 1px solid #2D2E30; border-radius: 6px;")
        self.color_changed.emit(color)
        if self._color_menu:
            self._color_menu.close()

    def _open_native_picker(self):
        if self._color_menu:
            self._color_menu.close()
            
        dialog = QColorDialog(QColor(self._current_color), self)
        dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
        dialog.setStyleSheet("""
            QColorDialog { background-color: #171717; color: #FFFFFF; }
            QPushButton { background-color: #252526; color: #FFFFFF; border: 1px solid #2D2E30; padding: 8px 16px; border-radius: 6px; min-width: 80px; }
            QPushButton:hover { background-color: #2D2E30; border: 1px solid #4C8DFF; }
            QFrame { background-color: #171717; }
            QLabel { color: #FFFFFF; }
            QSpinBox, QLineEdit { background-color: #252526; color: #FFFFFF; border: 1px solid #2D2E30; padding: 6px; border-radius: 6px; }
        """)
        
        if dialog.exec() == QColorDialog.DialogCode.Accepted:
            color = dialog.currentColor()
            if color.isValid():
                self._current_color = color.name()
                self.color_btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #2D2E30; border-radius: 6px;")
                self.color_changed.emit(color.name())

    def _set_tool(self, tool: str):
        # 1. Save the current size for the tool we are leaving
        self._tool_sizes[self._current_tool] = self._brush_size
        
        for action in [self.tool_pen, self.tool_pencil, self.tool_rect, self.tool_arrow, self.tool_circle, self.tool_text, self.tool_eraser]:
            action.setChecked(False)
        
        if tool == "pen": self.tool_pen.setChecked(True)
        elif tool == "pencil": self.tool_pencil.setChecked(True)
        elif tool == "rect": self.tool_rect.setChecked(True)
        elif tool == "arrow": self.tool_arrow.setChecked(True)
        elif tool == "circle": self.tool_circle.setChecked(True)
        elif tool == "text": self.tool_text.setChecked(True)
        elif tool == "eraser": self.tool_eraser.setChecked(True)
        
        # 2. Set the new tool and load its specific size
        self._current_tool = tool
        new_size = self._tool_sizes.get(tool, 3)
        self.set_brush_size(new_size)
        
        self.tool_changed.emit(tool)