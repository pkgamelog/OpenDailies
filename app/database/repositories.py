from typing import List, Optional
import sqlite3
import json

from app.models.entities import Project, Video, Comment, Annotation, Bookmark, RecentFile

class ProjectRepository:
    def __init__(self, db_manager):
        self._db = db_manager

    def save(self, project: Project) -> None:
        conn: sqlite3.Connection = self._db.get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO projects (id, name, file_path, created_at, updated_at, last_opened_video_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (project.id, project.name, project.file_path, project.created_at, project.updated_at, project.last_opened_video_id),
        )
        conn.commit()

    def get_by_id(self, project_id: str) -> Optional[Project]:
        conn: sqlite3.Connection = self._db.get_connection()
        cur = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cur.fetchone()
        if not row: return None
        return Project(
            id=row["id"], name=row["name"], file_path=row["file_path"],
            created_at=row["created_at"], updated_at=row["updated_at"],
            last_opened_video_id=row["last_opened_video_id"]
        )

class VideoRepository:
    def __init__(self, db_manager):
        self._db = db_manager

    def save(self, video: Video) -> None:
        conn: sqlite3.Connection = self._db.get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO videos (id, project_id, file_path, file_name, duration_ms, frame_rate, width, height, codec, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (video.id, video.project_id, video.file_path, video.file_name, video.duration_ms,
             video.frame_rate, video.width, video.height, video.codec, video.created_at, video.updated_at),
        )
        conn.commit()

    def get_by_project(self, project_id: str) -> List[Video]:
        conn: sqlite3.Connection = self._db.get_connection()
        cur = conn.execute("SELECT * FROM videos WHERE project_id = ?", (project_id,))
        rows = cur.fetchall()
        return [
            Video(
                id=row["id"], project_id=row["project_id"], file_path=row["file_path"],
                file_name=row["file_name"], duration_ms=row["duration_ms"] or 0,
                frame_rate=row["frame_rate"] or 0.0, width=row["width"] or 0,
                height=row["height"] or 0, codec=row["codec"] or "",
                created_at=row["created_at"], updated_at=row["updated_at"]
            ) for row in rows
        ]

class CommentRepository:
    def __init__(self, db_manager):
        self._db = db_manager

    def save(self, comment: Comment) -> None:
        conn: sqlite3.Connection = self._db.get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO comments (id, video_id, frame_number, timecode_ms, author, text, color_tag, is_resolved, parent_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (comment.id, comment.video_id, comment.frame_number, comment.timecode_ms,
             comment.author, comment.text, comment.color_tag, 1 if comment.is_resolved else 0,
             comment.parent_id, comment.created_at, comment.updated_at),
        )
        conn.commit()

    def get_by_video(self, video_id: str) -> List[Comment]:
        conn: sqlite3.Connection = self._db.get_connection()
        cur = conn.execute("SELECT * FROM comments WHERE video_id = ?", (video_id,))
        rows = cur.fetchall()
        return [
            Comment(
                id=row["id"], video_id=row["video_id"], frame_number=row["frame_number"] or 0,
                timecode_ms=row["timecode_ms"] or 0, author=row["author"] or "",
                text=row["text"] or "", color_tag=row["color_tag"] or "#FFFFFF",
                is_resolved=bool(row["is_resolved"]), parent_id=row["parent_id"],
                created_at=row["created_at"], updated_at=row["updated_at"]
            ) for row in rows
        ]
    
    def get_by_id(self, comment_id: str) -> Optional[Comment]:
        conn: sqlite3.Connection = self._db.get_connection()
        cur = conn.execute("SELECT * FROM comments WHERE id = ?", (comment_id,))
        row = cur.fetchone()
        if not row: return None
        return Comment(
            id=row["id"], video_id=row["video_id"], frame_number=row["frame_number"] or 0,
            timecode_ms=row["timecode_ms"] or 0, author=row["author"] or "",
            text=row["text"] or "", color_tag=row["color_tag"] or "#FFFFFF",
            is_resolved=bool(row["is_resolved"]), parent_id=row["parent_id"],
            created_at=row["created_at"], updated_at=row["updated_at"]
        )

    def delete_by_id(self, comment_id: str) -> None:
        conn: sqlite3.Connection = self._db.get_connection()
        conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        conn.commit()

