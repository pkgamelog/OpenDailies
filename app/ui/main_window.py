"""
Main Application Window (Full-Width Timeline Layout).
"""
from typing import Optional
import logging
import os
import glob
import shutil
import sys
import ctypes
import subprocess
import tempfile
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QScrollArea, 
    QFrame, QTabWidget, QStatusBar, QApplication, QMenuBar, QFileDialog, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QColor

# Mixins
from app.ui.mixins.media_mixin import MediaMixin
from app.ui.mixins.review_mixin import ReviewMixin
from app.ui.mixins.project_mixin import ProjectMixin

# Components
from app.playback.playback_engine import PlaybackEngine
from app.timeline.timeline_widget import TimelineWidget
from app.ui.widgets.annotation_overlay import AnnotationOverlay
from app.ui.widgets.annotation_toolbar import AnnotationToolBar
from app.ui.widgets.playback_toolbar import PlaybackToolBar
from app.ui.widgets.comment_panel import CommentPanel
from app.ui.widgets.bookmark_panel import BookmarkPanel
from app.ui.widgets.video_display_widget import VideoDisplayWidget
from app.ui.widgets.custom_title_bar import CustomTitleBar
from app.ui.widgets.shortcut_dialog import ShortcutManager, ShortcutDialog

# Services
from app.services.project_service import ProjectService
from app.services.review_service import ReviewService
from app.services.live_reload_manager import LiveReloadManager
from app.database.db_manager import DatabaseManager
from app.ffmpeg.ffmpeg_manager import FFmpegManager
from app.editing.editing_engine import EditingEngine
from app.workers.export_worker import ExportWorker
from app.workers.playblast_worker import PlayblastWorker

