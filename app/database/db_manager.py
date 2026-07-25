import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    _instance = None
    _connection = None
    _db_path = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_name="opendailies.db"):
        if self._connection is None:
            db_path = os.path.join(os.getcwd(), db_name)
            self._db_path = db_path
            logger.debug(f"Database location: {db_path}")
            self._connect(db_path)

    def _connect(self, db_path: str):
        self._connection = sqlite3.connect(db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL;")
        self._create_schema()
        self._apply_migrations()

    def reconnect(self, db_path: str) -> None:
        """Close current connection and open a new database file (Feature 6)."""
        if self._connection:
            self._connection.close()
        self._db_path = db_path
        self._connect(db_path)

    @property
    def db_path(self) -> str:
        return self._db_path

    def get_connection(self) -> sqlite3.Connection:
        return self._connection

    def _create_schema(self) -> None:
        cursor = self._connection.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY, name TEXT, file_path TEXT, 
                created_at TEXT, updated_at TEXT, last_opened_video_id TEXT
            );
            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY, project_id TEXT, file_path TEXT, file_name TEXT,
                duration_ms INTEGER, frame_rate REAL, width INTEGER, height INTEGER,
                codec TEXT, created_at TEXT, updated_at TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            CREATE TABLE IF NOT EXISTS comments (
                id TEXT PRIMARY KEY, video_id TEXT, frame_number INTEGER, timecode_ms INTEGER,
                author TEXT, text TEXT, color_tag TEXT, is_resolved INTEGER,
                parent_id TEXT, created_at TEXT, updated_at TEXT,
                FOREIGN KEY(video_id) REFERENCES videos(id)
            );
            CREATE TABLE IF NOT EXISTS annotations (
                id TEXT PRIMARY KEY, video_id TEXT, frame_number INTEGER, duration_frames INTEGER DEFAULT 1,
                author TEXT, data TEXT, color TEXT, created_at TEXT, updated_at TEXT,
                FOREIGN KEY(video_id) REFERENCES videos(id)
            );
            CREATE TABLE IF NOT EXISTS bookmarks (
                id TEXT PRIMARY KEY, video_id TEXT, frame_number INTEGER, name TEXT, color TEXT,
                created_at TEXT, updated_at TEXT,
                FOREIGN KEY(video_id) REFERENCES videos(id)
            );
            CREATE TABLE IF NOT EXISTS recent_files (
                id TEXT PRIMARY KEY, path TEXT, name TEXT, last_opened_at TEXT
            );
        """)
        self._connection.commit()

    def _apply_migrations(self) -> None:
        """Apply schema migrations safely (Feature 1)."""
        cursor = self._connection.cursor()
        cursor.execute("PRAGMA table_info(annotations)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'duration_frames' not in columns:
            cursor.execute("ALTER TABLE annotations ADD COLUMN duration_frames INTEGER DEFAULT 1")
            self._connection.commit()