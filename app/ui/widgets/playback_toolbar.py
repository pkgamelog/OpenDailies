"""Custom Main Toolbar (Premium Modular Transport Bar)."""
import os
import re
from PySide6.QtWidgets import QToolBar, QComboBox, QLabel, QToolButton, QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QSize, QRectF, QByteArray
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QPen, QColor, QFont, QPolygon
from PySide6.QtSvg import QSvgRenderer
from app.playback.frame_utils import format_display_info

class PlaybackToolBar(QToolBar):
    play_clicked = Signal()
    pause_clicked = Signal()
    stop_clicked = Signal()
    prev_frame_clicked = Signal()
    next_frame_clicked = Signal()
    loop_toggled = Signal(bool)
    speed_changed = Signal(float)
    compare_toggled = Signal(bool)
    sync_toggled = Signal(bool)
    annotations_toggled = Signal(bool)
    timecode_toggled = Signal(bool)
    fps_override_changed = Signal(float)
    display_mode_changed = Signal(int)
    subtitle_mode_changed = Signal(int)

    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    _ICONS_DIR = os.path.join(_BASE_DIR, "assets", "icons", "playback_toolbar")

    ICON_PATHS = {
        "play": os.path.join(_ICONS_DIR, "play.svg"),
        "pause": os.path.join(_ICONS_DIR, "pause.svg"),
        "stop": os.path.join(_ICONS_DIR, "stop.svg"),
        "prev": os.path.join(_ICONS_DIR, "prev.svg"),
        "next": os.path.join(_ICONS_DIR, "next.svg"),
        "loop": os.path.join(_ICONS_DIR, "loop.svg"),
        "compare": os.path.join(_ICONS_DIR, "compare.svg"),
        "sync": os.path.join(_ICONS_DIR, "sync.svg"),
        "annotations": os.path.join(_ICONS_DIR, "annotations.svg"),
        "timecode": os.path.join(_ICONS_DIR, "timecode.svg"),
        "framecode": os.path.join(_ICONS_DIR, "framecode.svg")
    }

    def __init__(self, parent=None):
        super().__init__("Main Controls", parent)
        self.setMovable(False)
        self.setIconSize(QSize(40, 40))
        self.setFixedHeight(64)
        
        self._current_frame = 0
        self._total_frames = 0
        self._fps = 24.0
        self._display_mode = 2
        self._subtitle_mode = 0
        self._is_playing = False  
        
        self._icon_cache = {}
        self._init_ui()

    def _get_icon(self, icon_name: str, fallback_draw_func) -> QIcon:
        if icon_name in self._icon_cache:
            return self._icon_cache[icon_name]
            
        icon_path = self.ICON_PATHS.get(icon_name)
        if icon_path and os.path.exists(icon_path):
            try:
                with open(icon_path, 'r', encoding='utf-8') as f:
                    svg_data = f.read()
                
                svg_data = re.sub(r'fill="(?!none|transparent)[^"]*"', 'fill="#FFFFFF"', svg_data, flags=re.IGNORECASE)
                svg_data = re.sub(r'stroke="(?!none|transparent)[^"]*"', 'stroke="#FFFFFF"', svg_data, flags=re.IGNORECASE)
                svg_data = svg_data.replace('currentColor', '#FFFFFF')
                
                renderer = QSvgRenderer(QByteArray(svg_data.encode('utf-8')))
                if renderer.isValid():
                    pix = QPixmap(48, 48)
                    pix.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pix)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    renderer.render(painter, QRectF(0, 0, 48, 48))
                    painter.end()
                    icon = QIcon(pix)
                    self._icon_cache[icon_name] = icon
                    return icon
            except Exception: pass
                
        pix = QPixmap(48, 48)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(2.0, 2.0)
        fallback_draw_func(p)
        p.end()
        icon = QIcon(pix)
        self._icon_cache[icon_name] = icon
        return icon

    def _init_ui(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(16, 2, 16, 2)
        layout.setSpacing(16)
        self.setStyleSheet("""
            QToolBar { background: transparent; border: none; }
            QToolButton { background: transparent; border: none; padding: 6px; border-radius: 6px; }
            QToolButton:hover { background-color: #2D2E30; }
            QToolButton:pressed { background-color: #3B82F6; }
            QToolButton:checked { background-color: #2D2E30; color: #4C8DFF; }
            QComboBox, QSpinBox { background-color: #2D2E30; border: 1px solid #2D2E30; border-radius: 6px; padding: 4px 8px; min-height: 20px; }
            QComboBox:hover, QSpinBox:hover { border: 1px solid #4C8DFF; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView { background-color: #202124; border: 1px solid #2D2E30; border-radius: 8px; padding: 4px; selection-background-color: #4C8DFF; }
        """)

        # 1. LEFT SECTION
        left_widget = QWidget()
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        self._info_label = QLabel("")
        self._info_label.setStyleSheet("color: #A9A9A9; font-weight: 500; background: transparent;")
        left_layout.addWidget(self._info_label)
        self.btn_display_mode = QToolButton()
        self.btn_display_mode.setIcon(self._get_icon("timecode", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 1)), p.drawText(QRect(2,2,20,20), Qt.AlignmentFlag.AlignCenter, "TC"))))
        self.btn_display_mode.setToolTip("Toggle Timecode / Frame Code")
        self.btn_display_mode.clicked.connect(self._toggle_display_mode)
        left_layout.addWidget(self.btn_display_mode)
        self._time_label = QLabel("00:00:00:00  |  Frame: 0 / 0")
        self._time_label.setObjectName("timeLabel")
        left_layout.addWidget(self._time_label)
        layout.addWidget(left_widget)
        layout.addStretch(1)

        # 2. CENTER SECTION
        center_widget = QWidget()
        center_layout = QHBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)
        
        icon_prev = self._get_icon("prev", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 2)), p.drawLine(16, 4, 8, 12), p.drawLine(8, 12, 16, 20), p.drawLine(4, 4, 4, 20)))
        self.prev_act = QAction(icon_prev, "Prev Frame", self); self.prev_act.triggered.connect(self.prev_frame_clicked.emit)
        btn_prev = QToolButton(); btn_prev.setDefaultAction(self.prev_act); center_layout.addWidget(btn_prev)
        
        icon_play = self._get_icon("play", lambda p: (p.setBrush(QColor("#FFFFFF")), p.setPen(Qt.PenStyle.NoPen), p.drawPolygon(QPolygon([QPoint(8, 5), QPoint(8, 19), QPoint(18, 12)]))))
        self.play_act = QAction(icon_play, "Play/Pause", self)
        self.play_act.triggered.connect(self._on_play_pause_clicked)  
        self.btn_play = QToolButton(); self.btn_play.setDefaultAction(self.play_act); center_layout.addWidget(self.btn_play)
        
        icon_stop = self._get_icon("stop", lambda p: (p.setBrush(QColor("#FFFFFF")), p.setPen(Qt.PenStyle.NoPen), p.drawRect(6, 6, 12, 12)))
        self.stop_act = QAction(icon_stop, "Stop", self); self.stop_act.triggered.connect(self.stop_clicked.emit)
        btn_stop = QToolButton(); btn_stop.setDefaultAction(self.stop_act); center_layout.addWidget(btn_stop)
        
        icon_next = self._get_icon("next", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 2)), p.drawLine(8, 4, 16, 12), p.drawLine(16, 12, 8, 20), p.drawLine(20, 4, 20, 20)))
        self.next_act = QAction(icon_next, "Next Frame", self); self.next_act.triggered.connect(self.next_frame_clicked.emit)
        btn_next = QToolButton(); btn_next.setDefaultAction(self.next_act); center_layout.addWidget(btn_next)
        
        center_layout.addSpacing(16)
        
        icon_loop = self._get_icon("loop", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 2)), p.drawArc(QRect(4, 4, 16, 16), 0, 270 * 16), p.drawLine(QPoint(14, 4), QPoint(18, 4)), p.drawLine(QPoint(18, 4), QPoint(18, 8))))
        self.loop_action = QAction(icon_loop, "Loop Video", self, checkable=True); self.loop_action.triggered.connect(self.loop_toggled.emit)
        btn_loop = QToolButton(); btn_loop.setDefaultAction(self.loop_action); center_layout.addWidget(btn_loop)
        layout.addWidget(center_widget)
        layout.addStretch(1)

        # 3. RIGHT SECTION
        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        
        icon_compare = self._get_icon("compare", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 2)), p.drawRect(2, 4, 8, 16), p.drawRect(14, 4, 8, 16)))
        self.compare_action = QAction(icon_compare, "Compare A/B", self, checkable=True); self.compare_action.toggled.connect(self.compare_toggled.emit)
        btn_compare = QToolButton(); btn_compare.setDefaultAction(self.compare_action); right_layout.addWidget(btn_compare)
        
        icon_sync = self._get_icon("sync", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 2)), p.drawLine(4, 8, 20, 8), p.drawLine(4, 16, 20, 16), p.drawLine(8, 5, 4, 8), p.drawLine(8, 11, 4, 8), p.drawLine(16, 13, 20, 16), p.drawLine(16, 19, 20, 16)))
        self.sync_action = QAction(icon_sync, "Sync A/B", self, checkable=True); self.sync_action.setChecked(True); self.sync_action.toggled.connect(self.sync_toggled.emit)
        btn_sync = QToolButton(); btn_sync.setDefaultAction(self.sync_action); right_layout.addWidget(btn_sync)
        
        icon_anno = self._get_icon("annotations", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 2)), p.drawLine(4, 20, 20, 4), p.drawPolygon(QPolygon([QPoint(20,4), QPoint(14,4), QPoint(20,10)]))))
        self.anno_action = QAction(icon_anno, "Toggle Annotations", self, checkable=True); self.anno_action.setChecked(True); self.anno_action.toggled.connect(self.annotations_toggled.emit)
        btn_anno = QToolButton(); btn_anno.setDefaultAction(self.anno_action); right_layout.addWidget(btn_anno)
        
        icon_tc = self._get_icon("timecode", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 1)), p.drawText(QRect(2,2,20,20), Qt.AlignmentFlag.AlignCenter, "TC")))
        self.tc_action = QAction(icon_tc, "Toggle Timecode Overlay", self, checkable=True); self.tc_action.toggled.connect(self.timecode_toggled.emit)
        btn_tc = QToolButton(); btn_tc.setDefaultAction(self.tc_action); right_layout.addWidget(btn_tc)

        self.btn_subtitle_mode = QToolButton()
        self.btn_subtitle_mode.setText("CC: Off")
        self.btn_subtitle_mode.setToolTip("Toggle Subtitles (Off / Bake CC / SRT / Both)")
        self.btn_subtitle_mode.setStyleSheet("QToolButton { color: #A9A9A9; font-size: 11px; font-weight: bold; padding: 4px 8px; } QToolButton:hover { background-color: #2D2E30; color: #FFFFFF; }")
        self.btn_subtitle_mode.clicked.connect(self._toggle_subtitle_mode)
        right_layout.addWidget(self.btn_subtitle_mode)

        right_layout.addSpacing(16)
        self._speed_box = QComboBox()
        self._speed_box.addItems(["0.5x", "1x", "1.5x", "2x"])
        self._speed_box.setCurrentText("1x")
        self._speed_box.currentTextChanged.connect(lambda t: self.speed_changed.emit(float(t.replace('x',''))))
        right_layout.addWidget(self._speed_box)
        right_layout.addWidget(QLabel("FPS:"))
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["Source", "23.976", "24", "25", "29.97", "30", "48", "60"])
        self.fps_combo.setFixedWidth(70)
        self.fps_combo.currentTextChanged.connect(self._on_fps_changed)
        right_layout.addWidget(self.fps_combo)
        layout.addWidget(right_widget)
        self.addWidget(container)

        # FIX: Prevent tool buttons from stealing keyboard focus (so Spacebar plays video instead of clicking the button)
        for btn in self.findChildren(QToolButton):
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for btn in self.findChildren(QPushButton):
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _on_play_pause_clicked(self):
        if self._is_playing:
            self.pause_clicked.emit()
        else:
            self.play_clicked.emit()

    def _toggle_display_mode(self):
        self._display_mode = (self._display_mode + 1) % 3
        self.display_mode_changed.emit(self._display_mode)
        if self._display_mode == 0: self.btn_display_mode.setIcon(self._get_icon("timecode", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 1)), p.drawText(QRect(2,2,20,20), Qt.AlignmentFlag.AlignCenter, "TC"))))
        elif self._display_mode == 1: self.btn_display_mode.setIcon(self._get_icon("framecode", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 1)), p.drawText(QRect(2,2,20,20), Qt.AlignmentFlag.AlignCenter, "FR"))))
        else: self.btn_display_mode.setIcon(self._get_icon("annotations", lambda p: (p.setPen(QPen(QColor("#FFFFFF"), 1)), p.drawText(QRect(2,2,20,20), Qt.AlignmentFlag.AlignCenter, "ALL"))))
        self._update_time_display()

    def _toggle_subtitle_mode(self):
        self._subtitle_mode = (self._subtitle_mode + 1) % 4
        self.subtitle_mode_changed.emit(self._subtitle_mode)
        if self._subtitle_mode == 0: self.btn_subtitle_mode.setText("CC: Off")
        elif self._subtitle_mode == 1: self.btn_subtitle_mode.setText("CC: Bake")
        elif self._subtitle_mode == 2: self.btn_subtitle_mode.setText("CC: SRT")
        elif self._subtitle_mode == 3: self.btn_subtitle_mode.setText("CC: Both")

    def update_play_state(self, is_playing: bool):
        self._is_playing = is_playing  
        if is_playing: self.play_act.setIcon(self._get_icon("pause", lambda p: (p.setBrush(QColor("#FFFFFF")), p.setPen(Qt.PenStyle.NoPen), p.drawRect(7, 5, 4, 14), p.drawRect(13, 5, 4, 14))))
        else: self.play_act.setIcon(self._get_icon("play", lambda p: (p.setBrush(QColor("#FFFFFF")), p.setPen(Qt.PenStyle.NoPen), p.drawPolygon(QPolygon([QPoint(8, 5), QPoint(8, 19), QPoint(18, 12)])))))

    def set_media_info(self, frame: int, total_frames: int, fps: float):
        self._current_frame = frame
        self._total_frames = total_frames
        self._fps = fps
        self._update_time_display()

    def _update_time_display(self):
        self._time_label.setText(format_display_info(self._current_frame, self._total_frames, self._fps, self._display_mode))

    def _on_fps_changed(self, text: str):
        if text == "Source": self.fps_override_changed.emit(0.0)
        else: self.fps_override_changed.emit(float(text))

    def update_info(self, text: str):
        self._info_label.setText(text)