"""
QThread Worker for non-blocking video exports.
"""
import sys
import subprocess
import re
from PySide6.QtCore import QThread, Signal
from app.ffmpeg.ffmpeg_manager import FFmpegManager

class ExportWorker(QThread):
    """Worker thread to execute FFmpeg exports without freezing the UI."""
    
    progress_updated = Signal(int)  # 0-100 percentage
    export_finished = Signal(bool, str)  # success, message
    error_occurred = Signal(str)

    def __init__(self, ffmpeg_manager: FFmpegManager, input_path: str, output_path: str, 
                 start_sec: float, duration_sec: float, lossless: bool):
        super().__init__()
        self.ffmpeg = ffmpeg_manager
        self.input_path = input_path
        self.output_path = output_path
        self.start_sec = start_sec
        self.duration_sec = duration_sec
        self.lossless = lossless
        self._is_cancelled = False
        self._process = None

    def run(self) -> None:
        """Executes the FFmpeg command and parses output for progress."""
        cmd = [
            self.ffmpeg.ffmpeg_path,
            "-y",
            "-ss", f"{self.start_sec:.3f}",
            "-i", self.input_path,
            "-t", f"{self.duration_sec:.3f}"
        ]
        
        if self.lossless:
            cmd.extend(["-c", "copy", "-avoid_negative_ts", "make_zero"])
        else:
            cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "aac"])
            
        cmd.append(self.output_path)

        try:
            # Windows-specific flag to hide the console window
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW
                
            # Use PIPE to capture stderr where FFmpeg outputs progress
            self._process = subprocess.Popen(
                cmd, 
                stderr=subprocess.PIPE, 
                stdout=subprocess.PIPE, 
                text=True, 
                encoding='utf-8', 
                errors='replace',
                creationflags=creation_flags
            )
            
            # Parse FFmpeg stderr for time= to calculate progress
            time_pattern = re.compile(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})")
            
            for line in self._process.stderr:
                if self._is_cancelled:
                    self._process.terminate()
                    self.export_finished.emit(False, "Export cancelled by user.")
                    return
                    
                match = time_pattern.search(line)
                if match:
                    time_str = match.group(1)
                    # Convert HH:MM:SS.xx to seconds
                    h, m, s = time_str.split(':')
                    current_sec = int(h) * 3600 + int(m) * 60 + float(s)
                    
                    if self.duration_sec > 0:
                        progress = int((current_sec / self.duration_sec) * 100)
                        self.progress_updated.emit(min(progress, 99))
                        
            self._process.wait()
            if self._process.returncode == 0:
                self.progress_updated.emit(100)
                self.export_finished.emit(True, f"Export complete: {self.output_path}")
            else:
                self.error_occurred.emit(f"FFmpeg exited with code {self._process.returncode}")
                
        except Exception as e:
            self.error_occurred.emit(str(e))

    def cancel(self) -> None:
        """Requests cancellation of the current export."""
        self._is_cancelled = True