class AnnotationRepository:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def save(self, annotation: 'Annotation') -> None:
        import json
        conn = self.db_manager.get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO annotations (id, video_id, frame_number, duration_frames, author, data, color, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                annotation.id, annotation.video_id, annotation.frame_number, 
                getattr(annotation, 'duration_frames', 1),
                getattr(annotation, 'author', ''), json.dumps(getattr(annotation, 'data', {})),
                getattr(annotation, 'color', '#FF0000'), annotation.created_at, annotation.updated_at,
            ),
        )
        conn.commit()

    def _row_to_annotation(self, row) -> 'Annotation':
        from app.models.entities import Annotation
        data = {}
        try:
            data = json.loads(row["data"]) if row["data"] else {}
        except Exception:
            pass
        return Annotation(
            id=row["id"], video_id=row["video_id"], frame_number=row["frame_number"] or 0,
            duration_frames=row["duration_frames"] or 1, author=row["author"] or "",
            data=data, color=row["color"] or "#FF0000", created_at=row["created_at"], updated_at=row["updated_at"]
        )

    def get_by_video_and_frame(self, video_id: str, frame_number: int) -> List['Annotation']:
        """Fetch annotations visible at a given frame (supports duration ranges - Feature 1)."""
        conn = self.db_manager.get_connection()
        rows = conn.execute(
            "SELECT * FROM annotations WHERE video_id = ? AND frame_number <= ? AND (frame_number + duration_frames) > ?",
            (video_id, frame_number, frame_number)
        ).fetchall()
        return [self._row_to_annotation(row) for row in rows]

    def get_all_by_video(self, video_id: str) -> List['Annotation']:
        """Fetch ALL annotations for a video (used for Playblast and JSON export)."""
        conn = self.db_manager.get_connection()
        rows = conn.execute("SELECT * FROM annotations WHERE video_id = ? ORDER BY frame_number", (video_id,)).fetchall()
        return [self._row_to_annotation(row) for row in rows]

    def get_annotation_frames(self, video_id: str) -> List[tuple]:
        """Returns a sorted list of (frame_number, duration_frames) tuples."""
        conn = self.db_manager.get_connection()
        rows = conn.execute("SELECT DISTINCT frame_number, duration_frames FROM annotations WHERE video_id = ?", (video_id,)).fetchall()
        return sorted([(row["frame_number"], row["duration_frames"] or 1) for row in rows])

    def delete_by_id(self, annotation_id: str) -> None:
        conn = self.db_manager.get_connection()
        conn.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
        conn.commit()

class BookmarkRepository:
    def __init__(self, db_manager):
        self._db = db_manager

    def save(self, bookmark: Bookmark) -> None:
        conn: sqlite3.Connection = self._db.get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO bookmarks (id, video_id, frame_number, name, color, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (bookmark.id, bookmark.video_id, bookmark.frame_number, bookmark.name, bookmark.color, bookmark.created_at, bookmark.updated_at),
        )
        conn.commit()

    def get_by_video(self, video_id: str) -> List[Bookmark]:
        conn: sqlite3.Connection = self._db.get_connection()
        cur = conn.execute("SELECT * FROM bookmarks WHERE video_id = ?", (video_id,))
        rows = cur.fetchall()
        return [
            Bookmark(
                id=row["id"], video_id=row["video_id"], frame_number=row["frame_number"] or 0,
                name=row["name"] or "", color=row["color"] or "#00FF00",
                created_at=row["created_at"], updated_at=row["updated_at"]
            ) for row in rows
        ]

    def get_by_id(self, bookmark_id: str) -> Optional[Bookmark]:
        conn: sqlite3.Connection = self._db.get_connection()
        cur = conn.execute("SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,))
        row = cur.fetchone()
        if not row: return None
        return Bookmark(
            id=row["id"], video_id=row["video_id"], frame_number=row["frame_number"] or 0,
            name=row["name"] or "", color=row["color"] or "#00FF00",
            created_at=row["created_at"], updated_at=row["updated_at"]
        )

    def delete_by_id(self, bookmark_id: str) -> None:
        conn: sqlite3.Connection = self._db.get_connection()
        conn.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
        conn.commit()

class RecentFileRepository:
    def __init__(self, db_manager):
        self._db = db_manager

    def save(self, recent: RecentFile) -> None:
        conn: sqlite3.Connection = self._db.get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO recent_files (id, path, name, last_opened_at)
            VALUES (?, ?, ?, ?)
            """,
            (recent.id, recent.path, recent.name, recent.last_opened_at),
        )
        conn.commit()

    def get_recent(self, limit: int = 20) -> List[RecentFile]:
        conn: sqlite3.Connection = self._db.get_connection()
        cur = conn.execute("SELECT * FROM recent_files ORDER BY last_opened_at DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        return [
            RecentFile(
                id=row["id"], path=row["path"], name=row["name"], last_opened_at=row["last_opened_at"]
            ) for row in rows
        ]