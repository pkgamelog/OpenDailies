from app.database.db_manager import DatabaseManager
from app.database.repositories import CommentRepository, BookmarkRepository, RecentFileRepository, AnnotationRepository
from app.models.entities import Comment, Bookmark, RecentFile, Annotation
from typing import List, Optional
import json
from datetime import datetime

class ReviewService:
    def __init__(self, db_manager: DatabaseManager):
        self.comment_repo = CommentRepository(db_manager)
        self.bookmark_repo = BookmarkRepository(db_manager)
        self.recent_repo = RecentFileRepository(db_manager)
        self.annotation_repo = AnnotationRepository(db_manager)

    # --- Comments ---
    def get_comments_for_video(self, video_id: str) -> List[Comment]:
        return self.comment_repo.get_by_video(video_id)
    def save_comment(self, comment: Comment) -> None:
        self.comment_repo.save(comment)
    def get_comment_by_id(self, comment_id: str) -> Optional[Comment]:
        return self.comment_repo.get_by_id(comment_id)
    def delete_comment(self, comment_id: str) -> None:
        self.comment_repo.delete_by_id(comment_id)

    # --- Bookmarks ---
    def get_bookmarks_for_video(self, video_id: str) -> List[Bookmark]:
        return self.bookmark_repo.get_by_video(video_id)
    def save_bookmark(self, bookmark: Bookmark) -> None:
        self.bookmark_repo.save(bookmark)
    def get_bookmark_by_id(self, bookmark_id: str) -> Optional[Bookmark]:
        return self.bookmark_repo.get_by_id(bookmark_id)
    def delete_bookmark(self, bookmark_id: str) -> None:
        self.bookmark_repo.delete_by_id(bookmark_id)

    # --- Annotations ---
    def save_annotation(self, annotation: Annotation) -> None:
        self.annotation_repo.save(annotation)
    def get_annotations_for_frame(self, video_id: str, frame_number: int) -> List[Annotation]:
        return self.annotation_repo.get_by_video_and_frame(video_id, frame_number)
    def get_annotation_keyframes(self, video_id: str) -> List[tuple]:
        return self.annotation_repo.get_annotation_frames(video_id)
    def get_all_annotations_for_video(self, video_id: str) -> List[Annotation]:
        return self.annotation_repo.get_all_by_video(video_id)
    def delete_annotation(self, annotation_id: str) -> None:
        self.annotation_repo.delete_by_id(annotation_id)

    # --- JSON Export (Feature 3) ---
    def export_review_data(self, video_id: str, file_path: str) -> None:
        """Export all review data to a structured JSON file."""
        comments = self.get_comments_for_video(video_id)
        bookmarks = self.get_bookmarks_for_video(video_id)
        annotations = self.get_all_annotations_for_video(video_id)

        data = {
            "version": "1.0",
            "video_id": video_id,
            "exported_at": datetime.now().isoformat(),
            "comments": [{"id": c.id, "frame_number": c.frame_number, "text": c.text, "author": c.author} for c in comments],
            "bookmarks": [{"id": b.id, "frame_number": b.frame_number, "name": b.name, "color": b.color} for b in bookmarks],
            "annotations": [
                {
                    "id": a.id, "frame_number": a.frame_number, "duration_frames": getattr(a, 'duration_frames', 1),
                    "color": a.color, "data": a.data
                } for a in annotations
            ]
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)