"""
Playback Engine backed by FFmpegDecoderThread.
Acts purely as a controller. Implements True Fast-Stepping and strict Stale Frame Rejection.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QImage

from app.playback.ffprobe_service import FFProbeService, VideoMetadata
from app.playback.ffmpeg_decoder import FFmpegDecoderThread
from app.playback.frame_utils import frames_to_seconds, seconds_to_frames

logger = logging.getLogger(__name__)

class PlaybackEngine(QObject):
    """Abstracts the FFmpeg decoder to provide frame-accurate playback, seeking, and looping."""
    
    position_changed = Signal(int)
    duration_changed = Signal(int)
    state_changed = Signal(str)
    error_occurred = Signal(str)
    frame_ready = Signal(int, float, QImage)
    loop_state_changed = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._metadata: Optional[VideoMetadata] = None
        self._decoder: Optional[FFmpegDecoderThread] = None
        
        self._current_frame: int = 0
        self._target_frame: int = -1  # Tracks requested frame to reject stale frames
        self._total_frames: int = 0
        self._fps: float = 24.0
        self._state: str = "stopped"
        self._playback_rate: float = 1.0
        self._loop_enabled: bool = False
        
        # Scrubbing Throttling & Debounce (50ms = 20Hz seek rate)
        self._target_scrub_frame: int = -1
        self._scrub_timer = QTimer(self)
        self._scrub_timer.setSingleShot(True)
        self._scrub_timer.setInterval(50)
        self._scrub_timer.timeout.connect(self._execute_debounced_seek)
        
        # Signal Crosstalk Avoidance
        self._is_block_signals = False

    @property
    def state(self) -> str:
        """Public read-only access to the current playback state."""
        return self._state

    def load_video(self, path: str, frame_rate: Optional[float] = None) -> None:
        """Probes video, prepares decoder, and emits total frames."""
        self._cancel_pending_scrubs()
        
        try:
            probe = FFProbeService()
            self._metadata = probe.probe(path)
        except Exception as e:
            logger.exception("FFProbe failed: %s", e)
            raise

        if frame_rate:
            self._metadata.fps = float(frame_rate)
            
        self._fps = self._metadata.fps or 24.0
        self._total_frames = int(self._metadata.frame_count) if self._metadata.frame_count else int((self._metadata.duration_ms / 1000.0) * self._fps)
        self._current_frame = 0
        self._target_frame = 0
        
        self._create_decoder(start_time_sec=0.0)
        self.duration_changed.emit(self._total_frames)
        self._emit_position_changed(0)
        
        # Start the thread immediately, pause it, and request the first frame
        if self._decoder:
            self._decoder.start_decoding()
            self._decoder.pause_decoding()
            self._decoder.request_single_frame()
            self._state = "paused"

    def play(self) -> None:
        """Starts or resumes playback."""
        if not self._metadata: return
        
        # Flush any pending scrub so playback starts from the user's requested frame
        self._flush_pending_scrub()
        
        max_frame = max(0, self._total_frames - 1)
        
        # If at or past EOF, restart from frame 0
        if self._current_frame >= max_frame and self._state != "playing":
            self._current_frame = 0
            self._target_frame = 0
            self._emit_position_changed(0)
            if self._decoder:
                self._destroy_decoder()
            self._create_decoder(start_time_sec=0.0)
            if self._decoder:
                self._decoder.start_decoding()
                
        if not self._decoder or not self._decoder.isRunning():
            start_sec = frames_to_seconds(self._current_frame, self._fps)
            self._create_decoder(start_time_sec=start_sec)
            if self._decoder:
                self._decoder.start_decoding()
                self._decoder.pause_decoding()
            
        if self._state == "playing":
            return
            
        try:
            self._decoder.set_playback_rate(self._playback_rate)
            self._decoder.resume_decoding()
            self._target_frame = -1  # Accept all frames during continuous playback
            self._state = "playing"
            self.state_changed.emit(self._state)
        except Exception:
            logger.exception("Failed to start/resume decoder")
            self.state_changed.emit("error")

    def pause(self) -> None:
        """Pauses the decoder thread."""
        if not self._decoder: return
        self._decoder.pause_decoding()
        self._state = "paused"
        self.state_changed.emit(self._state)

    def stop(self) -> None:
        """Stops playback completely, cancels scrubs, and resets to frame 0."""
        self._cancel_pending_scrubs()
        self._state = "stopped"
        self.state_changed.emit(self._state)
        if self._decoder:
            self._destroy_decoder()
        self._current_frame = 0
        self._target_frame = 0
        self._emit_position_changed(0)

    def set_position(self, frame: int) -> None:
        """Sets position via UI slider. Debounces rapid seeks."""
        if not self._metadata: return
        
        # Prevent recursive UI loops
        if self._is_block_signals:
            return
            
        max_frame = max(0, self._total_frames - 1)
        frame = max(0, min(int(frame), max_frame))
        
        # Store the requested frame atomically and debounce the seek
        self._target_scrub_frame = frame
        self._scrub_timer.start()

    def _execute_debounced_seek(self) -> None:
        """Executes the seek only when the timer times out, skipping intermediate seeks."""
        if self._target_scrub_frame == -1: return
        
        frame = self._target_scrub_frame
        self._target_scrub_frame = -1
        
        self._seek_to_frame(frame)

    def step_frame_forward(self) -> None:
        """Steps exactly one frame forward. Cancels slider scrub."""
        if not self._metadata: return
        self._cancel_pending_scrubs()
        self.pause()
        
        max_frame = max(0, self._total_frames - 1)
        target = min(self._current_frame + 1, max_frame)
        
        # TRUE FAST-PATH: If stepping forward sequentially, ask the paused FFmpeg 
        # process to just read the next frame in its buffer. No restart required!
        if (target == self._current_frame + 1 and 
            self._current_frame < max_frame and
            self._decoder and self._decoder.isRunning()):
            
            self._current_frame = target
            self._target_frame = target
            self._decoder.request_single_frame()
            self._emit_position_changed(target)
            return
            
        # Fallback to full seek if at EOF or decoder is dead
        self._seek_to_frame(target)

    def step_frame_backward(self) -> None:
        """Steps exactly one frame backward. Cancels slider scrub."""
        if not self._metadata: return
        self._cancel_pending_scrubs()
        self.pause()
        
        target = max(0, self._current_frame - 1)
        self._seek_to_frame(target)

    def _seek_to_frame(self, frame: int, play_after_seek: bool = False) -> None:
        """Instantly seeks to a specific frame. Used by step buttons and debounced slider."""
        if not self._metadata: return
        
        max_frame = max(0, self._total_frames - 1)
        frame = max(0, min(int(frame), max_frame))
        seconds = frame / self._fps
        
        # Track the target frame to reject stale frames from interrupted seeks
        self._target_frame = frame
        
        if self._decoder and self._decoder.isRunning():
            self._decoder.seek(seconds, play_after_seek=play_after_seek)
        else:
            self._create_decoder(start_time_sec=seconds)
            if self._decoder:
                self._decoder.start_decoding()
                self._decoder.pause_decoding()
                self._decoder.seek(seconds, play_after_seek=play_after_seek)

    def set_playback_rate(self, rate: float) -> None:
        self._playback_rate = float(rate)
        if self._decoder:
            self._decoder.set_playback_rate(rate)

    def toggle_loop(self) -> bool:
        self._loop_enabled = not self._loop_enabled
        self.loop_state_changed.emit(self._loop_enabled)
        return self._loop_enabled

    def position(self) -> int:
        return self._current_frame

    # --- Internal Helpers ---

    def _cancel_pending_scrubs(self) -> None:
        """Cancels any pending debounce timer to prevent stale seeks."""
        self._scrub_timer.stop()
        self._target_scrub_frame = -1

    def _flush_pending_scrub(self) -> None:
        """Immediately executes a pending scrub if the timer is active."""
        if self._scrub_timer.isActive():
            self._scrub_timer.stop()
            if self._target_scrub_frame != -1:
                target = self._target_scrub_frame
                self._target_scrub_frame = -1
                # Execute seek with play=True because we are flushing to play
                self._seek_to_frame(target, play_after_seek=True)

    def _emit_position_changed(self, frame: int) -> None:
        """Helper to emit position_changed safely with re-entrancy block."""
        self._is_block_signals = True
        self.position_changed.emit(frame)
        self._is_block_signals = False

    def _create_decoder(self, start_time_sec: float = 0.0) -> None:
        """Instantiates a decoder thread configured for current metadata."""
        if self._decoder:
            self._destroy_decoder()
            
        if not self._metadata: return

        try:
            self._decoder = FFmpegDecoderThread(
                video_path=self._metadata.path,
                width=self._metadata.width or 640,
                height=self._metadata.height or 480,
                fps=self._fps,
                start_time=start_time_sec,
            )
            self._decoder.frame_ready.connect(self._on_frame_ready)
            self._decoder.finished.connect(self._on_decoder_finished)
            self._decoder.error.connect(self.error_occurred.emit)
        except Exception as e:
            logger.exception("Failed to create decoder: %s", e)
            self._decoder = None

    def _destroy_decoder(self) -> None:
        """Safely stops, waits, and deletes the decoder thread without terminate()."""
        if not self._decoder: return
        dec = self._decoder
        self._decoder = None
        
        try:
            # Disconnect signals FIRST to prevent the finished signal from 
            # triggering false EOF logic when we manually kill the thread.
            try:
                dec.frame_ready.disconnect(self._on_frame_ready)
                dec.finished.disconnect(self._on_decoder_finished)
                dec.error.disconnect(self.error_occurred.emit)
            except Exception:
                pass
                
            dec.stop_decoding()
            dec.requestInterruption()
            dec.quit()
            
            # Wait gracefully. Do not use terminate().
            if not dec.wait(2000):
                logger.warning("Decoder thread failed to exit gracefully after 2s. Forcing termination.")
                # Absolute last resort fallback
                dec.terminate()
                dec.wait(1000)
                
            dec.deleteLater()
        except Exception:
            logger.exception("Error during decoder destruction")

    def _on_frame_ready(self, abs_frame: int, timestamp: float, img: QImage) -> None:
        """Receives frame from decoder. Updates internal state and emits UI signals."""
        # STRICT STALE FRAME REJECTION:
        # If we are not in continuous play mode, and the decoded frame is older 
        # than our requested target, discard it immediately. This prevents timeline snap-back.
        if self._state != "playing" and self._target_frame != -1:
            if abs_frame < self._target_frame:
                logger.debug(f"Ignoring stale frame {abs_frame} (target: {self._target_frame})")
                return
                
        # The decoder is the single source of truth.
        # Only update position if it actually changed to avoid duplicate UI redraws.
        if abs_frame != self._current_frame:
            self._current_frame = abs_frame
            self._emit_position_changed(abs_frame)
            
        self.frame_ready.emit(abs_frame, timestamp, img)

    def _on_decoder_finished(self) -> None:
        """Handles EOF and loop restart logic."""
        # If the engine is already stopped, this signal is from a manual shutdown, ignore it.
        if self._state == "stopped":
            return
            
        max_frame = max(0, self._total_frames - 1)
        
        # If loop is enabled, and we reached EOF while playing
        if self._loop_enabled and self._state == "playing":
            self._current_frame = 0
            self._target_frame = 0
            self._emit_position_changed(0)
            self._destroy_decoder()
            self._create_decoder(start_time_sec=0.0)
            if self._decoder:
                self._decoder.set_playback_rate(self._playback_rate)
                self._decoder.start_decoding()
                self._decoder.resume_decoding()
                self._state = "playing"
                self.state_changed.emit(self._state)
        else:
            # EOF reached, stop playback
            self._current_frame = max_frame
            self._target_frame = max_frame
            self._emit_position_changed(max_frame)
            self._state = "stopped"
            self.state_changed.emit(self._state)
            self._destroy_decoder()