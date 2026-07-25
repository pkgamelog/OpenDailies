"""
Project Controller Mixin for MainWindow.
Handles project save/load, JSON export, SRT export, and video trimming/exporting.
"""
import os
import shutil
import logging
from typing import Optional
from PySide6.QtWidgets import QFileDialog, QMessageBox, QProgressBar
from app.workers.export_worker import ExportWorker
from app.workers.playblast_worker import PlayblastWorker
from app.playback.frame_utils import frame_to_srt_time

class ProjectMixin:
    def _new_project(self):
        self._reset_session()
        self.db_manager.reconnect(os.path.join(os.getcwd(), "opendailies.db"))
        self.setWindowTitle("OpenDailies - New Project")

    def _open_project(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "OpenDailies Project (*.odp)")
        if not file_path: return
        self._reset_session()
        self.db_manager.reconnect(file_path)
        conn = self.db_manager.get_connection()
        proj_row = conn.execute("SELECT * FROM projects LIMIT 1").fetchone()
        if proj_row:
            from app.models.entities import Project
            self.current_project = Project(id=proj_row["id"], name=proj_row["name"], file_path=proj_row["file_path"])
        else:
            self.current_project = self.project_service.create_project("Adhoc Review", "")
        QMessageBox.information(self, "Project Loaded", "Project loaded. Please select the video file associated with it to view annotations.")
        self.open_video_file()

    def _save_project_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Project As", "", "OpenDailies Project (*.odp)")
        if not file_path: return
        conn = self.db_manager.get_connection()
        conn.commit()
        shutil.copy2(self.db_manager.db_path, file_path)
        self.statusBar().showMessage(f"Project saved to: {file_path}", 5000)

    def _export_playblast(self):
        if not self.current_video: return
        output_path, _ = QFileDialog.getSaveFileName(self, "Export Playblast", "", "MP4 Video (*.mp4)")
        if not output_path: return
        
        # FIX: Get trim points from timeline
        in_frame = getattr(self.timeline_widget, '_in_point_frame', 0)
        out_frame = getattr(self.timeline_widget, '_out_point_frame', self._duration_frames - 1)
        if out_frame <= in_frame:
            in_frame = 0
            out_frame = max(0, self._duration_frames - 1)
        
        annotations = self.review_service.get_all_annotations_for_video(self.current_video.id)
        ann_dicts = [{"frame_number": a.frame_number, "duration_frames": getattr(a, 'duration_frames', 1), "data": a.data, "color": a.color} for a in annotations]
        
        bookmarks = self.review_service.get_bookmarks_for_video(self.current_video.id)
        bm_dicts = [{"frame_number": b.frame_number, "name": b.name} for b in bookmarks]
        
        # Filter bookmarks to only include those within the trim range (for SRT export)
        trimmed_bookmarks = [bm for bm in bookmarks if in_frame <= bm.frame_number <= out_frame]
        
        display_mode = getattr(self.playback_toolbar, '_display_mode', 2)
        sub_mode = getattr(self.playback_toolbar, '_subtitle_mode', 0)
        
        self.playblast_worker = PlayblastWorker(
            self.ffmpeg_manager.ffmpeg_path, 
            self.current_video.file_path, 
            output_path, 
            self.current_video.width, 
            self.current_video.height, 
            self.current_frame_rate, 
            self._duration_frames, 
            in_frame,  # Pass start_frame
            out_frame, # Pass end_frame
            ann_dicts,
            bm_dicts,
            display_mode=display_mode,
            subtitle_mode=sub_mode
        )
        self._playblast_progress = QProgressBar()
        self.statusBar().addPermanentWidget(self._playblast_progress)
        self.playblast_worker.progress_updated.connect(self._playblast_progress.setValue)
        self.playblast_worker.export_finished.connect(self._on_playblast_finished)
        self.playblast_worker.start()
        
        # FIX: Auto-generate SRT file if mode is 2 (SRT) or 3 (Both)
        if sub_mode == 2 or sub_mode == 3:
            srt_path = output_path.rsplit('.', 1)[0] + '.srt'
            self._generate_srt_file(srt_path, trimmed_bookmarks)

    def _on_playblast_finished(self, success: bool, message: str):
        if hasattr(self, '_playblast_progress') and self._playblast_progress:
            self.statusBar().removeWidget(self._playblast_progress)
            self._playblast_progress = None
        if success: QMessageBox.information(self, "Playblast", message)

    def _export_review_json(self):
        if not self.current_video: return
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Review Data", "", "JSON Files (*.json)")
        if not file_path: return
        self.review_service.export_review_data(self.current_video.id, file_path)
        self.statusBar().showMessage(f"Review data exported to {file_path}", 5000)

    def _export_subtitles_srt(self):
        if not self.current_video: return
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Subtitles (SRT)", "", "SubRip Subtitle (*.srt)")
        if not file_path: return
        bookmarks = self.review_service.get_bookmarks_for_video(self.current_video.id)
        self._generate_srt_file(file_path, bookmarks)
        self.statusBar().showMessage(f"Subtitles exported to {file_path}", 5000)

    def _generate_srt_file(self, file_path: str, bookmarks: list):
        bookmarks.sort(key=lambda x: x.frame_number)
        fps = self.current_frame_rate
        srt_lines = []
        for i, bm in enumerate(bookmarks):
            start_frame = bm.frame_number
            end_frame = bookmarks[i+1].frame_number if i+1 < len(bookmarks) else start_frame + int(fps * 2)
            start_time = frame_to_srt_time(start_frame, fps)
            end_time = frame_to_srt_time(end_frame, fps)
            name = bm.name if bm.name.strip() else "Bookmark"
            srt_lines.append(str(i+1))
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(name)
            srt_lines.append("")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(srt_lines))

    def export_trimmed_video(self) -> None:
        if not self.current_video: return
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Trimmed Video", "", "Video Files (*.mp4)")
        if not save_path: return
        in_frame = getattr(self.timeline_widget, '_in_point_frame', None)
        out_frame = getattr(self.timeline_widget, '_out_point_frame', None)
        if in_frame is None or out_frame is None or out_frame <= in_frame: return
        start_sec = (in_frame / float(self.current_frame_rate)); duration_sec = ((out_frame - in_frame) / float(self.current_frame_rate))
        self.export_worker = ExportWorker(self.ffmpeg_manager, self.current_video.file_path, save_path, start_sec, duration_sec, lossless=True)
        self.export_worker.progress_updated.connect(lambda p: self.statusBar().showMessage(f"Exporting: {p}%"))
        self.export_worker.export_finished.connect(self._on_export_finished)
        self.export_worker.start()

    def _on_export_finished(self, success, message): pass