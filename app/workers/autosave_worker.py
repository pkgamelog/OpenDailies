"""
QThread Worker for periodic autosaving.
"""
from PySide6.QtCore import QThread, Signal
from app.database.db_manager import DatabaseManager

class AutosaveWorker(QThread):
    """Periodically commits the database to disk."""
    
    autosave_complete = Signal()
    
    def __init__(self, db_manager: DatabaseManager, interval_min: int = 5):
        super().__init__()
        self.db_manager = db_manager
        self.interval_sec = interval_min * 60
        self._running = True

    def run(self) -> None:
        while self._running:
            self.msleep(self.interval_sec * 1000)
            if not self._running: break
            
            # SQLite with WAL mode handles concurrency well, but we ensure commit
            conn = self.db_manager.get_connection()
            conn.commit()
            self.autosave_complete.emit()

    def stop(self) -> None:
        """Stops the autosave loop gracefully."""
        self._running = False
