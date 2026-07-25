"""
QThread Worker for generating video thumbnails.
"""
import subprocess
import os
from PySide6.QtCore import QThread, Signal, QByteArray
from PySide6.QtGui import QPixmap

class ThumbnailWorker(QThread):
    """Extracts a single frame from a video to use as a thumbnail."""
    
    thumbnail_ready = Signal(str, QPixmap)  # file_path, pixmap
    error_occurred = Signal(str)

    def __init__(self, ffmpeg_path: str, video_path: str):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.video_path = video_path

    def run(self) -> None:
        temp_thumb = os.path.join(os.path.dirname(self.video_path), f".thumb_{os.path.basename(self.video_path)}.png")
        
        cmd = [
            self.ffmpeg_path,
            "-ss", "00:00:01", # Grab frame at 1 second
            "-i", self.video_path,
            "-frames:v", "1",
            "-vf", "scale=320:-1", # 320px wide
            "-y",
            temp_thumb
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if os.path.exists(temp_thumb):
                pixmap = QPixmap(temp_thumb)
                self.thumbnail_ready.emit(self.video_path, pixmap)
                os.remove(temp_thumb) # Cleanup
        except Exception as e:
            self.error_occurred.emit(str(e))