class MainWindow(QMainWindow, MediaMixin, ReviewMixin, ProjectMixin):
    def __init__(self):
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self.setWindowTitle("OpenDailies")
        
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            width = min(int(screen_geometry.width() * 0.85), 1600)
            height = min(int(screen_geometry.height() * 0.90), 1000)
            width = max(width, 1024)
            height = max(height, 600)
            self.resize(width, height)
            x = screen_geometry.center().x() - (width // 2)
            y = screen_geometry.center().y() - (height // 2)
            self.move(x, y)
        else:
            self.resize(1440, 900)
            
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        self.db_manager = DatabaseManager()
        self.ffmpeg_manager = FFmpegManager()
        self.project_service = ProjectService(self.db_manager)
        self.review_service = ReviewService(self.db_manager)
        self.editing_engine = EditingEngine(self.ffmpeg_manager)
        
        self.current_project = None
        self.current_video = None
        self.current_frame_rate = 24.0
        self._duration_frames = 0
        self.export_worker = None
        self.playblast_worker = None
        self._playblast_progress = None
        
        self._take_b_engine = None
        self._take_b_path = None
        self._is_synced = True
        self._active_bookmarks = []
        
        # NEW: Rolling cache for Before/After slider to prevent overwriting active streams
        self._before_cache_path = None
        self._before_cache_id = 0
        
        # Modular Live Reload Service
        self.live_reload_manager = LiveReloadManager(self)
        self.live_reload_manager.file_updated.connect(self._do_live_reload)
        
        self._shortcuts = ShortcutManager.load_shortcuts()
        
        self._init_ui()
        self._connect_signals()
        self._setup_shortcuts()

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int(1)))
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int(1)))
            except Exception: pass

    def _init_ui(self) -> None:
        self.central_widget = QWidget()
        self.central_widget.setStyleSheet("background-color: #171717;")
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(self)
        self.title_bar.close_requested.connect(self.close)
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.maximize_requested.connect(self._toggle_maximize)
        main_layout.addWidget(self.title_bar)
        
        self.menubar = QMenuBar(self)
        self.menubar.setStyleSheet("""
            QMenuBar { background-color: #171717; color: #A9A9A9; border-bottom: 1px solid #2D2E30; padding: 2px; }
            QMenuBar::item { background: transparent; padding: 6px 12px; border-radius: 6px; }
            QMenuBar::item:selected { background-color: #2D2E30; color: #FFFFFF; }
        """)
        main_layout.addWidget(self.menubar)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(8)
        main_layout.addWidget(content_widget)
        
        media_h_layout = QHBoxLayout()
        media_h_layout.setContentsMargins(0, 0, 0, 0)
        media_h_layout.setSpacing(8)
        
        self.annotation_toolbar = AnnotationToolBar(self)
        self.annotation_toolbar.setMovable(False)
        media_h_layout.addWidget(self.annotation_toolbar)
        
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(8)
        main_splitter.setStyleSheet("QSplitter::handle { background-color: transparent; }")
        
        self.video_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.video_splitter.setHandleWidth(8)
        self.video_splitter.setStyleSheet("QSplitter::handle { background-color: transparent; }")
        
        self.video_widget = VideoDisplayWidget()
        self.video_widget.video_dropped.connect(self._load_dropped_video)
        self.video_widget.open_requested.connect(lambda: self.open_video_file(None))
        
        self.annotation_overlay = AnnotationOverlay(self.video_widget)
        self.annotation_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.video_widget.set_overlay(self.annotation_overlay)
        self.annotation_overlay.show()
        
        self._take_b_display = VideoDisplayWidget()
        self._take_b_display.hide()
        
        self.video_splitter.addWidget(self.video_widget)
        self.video_splitter.addWidget(self._take_b_display)
        main_splitter.addWidget(self.video_splitter)
        
        right_panel = QFrame()
        right_panel.setObjectName("PanelCard")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tab_widget = QTabWidget()
        self.comment_panel = CommentPanel()
        self.bookmark_panel = BookmarkPanel()
        self.tab_widget.addTab(self.comment_panel, "Comments")
        self.tab_widget.addTab(self.bookmark_panel, "Bookmarks")
        right_layout.addWidget(self.tab_widget)
        
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([int(self.width() * 0.75), int(self.width() * 0.25)])
        
        media_h_layout.addWidget(main_splitter, 1)
        content_layout.addLayout(media_h_layout, 1)
        
        self.timeline_widget = TimelineWidget()
        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidgetResizable(False) 
        self.timeline_scroll.setWidget(self.timeline_widget)
        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.timeline_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.timeline_scroll.setFixedHeight(48)
        self.timeline_scroll.setStyleSheet("""
            QScrollBar:horizontal { background: transparent; height: 8px; margin: 0px; }
            QScrollBar::handle:horizontal { background: #3e3e3e; min-width: 40px; border-radius: 4px; }
            QScrollBar::handle:horizontal:hover { background: #4C8DFF; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { background: none; border: none; height: 0px; width: 0px; }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
        """)
        content_layout.addWidget(self.timeline_scroll)
        
        self.playback_engine = PlaybackEngine()
        
        self.playback_toolbar = PlaybackToolBar(self)
        self.playback_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.playback_toolbar)

        self.setStatusBar(QStatusBar())
        self._create_menus()

    def _load_dropped_video(self, file_path: str):
        if file_path:
            self.open_video_file(file_path)

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _create_menus(self) -> None:
        file_menu = self.menubar.addMenu("&File")
        new_proj_act = QAction("New Project", self); new_proj_act.triggered.connect(self._new_project); file_menu.addAction(new_proj_act)
        open_proj_act = QAction("Open Project...", self); open_proj_act.triggered.connect(self._open_project); file_menu.addAction(open_proj_act)
        save_proj_act = QAction("Save Project As...", self); save_proj_act.triggered.connect(self._save_project_as); file_menu.addAction(save_proj_act)
        file_menu.addSeparator()
        open_action = QAction("Open Video...", self); open_action.triggered.connect(self.open_video_file); file_menu.addAction(open_action)
        export_action = QAction("Export Trim...", self); export_action.triggered.connect(self.export_trimmed_video); file_menu.addAction(export_action)
        playblast_act = QAction("Export Playblast...", self); playblast_act.triggered.connect(self._export_playblast); file_menu.addAction(playblast_act)
        json_act = QAction("Export Review Data (JSON)...", self); json_act.triggered.connect(self._export_review_json); file_menu.addAction(json_act)
        srt_act = QAction("Export Subtitles (SRT)...", self); srt_act.triggered.connect(self._export_subtitles_srt); file_menu.addAction(srt_act)

        settings_menu = self.menubar.addMenu("&Settings")
        self.pressure_act = QAction("Pen Pressure", self, checkable=True)
        self.pressure_act.setChecked(True)
        self.pressure_act.triggered.connect(self._toggle_pressure)
        settings_menu.addAction(self.pressure_act)
        
        self.live_reload_act = QAction("Live Link (Maya Playblast)", self, checkable=True)
        self.live_reload_act.setChecked(True)
        self.live_reload_act.triggered.connect(self._toggle_live_reload)
        settings_menu.addAction(self.live_reload_act)

        self.before_after_act = QAction("Before/After Slider", self, checkable=True)
        self.before_after_act.setChecked(False)
        self.before_after_act.triggered.connect(self._toggle_before_after)
        settings_menu.addAction(self.before_after_act)

        settings_menu.addSeparator()
        import_brush_act = QAction("&Import Brush Preset...", self)
        import_brush_act.triggered.connect(self._import_brush_preset)
        settings_menu.addAction(import_brush_act)

        config_shortcuts_act = QAction("Configure &Shortcuts...", self)
        config_shortcuts_act.triggered.connect(self._open_shortcut_dialog)
        settings_menu.addAction(config_shortcuts_act)

        help_menu = self.menubar.addMenu("&Help")
        help_act = QAction("&Open Help File (HELP.txt)", self)
        help_act.triggered.connect(self._open_help_file)
        help_menu.addAction(help_act)

    def _open_help_file(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        help_path = os.path.join(base_dir, "assets", "HELP.txt")
        if os.path.exists(help_path):
            try:
                if sys.platform == "win32": os.startfile(help_path)
                elif sys.platform == "darwin": subprocess.Popen(["open", help_path])
                else: subprocess.Popen(["xdg-open", help_path])
            except Exception as e:
                QMessageBox.warning(self, "Help", f"Could not open help file: {e}")
        else:
            QMessageBox.warning(self, "Help", "HELP.txt not found in the assets folder.")

    def _import_brush_preset(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Custom Brush Preset", "", "OpenDailies Brush (*.odbrush);;JSON Files (*.json)")
        if file_path:
            self.annotation_overlay.load_custom_brush(file_path)
            self.statusBar().showMessage(f"Brush preset imported: {os.path.basename(file_path)}", 3000)

    def _toggle_pressure(self, checked: bool):
        self.annotation_overlay.set_pressure_enabled(checked)
        self.statusBar().showMessage(f"Pen Pressure: {'Enabled' if checked else 'Disabled'}", 2000)

    def _open_shortcut_dialog(self):
        dialog = ShortcutDialog(self._shortcuts, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_shortcuts = dialog.get_shortcuts()
            self._shortcuts = new_shortcuts
            ShortcutManager.save_shortcuts(new_shortcuts)
            self._apply_tool_shortcuts()
            QMessageBox.information(self, "Shortcuts Updated", "Annotation shortcuts have been successfully updated.")

    def _connect_signals(self) -> None:
        self.playback_toolbar.play_clicked.connect(self._toggle_play_pause)
        self.playback_toolbar.pause_clicked.connect(lambda: (self.playback_engine.pause(), self.playback_toolbar.update_play_state(False)))
        self.playback_toolbar.stop_clicked.connect(lambda: (self.playback_engine.stop(), self.playback_toolbar.update_play_state(False)))
        self.playback_toolbar.prev_frame_clicked.connect(self.playback_engine.step_frame_backward)
        self.playback_toolbar.next_frame_clicked.connect(self.playback_engine.step_frame_forward)
        self.playback_toolbar.loop_toggled.connect(self._toggle_loop)
        self.playback_toolbar.speed_changed.connect(self.playback_engine.set_playback_rate)
        self.playback_toolbar.fps_override_changed.connect(self._on_fps_override)
        self.playback_toolbar.compare_toggled.connect(self._toggle_compare)
        self.playback_toolbar.sync_toggled.connect(self._on_sync_toggled)
        self.playback_toolbar.annotations_toggled.connect(self._toggle_annotations)
        self.playback_toolbar.timecode_toggled.connect(self._toggle_timecode)
        self.playback_toolbar.subtitle_mode_changed.connect(self._on_subtitle_mode_changed)
        
        self.annotation_toolbar.tool_changed.connect(self.annotation_overlay.set_tool)
        self.annotation_toolbar.color_changed.connect(self.annotation_overlay.set_color)
        self.annotation_toolbar.size_changed.connect(self.annotation_overlay.set_brush_size)
        self.annotation_overlay.size_changed_live.connect(self.annotation_toolbar.set_brush_size)
        self.annotation_toolbar.undo_clicked.connect(self.annotation_overlay.undo)
        self.annotation_toolbar.clear_clicked.connect(self._on_clear_frame_requested)
        self.annotation_toolbar.onion_changed.connect(self._refresh_annotations)
        
        self.timeline_widget.position_changed.connect(self.playback_engine.set_position)
        def _on_engine_position(frame: int):
            self.timeline_widget.blockSignals(True)
            self.timeline_widget.set_position_frame(int(frame))
            self.timeline_widget.blockSignals(False)
        self.playback_engine.position_changed.connect(_on_engine_position)
        self.playback_engine.duration_changed.connect(self._on_total_frames_changed_ui)
        self.timeline_widget.scrub_started.connect(self._on_scrub_started)
        self.timeline_widget.scrub_finished.connect(self._on_scrub_finished)
        
        self.comment_panel.jump_to_frame_requested.connect(self._jump_to_frame)
        self.comment_panel.add_comment_requested.connect(self._on_add_comment_requested)
        self.comment_panel.edit_comment_requested.connect(self._on_edit_comment_requested)
        self.comment_panel.delete_comment_requested.connect(self._on_delete_comment_requested)
        self.playback_engine.position_changed.connect(self.comment_panel.highlight_comment_frame)
        
        self.bookmark_panel.jump_to_frame_requested.connect(self._jump_to_frame)
        self.bookmark_panel.add_bookmark_requested.connect(self._add_bookmark_at_playhead)
        self.bookmark_panel.rename_bookmark_requested.connect(self._on_rename_bookmark_requested)
        self.bookmark_panel.delete_bookmark_requested.connect(self._on_delete_bookmark_requested)

        self.playback_engine.position_changed.connect(self._on_frame_changed_ui)
        self.playback_engine.frame_ready.connect(self._on_engine_frame)
        
        self.annotation_overlay.annotation_added.connect(self._on_annotation_drawn)
        self.annotation_overlay.annotation_erased.connect(self._on_annotation_erased)
        self.playback_engine.position_changed.connect(lambda f: self._refresh_annotations())

    def _setup_shortcuts(self) -> None:
        seq_comma = self._shortcuts.get("Jump to Prev Annotation", ",")
        QShortcut(QKeySequence(seq_comma), self, activated=self._jump_to_prev_annotation_key)
        
        seq_period = self._shortcuts.get("Jump to Next Annotation", ".")
        QShortcut(QKeySequence(seq_period), self, activated=self._jump_to_next_annotation_key)
        
        self._apply_tool_shortcuts()

    def _apply_tool_shortcuts(self):
        anno_mapping = {
            "Pen": self.annotation_toolbar.tool_pen,
            "Pencil": self.annotation_toolbar.tool_pencil,
            "Rectangle": self.annotation_toolbar.tool_rect,
            "Arrow": self.annotation_toolbar.tool_arrow,
            "Circle": self.annotation_toolbar.tool_circle,
            "Text": self.annotation_toolbar.tool_text,
            "Eraser": self.annotation_toolbar.tool_eraser,
            "Undo": self.annotation_toolbar.undo_act,
            "Clear Frame": self.annotation_toolbar.clear_act
        }
        for name, action in anno_mapping.items():
            seq_str = self._shortcuts.get(name, "")
            if seq_str: action.setShortcut(QKeySequence(seq_str))
            else: action.setShortcut(QKeySequence())

        pb_mapping = {
            "Play/Pause": self.playback_toolbar.play_act,
            "Stop": self.playback_toolbar.stop_act,
            "Prev Frame": self.playback_toolbar.prev_act,
            "Next Frame": self.playback_toolbar.next_act,
            "Loop": self.playback_toolbar.loop_action,
            "Compare A/B": self.playback_toolbar.compare_action,
            "Toggle Annotations": self.playback_toolbar.anno_action,
            "Toggle Timecode Overlay": self.playback_toolbar.tc_action
        }
        for name, action in pb_mapping.items():
            seq_str = self._shortcuts.get(name, "")
            if seq_str: action.setShortcut(QKeySequence(seq_str))
            else: action.setShortcut(QKeySequence())

    def closeEvent(self, event):
        try:
            if self.playblast_worker and self.playblast_worker.isRunning(): self.playblast_worker.cancel(); self.playblast_worker.wait(2000)
            if self.export_worker and self.export_worker.isRunning(): self.export_worker.cancel(); self.export_worker.wait(2000)
            self.playback_engine.stop()
            if self._take_b_engine: self._take_b_engine.stop()
            dec = getattr(self.playback_engine, '_decoder', None)
            if dec: dec.stop_decoding(); dec.wait(2000)
            
            # NEW: Clean up rolling cache files from temp directory
            temp_dir = tempfile.gettempdir()
            cache_pattern = os.path.join(temp_dir, "od_cache_*.mp4")
            for old_cache in glob.glob(cache_pattern):
                try: os.remove(old_cache)
                except: pass
                
        except Exception: pass
        super().closeEvent(event)