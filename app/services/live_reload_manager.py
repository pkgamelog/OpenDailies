from PySide6.QtCore import QObject, QFileSystemWatcher, QTimer, Signal
import os

class LiveReloadManager(QObject):
    """Monitors video files and emits a signal when one is overwritten, 
       with a debounce timer to ensure the file is fully written."""
    
    file_updated = Signal(str)  # Emits the file path that changed

    def __init__(self, parent=None):
        super().__init__(parent)
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)
        
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(1000) # Wait 1s for Maya to finish writing
        self._debounce_timer.timeout.connect(self._emit_update)
        
        self._current_files = []
        self._is_enabled = True

    def set_enabled(self, enabled: bool):
        self._is_enabled = enabled
        if not enabled:
            self.stop_watching()

    def watch_files(self, file_paths: list):
        """Start watching a list of files (Take A and Take B)."""
        self.stop_watching()
        if self._is_enabled:
            self._current_files = [p for p in file_paths if p and os.path.exists(p)]
            if self._current_files:
                self._watcher.addPaths(self._current_files)

    def stop_watching(self):
        """Stop watching all files."""
        if self._watcher.files():
            self._watcher.removePaths(self._watcher.files())
        self._debounce_timer.stop()
        self._changed_file = None

    def _on_file_changed(self, path: str):
        """Triggered instantly when OS detects a change. Starts the debounce timer."""
        # QFileSystemWatcher drops paths after they are overwritten. Re-add it.
        if path not in self._watcher.files():
            if os.path.exists(path):
                self._watcher.addPath(path)
        
        # Remember which file actually changed so we can emit it correctly
        self._changed_file = path
        
        # Restart the timer. If multiple saves happen rapidly, it only fires once at the end.
        self._debounce_timer.start()

    def _emit_update(self):
        """Emits the signal only after the timer fires (file is safely written)."""
        if hasattr(self, '_changed_file') and self._changed_file:
            self.file_updated.emit(self._changed_file)
            self._changed_file = None