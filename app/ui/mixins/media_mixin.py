"""
Media Controller Mixin for MainWindow.
Handles video loading, playback, A/B compare, and timeline UI updates.
"""
from typing import Optional
import logging
import os
import shutil
import tempfile
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation
from app.models.entities import Video
from app.playback.playback_engine import PlaybackEngine
from app.ui.widgets.before_after_overlay import BeforeAfterOverlay

class ToastNotification(QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(text)
        label.setStyleSheet("""
            background-color: rgba(76, 141, 255, 230); 
            color: #FFFFFF; 
            border-radius: 14px; 
            padding: 12px 24px;
            font-size: 14px;
            font-weight: bold;
            font-family: 'SF Pro Display', 'Segoe UI', sans-serif;
        """)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(300)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        
        self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out.setDuration(500)
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        self.fade_out.finished.connect(self.hide)
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._start_fade_out)
        
    def show_toast(self):
        self.adjustSize()
        if self.parent():
            p_rect = self.parent().rect()
            x = p_rect.center().x() - (self.width() // 2)
            y = p_rect.bottom() - self.height() - 60
            self.move(x, y)
        self.show()
        self.raise_()
        self.fade_in.start()
        self.timer.start(1500)
        
    def _start_fade_out(self):
        self.fade_out.start()


class MediaMixin:
    def _toggle_play_pause(self):
        if self.playback_engine.state == "playing":
            self.playback_engine.pause()
            self.playback_toolbar.update_play_state(False)
        else:
            self.playback_engine.play()
            self.playback_toolbar.update_play_state(True)

    def _toggle_live_reload(self, checked: bool):
        self.live_reload_manager.set_enabled(checked)
        if not checked:
            self.live_reload_manager.stop_watching()
        else:
            self._update_watched_files()
            self.statusBar().showMessage("Live Link Enabled", 2000)

    def _toggle_before_after(self, checked: bool):
        """Wrapper to hide the slider if the user turns the toggle off."""
        if not checked:
            self._disable_before_after()

    def _update_watched_files(self):
        paths = []
        if self.current_video:
            paths.append(self.current_video.file_path)
        if hasattr(self, '_take_b_path') and self._take_b_path:
            paths.append(self._take_b_path)
        if paths:
            self.live_reload_manager.watch_files(paths)
        else:
            self.live_reload_manager.stop_watching()

    def open_video_file(self, file_path: str = None) -> None:
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Video", "", "Video Files (*.mp4 *.mov *.avi *.mkv *.m4v *.webm *.wmv *.flv)")
            if not file_path: return
            
        try: self._reset_session()
        except Exception: self._logger.exception("Failed to reset previous session")
            
        metadata = self.ffmpeg_manager.probe_video(file_path)
        if not metadata:
            QMessageBox.warning(self, "Error", "Could not read video metadata."); return
            
        self.current_frame_rate = metadata["frame_rate"]
        self.playback_engine.load_video(file_path, self.current_frame_rate)
        self.setWindowTitle(f"OpenDailies - {file_path.split('/')[-1]}")
        
        conn = self.db_manager.get_connection()
        existing_vid = conn.execute("SELECT * FROM videos WHERE file_path = ?", (file_path,)).fetchone()
        
        if existing_vid:
            self.current_video = Video(id=existing_vid["id"], project_id=existing_vid["project_id"], file_path=existing_vid["file_path"], file_name=existing_vid["file_name"], duration_ms=existing_vid["duration_ms"], frame_rate=existing_vid["frame_rate"], width=existing_vid["width"], height=existing_vid["height"], codec=existing_vid["codec"], created_at=existing_vid["created_at"], updated_at=existing_vid["updated_at"])
        else:
            if not self.current_project: self.current_project = self.project_service.create_project("Adhoc Review", file_path)
            self.current_video = Video(project_id=self.current_project.id, file_path=file_path, file_name=file_path.split('/')[-1], duration_ms=metadata["duration_ms"], frame_rate=metadata["frame_rate"], width=metadata["width"], height=metadata["height"], codec=metadata["codec"])
            self.project_service.add_video_to_project(self.current_project, self.current_video)
        
        self.comment_panel.load_comments(self.review_service.get_comments_for_video(self.current_video.id), self.current_frame_rate)
        self.bookmark_panel.load_bookmarks(self.review_service.get_bookmarks_for_video(self.current_video.id))
        self._refresh_annotations()
        
        # NEW: Rolling cache for Before/After slider
        # Delete the old cache file if it exists
        if self._before_cache_path and os.path.exists(self._before_cache_path):
            try: os.remove(self._before_cache_path)
            except: pass
            
        self._before_cache_id += 1
        self._before_cache_path = os.path.join(tempfile.gettempdir(), f"od_cache_{self._before_cache_id}.mp4")
        try: shutil.copy2(file_path, self._before_cache_path)
        except Exception: pass
            
        self._update_watched_files()

    def _reset_session(self) -> None:
        try:
            self.playback_engine.stop()
            self.playback_toolbar.update_play_state(False)
            if self._take_b_engine: self._take_b_engine.stop(); self._take_b_engine = None
            self._take_b_display.hide()
            self.playback_toolbar.compare_action.setChecked(False)
            
            # Stop Before/After engine if active
            self._disable_before_after()
            
            self.comment_panel.load_comments([], self.current_frame_rate)
            self.bookmark_panel.load_bookmarks([])
            self.timeline_widget.set_duration_frames(0)
            self.timeline_widget.set_position_frame(0)
            self.timeline_widget.set_annotation_keys([])
            self.annotation_overlay.clear_annotations()
            self.video_widget.clear_frame()
            self.current_video = None
            self._take_b_path = None
            self.setWindowTitle("OpenDailies")
            self.live_reload_manager.stop_watching()
        except Exception: self._logger.exception("Failed during session reset")

    def _toggle_compare(self, checked: bool):
        if checked:
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Take B Video", "", "Video Files (*.mp4 *.mov *.avi *.mkv)")
            if not file_path:
                self.playback_toolbar.compare_action.setChecked(False)
                return
            self._take_b_display.show()
            self.video_splitter.setSizes([self.width() // 2, self.width() // 2])
            self._take_b_engine = PlaybackEngine()
            self._take_b_engine.frame_ready.connect(lambda idx, ts, img: self._take_b_display.update_frame(img))
            if self._is_synced:
                self.playback_engine.position_changed.connect(self._take_b_engine.set_position)
            metadata = self.ffmpeg_manager.probe_video(file_path)
            if metadata: self._take_b_engine.load_video(file_path, metadata["frame_rate"])
            self._take_b_path = file_path
            self._update_watched_files()
        else:
            self._take_b_display.hide()
            if self._take_b_engine:
                self._take_b_engine.stop()
                self._take_b_engine = None
            self._take_b_path = None
            self._update_watched_files()

    def _on_sync_toggled(self, checked: bool):
        self._is_synced = checked
        if self._take_b_engine:
            if checked:
                self.playback_engine.position_changed.connect(self._take_b_engine.set_position)
            else:
                try: self.playback_engine.position_changed.disconnect(self._take_b_engine.set_position)
                except Exception: pass

    def _on_fps_override(self, fps: float):
        if fps > 0 and self.current_video:
            self.current_frame_rate = fps
            self._duration_frames = int((self.current_video.duration_ms / 1000.0) * fps)
            self.playback_engine.duration_changed.emit(self._duration_frames)
            self.timeline_widget.set_duration_frames(self._duration_frames)

    def _toggle_timecode(self, checked: bool): self.video_widget.set_timecode_visible(checked)
    def _toggle_annotations(self, checked: bool):
        self.annotation_overlay.setVisible(checked)
        self.annotation_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, not checked)

    def _toggle_loop(self, checked: bool):
        self.playback_engine._loop_enabled = checked; self.playback_engine.loop_state_changed.emit(checked)

    def _on_frame_changed_ui(self, frame: int) -> None:
        try:
            self.playback_toolbar.set_media_info(int(frame), self._duration_frames, float(self.current_frame_rate))
            from app.playback.frame_utils import format_display_info
            mode = self.playback_toolbar._display_mode
            overlay_str = format_display_info(int(frame), self._duration_frames, float(self.current_frame_rate), mode)
            self.video_widget.set_timecode(overlay_str)
            sub_mode = self.playback_toolbar._subtitle_mode
            if sub_mode == 1 or sub_mode == 3:
                sub_duration = int(self.current_frame_rate * 2)
                active_bm = None
                for bm in self._active_bookmarks:
                    bm_frame = bm.frame_number
                    if bm_frame <= frame < bm_frame + sub_duration:
                        active_bm = bm
                        break
                if active_bm:
                    self.video_widget.set_subtitle(active_bm.name)
                    self.video_widget.set_subtitle_visible(True)
                else:
                    self.video_widget.set_subtitle_visible(False)
            else:
                self.video_widget.set_subtitle_visible(False)
        except Exception: pass

    def _on_subtitle_mode_changed(self, mode):
        self._on_frame_changed_ui(self.playback_engine.position())

    def _on_total_frames_changed_ui(self, total_frames: int) -> None:
        self._duration_frames = int(total_frames)
        self.timeline_widget.set_duration_frames(total_frames)
        timeline_width = self.timeline_scroll.viewport().width() - 20
        if timeline_width > 0 and total_frames > 0:
            self.timeline_widget.fit_to_width(timeline_width)

    def _on_engine_frame(self, frame_index, timestamp, img):
        try: self.video_widget.update_frame(img)
        except Exception: pass

    def _on_scrub_started(self): 
        self.playback_engine.pause()
        self.playback_toolbar.update_play_state(False)
        
    def _on_scrub_finished(self): 
        if getattr(self, '_was_playing_before_scrub', False):
            self.playback_engine.play()
            self.playback_toolbar.update_play_state(True)

    # --- Live Reload & Before/After Logic ---

    def _do_live_reload(self, file_path: str):
        is_take_a = self.current_video and file_path == self.current_video.file_path
        is_take_b = hasattr(self, '_take_b_path') and file_path == self._take_b_path
        
        if not is_take_a and not is_take_b: return
            
        try:
            new_metadata = self.ffmpeg_manager.probe_video(file_path)
            if not new_metadata: 
                self._toast = ToastNotification("⚠ File Locked by Maya", self.video_widget)
                self._toast.show_toast()
                return
            
            new_fps = new_metadata["frame_rate"]
            new_total_frames = int((new_metadata["duration_ms"] / 1000.0) * new_fps)
            
            # 1. UPDATE TAKE B
            if is_take_b and self._take_b_engine:
                old_frame = self._take_b_engine.position()
                self._take_b_engine.stop()
                self._take_b_engine.load_video(file_path, new_fps)
                self._take_b_engine.set_position(min(old_frame, new_total_frames))
                if self.playback_engine.state == "playing": self._take_b_engine.play()
                self._toast = ToastNotification("✔ Take B Playblast Updated", self.video_widget)
                self._toast.show_toast()
                
            # 2. UPDATE TAKE A (Main Video)
            elif is_take_a:
                old_frame = self.playback_engine.position()
                old_zoom = self.timeline_widget._px_per_frame
                old_in = self.timeline_widget._in_point_frame
                old_out = self.timeline_widget._out_point_frame
                was_playing = (self.playback_engine.state == "playing")
                
                self.playback_engine.stop()
                self.current_frame_rate = new_fps
                self.playback_engine.load_video(file_path, new_fps)
                
                self._duration_frames = new_total_frames
                self.timeline_widget.set_duration_frames(new_total_frames)
                restored_frame = min(old_frame, new_total_frames)
                self.playback_engine.set_position(restored_frame)
                self.timeline_widget.set_position_frame(restored_frame)
                self.timeline_widget._px_per_frame = old_zoom
                self.timeline_widget.set_in_point_frame(min(old_in, new_total_frames))
                self.timeline_widget.set_out_point_frame(min(old_out, new_total_frames))
                self.timeline_widget._update_min_width()
                self.timeline_widget.update()
                
                self._refresh_annotations()
                if was_playing: self.playback_engine.play()
                    
                # NEW: Setup Before/After Slider using the OLD cache file
                if self.before_after_act.isChecked() and self._before_cache_path and os.path.exists(self._before_cache_path):
                    # Pass the OLD cache path to the before engine
                    self._setup_before_after(restored_frame, self._before_cache_path)
                    
                    # Generate a NEW cache path for the new video so we don't overwrite the old one
                    self._before_cache_id += 1
                    self._before_cache_path = os.path.join(tempfile.gettempdir(), f"od_cache_{self._before_cache_id}.mp4")
                    try: shutil.copy2(file_path, self._before_cache_path)
                    except: pass
                    
                self._update_watched_files()
                self._toast = ToastNotification("✔ Video Playblast Updated", self.video_widget)
                self._toast.show_toast()
                
        except Exception as e:
            self._logger.exception("Failed to live reload video")
            self.statusBar().showMessage(f"Live Reload Failed: {e}", 3000)

    def _setup_before_after(self, start_frame: int, cache_path: str):
        """Spawns a hidden engine for the old video and shows the slider overlay."""
        if hasattr(self, '_before_engine') and self._before_engine:
            try: self.playback_engine.position_changed.disconnect(self._before_engine.set_position)
            except: pass
            self._before_engine.stop()
            
        self._before_engine = PlaybackEngine()
        self._before_engine.frame_ready.connect(self._on_before_frame)
        # Load the specific OLD cache file passed to this function
        self._before_engine.load_video(cache_path, self.current_frame_rate)
        
        if not hasattr(self, 'before_overlay') or not self.before_overlay:
            self.before_overlay = BeforeAfterOverlay(self.video_widget)
            self.before_overlay.closed.connect(self._disable_before_after)
            self.video_widget.before_overlay = self.before_overlay 
            
        if self.video_widget._last_pixmap:
            pix_w = self.video_widget._last_pixmap.width()
            pix_h = self.video_widget._last_pixmap.height()
            x = (self.video_widget.width() - pix_w) // 2
            y = (self.video_widget.height() - pix_h) // 2
            self.before_overlay.setGeometry(x, y, pix_w, pix_h)
            
        self.before_overlay.show()
        self.before_overlay.raise_()
        
        self.playback_engine.position_changed.connect(self._before_engine.set_position)
        self._before_engine.set_position(start_frame)
        
    def _on_before_frame(self, frame_index, timestamp, img):
        if self.before_overlay and self.before_overlay.isVisible():
            self.before_overlay.update_before_frame(img)
            
    def _disable_before_after(self):
        if hasattr(self, '_before_engine') and self._before_engine:
            try: self.playback_engine.position_changed.disconnect(self._before_engine.set_position)
            except: pass
            self._before_engine.stop()
            self._before_engine = None
            
        if hasattr(self, 'before_overlay') and self.before_overlay:
            self.before_overlay.hide()