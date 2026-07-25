from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

logger = logging.getLogger(__name__)

@dataclass
class DecodedFrameInfo:
    timestamp_seconds: float
    frame_index: int

class FFmpegNotFound(Exception):
    """ffmpeg executable not located."""

class FFmpegDecodingError(Exception):
    """General ffmpeg decoding error."""

class FFmpegDecoderThread(QThread):
    frame_ready = Signal(int, float, QImage, int)
    finished = Signal()
    error = Signal(str)

    def __init__(
        self,
        video_path: str,
        width: int,
        height: int,
        fps: float,
        start_time: Optional[float] = None,
        ffmpeg_path: Optional[str] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.video_path = str(video_path)
        self.width = int(width) if width > 0 else 640
        self.height = int(height) if height > 0 else 480
        self.fps = float(fps) if fps > 0 else 24.0  # FIX: Prevent 0 FPS crash
        self.start_time = float(start_time) if start_time is not None else 0.0

        self._ffmpeg_exe = ffmpeg_path or self._locate_ffmpeg()

        self._is_playing: bool = False
        self._step_request_count: int = 0
        self._stop_requested: bool = False
        self._seek_request: Optional[dict] = None
        
        self._proc: Optional[subprocess.Popen] = None
        self._frame_bytes = self.width * self.height * 3
        
        self._playback_rate = 1.0
        self._pause_event = threading.Event()
        self._pause_event.set()
        
        self._seek_generation = 0
        self._current_gen = 0

    def start_decoding(self) -> None:
        if not self.isRunning():
            self._stop_requested = False
            self._pause_event.set()
            self.start()

    def pause_decoding(self) -> None:
        self._is_playing = False
        self._step_request_count = 0
        if self._seek_request:
            self._seek_request['play'] = False
        self._pause_event.set()  # FIX: Set event to wake up thread so it can enter paused state

    def resume_decoding(self) -> None:
        if self._seek_request:
            self._seek_request['play'] = True
        else:
            self._is_playing = True
            self._step_request_count = 0
            self._pause_event.set()

    def request_single_frame(self) -> None:
        self._is_playing = False
        self._step_request_count += 1
        self._pause_event.set()
        if self._seek_request:
            self._seek_request['play'] = False

    def stop_decoding(self) -> None:
        self._stop_requested = True
        self._is_playing = False
        self._step_request_count = 0
        self._seek_request = None
        self._pause_event.set()
        self._terminate_proc()

    def shutdown(self, wait_ms: int = 5000) -> None:
        self.stop_decoding()
        self.requestInterruption()
        self.quit()
        self.wait(wait_ms)
        if self.isRunning():
            self._terminate_proc()
            self.wait(2000)

    def seek(self, seconds: float, play_after_seek: bool = False) -> int:
        self._seek_generation += 1
        self._seek_request = {
            'sec': float(seconds), 
            'play': bool(play_after_seek),
            'gen': self._seek_generation
        }
        self._pause_event.set()
        self._interrupt_proc()
        return self._seek_generation

    def set_playback_rate(self, rate: float) -> None:
        self._playback_rate = float(rate) if rate > 0 else 1.0  # FIX: Prevent 0.0 rate crash

    def is_seek_pending(self) -> bool:
        return self._seek_request is not None

    def _locate_ffmpeg(self) -> str:
        project_root = Path(__file__).resolve().parents[2]
        cand = project_root / "ffmpeg.exe"
        if cand.exists():
            return str(cand)
        which_name = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
        if which_name:
            return which_name
        raise FFmpegNotFound("ffmpeg executable not found in project root or PATH")

    def _build_command(self, start_sec: Optional[float] = None) -> list:
        cmd = [self._ffmpeg_exe]
        if start_sec is not None:
            cmd += ["-ss", str(start_sec)]
        cmd += ["-i", self.video_path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        return cmd

    def _start_proc(self, start_sec: Optional[float] = None) -> None:
        self._terminate_proc()
        cmd = self._build_command(start_sec=start_sec)
        try:
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW

            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=10 ** 6,
                creationflags=creation_flags
            )
        except Exception as exc:
            raise FFmpegDecodingError(f"Failed to start ffmpeg: {exc}")

    def _interrupt_proc(self) -> None:
        proc = self._proc
        if proc:
            try:
                proc.terminate()
            except Exception:
                pass

    def _terminate_proc(self) -> None:
        if self._proc:
            try:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=0.1)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                    try:
                        self._proc.wait(timeout=0.1)
                    except subprocess.TimeoutExpired:
                        pass
            except Exception:
                pass
            finally:
                try:
                    if self._proc.stdout:
                        self._proc.stdout.close()
                except Exception:
                    pass
                self._proc = None

    def _emit_frame(self, abs_frame: int, timestamp: float, frame_data: bytes) -> None:
        if self._stop_requested:
            return
            
        try:
            bytes_per_line = self.width * 3
            fmt = QImage.Format.Format_RGB888
            img = QImage(frame_data, self.width, self.height, bytes_per_line, fmt)
            if not img.isNull():
                self.frame_ready.emit(abs_frame, timestamp, img.copy(), self._current_gen)
        except Exception:
            pass

    def run(self) -> None:
        current_start = self.start_time
        try:
            self._start_proc(start_sec=current_start)
        except Exception as e:
            self.error.emit(str(e))
            return

        if not self._proc or not self._proc.stdout:
            self.error.emit("Failed to get stdout from ffmpeg")
            return

        frame_index = 0
        wall_clock_start = time.perf_counter()
        pts_offset = current_start
        self._current_gen = 0
        
        prev_is_playing = self._is_playing

        while not self._stop_requested:
            if self.isInterruptionRequested():
                break

            if self._seek_request:
                req = self._seek_request
                self._seek_request = None
                
                try:
                    self._terminate_proc()
                    self._start_proc(start_sec=req['sec'])
                except Exception as exc:
                    self.error.emit(str(exc))
                    break
                    
                if not self._proc or not self._proc.stdout:
                    break
                    
                current_start = req['sec']
                pts_offset = req['sec']
                frame_index = 0
                wall_clock_start = time.perf_counter()
                
                self._is_playing = req['play']
                self._step_request_count = 0 if req['play'] else 1
                self._pause_event.set()
                self._current_gen = req['gen']
                prev_is_playing = self._is_playing
                continue

            if not self._is_playing and self._step_request_count == 0:
                self._pause_event.clear()
                self._pause_event.wait(timeout=0.1)
                prev_is_playing = False
                continue

            try:
                if not self._proc or not self._proc.stdout:
                    if self._seek_request:
                        continue
                    break
                    
                frame_data = self._proc.stdout.read(self._frame_bytes)
                if not frame_data or len(frame_data) < self._frame_bytes:
                    if self._seek_request:
                        continue
                    break      
            except (BrokenPipeError, OSError, ValueError):
                if self._seek_request:
                    continue
                break
            except Exception:
                if self._seek_request:
                    continue
                break

            if self._seek_request:
                continue

            timestamp_seconds = pts_offset + (frame_index / max(1.0, self.fps))
            abs_frame = int(round(timestamp_seconds * self.fps))

            eff_fps = max(0.1, self.fps * self._playback_rate)  # FIX: Prevent ZeroDivision

            if self._is_playing:
                if not prev_is_playing:
                    wall_clock_start = time.perf_counter() - (frame_index / eff_fps)
                    prev_is_playing = True
                
                target_wall_time = wall_clock_start + (frame_index / eff_fps)
                now = time.perf_counter()
                delay = target_wall_time - now
                
                if delay < -0.150:
                    frame_index += 1
                    continue

            self._emit_frame(abs_frame, timestamp_seconds, frame_data)

            if self._step_request_count > 0:
                self._step_request_count -= 1
                frame_index += 1
                prev_is_playing = False
                continue

            if self._is_playing:
                target_wall_time = wall_clock_start + (frame_index / eff_fps)
                now = time.perf_counter()
                delay = target_wall_time - now
                
                if delay > 0:
                    end_time = now + delay
                    while time.perf_counter() < end_time:
                        if self._stop_requested or self._seek_request or not self._is_playing:
                            break
                        time.sleep(0.001)

            frame_index += 1

        self._terminate_proc()
        if not self._stop_requested:
            self.finished.emit()