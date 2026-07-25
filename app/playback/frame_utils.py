from __future__ import annotations

from typing import Optional
import math


def frames_to_seconds(frame: int, fps: float) -> float:
    try:
        return frame / float(fps)
    except Exception:
        return 0.0


def seconds_to_frames(seconds: float, fps: float) -> int:
    try:
        return int(round(seconds * float(fps)))
    except Exception:
        return 0


def smpte_from_frame(frame: int, fps: float) -> str:
    """Returns strictly the HH:MM:SS:FF string."""
    try:
        fps_r = max(1, round(fps))
        ff = frame % fps_r
        total_secs = frame // fps_r
        ss = total_secs % 60
        mm = (total_secs // 60) % 60
        hh = total_secs // 3600
        return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"
    except Exception:
        return "00:00:00:00"


def format_display_info(frame: int, total_frames: int, fps: float, mode: int) -> str:
    """
    Formats the display string based on the mode.
    0 = Timecode (HH:MM:SS:FF)
    1 = Frame Code (Frame: X / Y)
    2 = Both (HH:MM:SS:FF | Frame: X / Y)
    """
    tc_str = smpte_from_frame(frame, fps)
    frame_str = f"Frame: {frame} / {total_frames}"
    
    if mode == 0:
        return tc_str
    elif mode == 1:
        return frame_str
    else:
        return f"{tc_str}  |  {frame_str}"


def frame_to_srt_time(frame: int, fps: float) -> str:
    """Converts a frame number to SRT timestamp format: HH:MM:SS,mmm"""
    fps_r = max(1, round(fps))
    ms_per_frame = 1000.0 / fps_r
    total_ms = int(frame * ms_per_frame)
    
    h = total_ms // 3600000
    m = (total_ms % 3600000) // 60000
    s = (total_ms % 60000) // 1000
    ms = total_ms % 1000
    
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"