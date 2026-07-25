"""
Editing Engine for handling video cut, split, and extract operations.
"""
import os
from typing import Tuple
from app.ffmpeg.ffmpeg_manager import FFmpegManager

class EditingEngine:
    """Handles the logic of video manipulation via FFmpeg."""
    
    def __init__(self, ffmpeg_manager: FFmpegManager):
        self.ffmpeg = ffmpeg_manager

    def extract_clip(self, input_path: str, output_path: str, start_ms: int, end_ms: int, frame_accurate: bool = False) -> bool:
        """
        Extracts a portion of the video.
        Uses stream copy for speed if frame_accurate=False.
        """
        start_sec = start_ms / 1000.0
        duration_sec = (end_ms - start_ms) / 1000.0
        
        return self.ffmpeg.trim_video(
            input_path=input_path,
            output_path=output_path,
            start_sec=start_sec,
            duration_sec=duration_sec,
            lossless=not frame_accurate
        )

    def split_video(self, input_path: str, split_ms: int, output_dir: str, base_name: str) -> Tuple[bool, str, str]:
        """
        Splits a video into two parts at the given timestamp.
        """
        part1_path = os.path.join(output_dir, f"{base_name}_part1.mp4")
        part2_path = os.path.join(output_dir, f"{base_name}_part2.mp4")
        
        # Part 1: Start to split point
        success1 = self.extract_clip(input_path, part1_path, 0, split_ms, frame_accurate=False)
        # Part 2: Split point to End
        success2 = self.extract_clip(input_path, part2_path, split_ms, 99999999, frame_accurate=False)
        
        return (success1 and success2), part1_path, part2_path
