"""
Review Controller Mixin for MainWindow.
Handles annotations, comments, and bookmarks logic.
"""
import logging
from typing import Optional
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox, QMessageBox, QInputDialog
from app.models.entities import Comment, Annotation, Bookmark

class ReviewMixin:
    def _refresh_annotations(self, clear_history: bool = True):
        """Fetches current and onion skin annotations and updates the overlay."""
        if not self.current_video: return
        frame = self.playback_engine.position()
        
        cur = self.review_service.get_annotations_for_frame(self.current_video.id, frame)
        cur_dicts = [{"id": a.id, **a.data} for a in cur if a.data]
        
        before = self.annotation_toolbar.onion_before_spin.value()
        after = self.annotation_toolbar.onion_after_spin.value()
        max_opacity = self.annotation_toolbar.onion_opacity_slider.value() / 100.0
        
        onion_data = []
        for i in range(1, before + 1):
            f = frame - i
            if f >= 0:
                anns = self.review_service.get_annotations_for_frame(self.current_video.id, f)
                if anns: onion_data.append((-i, [{"id": a.id, **a.data} for a in anns if a.data]))
                    
        for i in range(1, after + 1):
            f = frame + i
            anns = self.review_service.get_annotations_for_frame(self.current_video.id, f)
            if anns: onion_data.append((i, [{"id": a.id, **a.data} for a in anns if a.data]))
        
        # FIX: Pass clear_history flag so undo stack isn't wiped after drawing
        self.annotation_overlay.load_annotations(cur_dicts, onion_data, max_opacity, clear_history=clear_history)
        self.timeline_widget.set_annotation_keys(self.review_service.get_annotation_keyframes(self.current_video.id))

    def _on_annotation_drawn(self, drawing_dict):
        if not self.current_video: return
        from app.models.entities import Annotation
        duration = 1
        ann = Annotation(video_id=self.current_video.id, frame_number=self.playback_engine.position(), duration_frames=duration, data=drawing_dict, color=drawing_dict.get("color", "#4C8DFF"))
        self.review_service.save_annotation(ann)
        
        self.timeline_widget.set_annotation_keys(self.review_service.get_annotation_keyframes(self.current_video.id))

    def _on_annotation_erased(self, drawing_dict):
        if not self.current_video: return
        ann_id = drawing_dict.get("id")
        if ann_id:
            self.review_service.delete_annotation(ann_id)
            self._refresh_annotations()

    def _on_clear_frame_requested(self):
        if not self.current_video: return
        frame = self.playback_engine.position()
        anns = self.review_service.get_annotations_for_frame(self.current_video.id, frame)
        for ann in anns:
            self.review_service.delete_annotation(ann.id)
        self._refresh_annotations()

    def _jump_to_prev_annotation_key(self):
        if not self.current_video: return
        keys = self.review_service.get_annotation_keyframes(self.current_video.id)
        frames = [k[0] for k in keys]
        prev_keys = [k for k in frames if k < self.playback_engine.position()]
        if prev_keys: self.playback_engine.set_position(prev_keys[-1])

    def _jump_to_next_annotation_key(self):
        if not self.current_video: return
        keys = self.review_service.get_annotation_keyframes(self.current_video.id)
        frames = [k[0] for k in keys]
        next_keys = [k for k in frames if k > self.playback_engine.position()]
        if next_keys: self.playback_engine.set_position(next_keys[0])

    def _jump_to_frame(self, frame_number: int): 
        self.playback_engine.set_position(int(frame_number))

    # --- Fully Implemented Comment Logic ---
    def _ask_multiline(self, title, label="", initial=""):
        dlg = QDialog(self); dlg.setWindowTitle(title); vbox = QVBoxLayout(dlg)
        txt = QTextEdit(dlg); txt.setPlainText(initial); vbox.addWidget(txt)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        vbox.addWidget(buttons); buttons.accepted.connect(dlg.accept); buttons.rejected.connect(dlg.reject)
        dlg.setStyleSheet("""
            QDialog { background-color: #171717; border-radius: 12px; }
            QTextEdit { background-color: #252526; color: #FFFFFF; border: 1px solid #2D2E30; border-radius: 8px; padding: 8px; font-size: 14px; }
            QPushButton { background-color: #252526; color: #FFFFFF; border: 1px solid #2D2E30; border-radius: 6px; padding: 8px 16px; min-width: 80px; }
            QPushButton:hover { background-color: #2D2E30; border: 1px solid #4C8DFF; }
            QPushButton:default { background-color: #4C8DFF; color: #FFFFFF; border: none; }
        """)
        if dlg.exec() == QDialog.DialogCode.Accepted: return True, txt.toPlainText()
        return False, initial

    def _on_add_comment_requested(self):
        if not self.current_video: return
        ok, text = self._ask_multiline("Add Comment", "Comment:")
        if not ok or not text.strip(): return
        c = Comment(video_id=self.current_video.id, frame_number=int(self.playback_engine.position()), text=text)
        self.review_service.save_comment(c)
        self.comment_panel.load_comments(self.review_service.get_comments_for_video(self.current_video.id), self.current_frame_rate)

    def _on_edit_comment_requested(self, comment_id: str):
        if not comment_id: return
        c = self.review_service.get_comment_by_id(comment_id)
        if not c: return
        ok, text = self._ask_multiline("Edit Comment", "Comment:", initial=c.text)
        if not ok: return
        c.text = text
        self.review_service.save_comment(c)
        self.comment_panel.load_comments(self.review_service.get_comments_for_video(self.current_video.id), self.current_frame_rate)

    def _on_delete_comment_requested(self, comment_id: str):
        if not comment_id: return
        reply = QMessageBox.question(self, "Delete Comment", "Delete this comment?")
        if reply != QMessageBox.StandardButton.Yes: return
        self.review_service.delete_comment(comment_id)
        self.comment_panel.load_comments(self.review_service.get_comments_for_video(self.current_video.id), self.current_frame_rate)

    # --- Fully Implemented Bookmark Logic ---
    def _refresh_bookmarks(self):
        if not self.current_video: return
        bookmarks = self.review_service.get_bookmarks_for_video(self.current_video.id)
        self._active_bookmarks = bookmarks # Cache for fast subtitle lookup
        self.bookmark_panel.load_bookmarks(bookmarks)
        self.timeline_widget.load_markers(bookmarks)

    def _add_bookmark_at_playhead(self):
        if not self.current_video: return
        bm = Bookmark(video_id=self.current_video.id, frame_number=int(self.playback_engine.position()), name="Bookmark")
        self.review_service.save_bookmark(bm)
        self._refresh_bookmarks()

    def _on_rename_bookmark_requested(self, bookmark_id: str, new_name: str):
        try:
            bm = self.review_service.get_bookmark_by_id(bookmark_id)
            if not bm: return
            dlg = QInputDialog(self)
            dlg.setWindowTitle("Rename Bookmark")
            dlg.setLabelText("New Name:")
            dlg.setTextValue(bm.name)
            dlg.setStyleSheet("""
                QInputDialog { background-color: #171717; }
                QLabel { color: #FFFFFF; }
                QLineEdit { background-color: #252526; color: #FFFFFF; border: 1px solid #2D2E30; border-radius: 6px; padding: 6px; }
                QPushButton { background-color: #252526; color: #FFFFFF; border: 1px solid #2D2E30; border-radius: 6px; padding: 8px 16px; min-width: 80px; }
                QPushButton:hover { background-color: #2D2E30; border: 1px solid #4C8DFF; }
            """)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                bm.name = dlg.textValue()
                self.review_service.save_bookmark(bm)
                self._refresh_bookmarks()
        except Exception as e: self._logger.exception("Failed to rename bookmark")

    def _on_delete_bookmark_requested(self, bookmark_id: str):
        try: 
            self.review_service.delete_bookmark(bookmark_id)
            self._refresh_bookmarks()
        except Exception as e: self._logger.exception("Failed to delete bookmark")