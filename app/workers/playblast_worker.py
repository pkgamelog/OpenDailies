"""
QThread Worker for exporting Playblasts (burn-in annotations, timecode, and bookmark subtitles).
Respects timeline trim points (In/Out).
"""
import sys
import subprocess
from typing import List, Dict
from PySide6.QtCore import QThread, Signal, QPoint, QRectF, QRect, Qt
from PySide6.QtGui import QImage, QPainter, QPen, QColor, QFont, QPolygon
import math
from app.playback.frame_utils import format_display_info

class PlayblastWorker(QThread):
    progress_updated = Signal(int)
    export_finished = Signal(bool, str)
    error_occurred = Signal(str)

    def __init__(self, ffmpeg_path: str, input_path: str, output_path: str,
                 width: int, height: int, fps: float, total_frames: int,
                 start_frame: int, end_frame: int,
                 annotations: List[Dict], bookmarks: List[Dict], display_mode: int = 2, subtitle_mode: int = 0, parent=None):
        super().__init__(parent)
        self.ffmpeg_path = ffmpeg_path
        self.input_path = input_path
        self.output_path = output_path
        self.width = width
        self.height = height
        self.fps = fps
        self.total_frames = max(1, total_frames)
        
        # Trim region
        self.start_frame = max(0, start_frame)
        self.end_frame = min(self.total_frames - 1, end_frame)
        if self.end_frame <= self.start_frame:
            self.end_frame = self.total_frames - 1
            
        self.export_frame_count = max(1, self.end_frame - self.start_frame + 1)
        
        self.annotations = annotations
        self.bookmarks = bookmarks
        self.display_mode = display_mode
        self.subtitle_mode = subtitle_mode # 0=Off, 1=Bake, 2=SRT, 3=Both
        self._is_cancelled = False

    def run(self):
        # Calculate exact seek time and duration for FFmpeg
        start_sec = self.start_frame / self.fps
        duration_sec = self.export_frame_count / self.fps
        
        # FIX: Add -ss and -t to decode_cmd to only process the trimmed region
        decode_cmd = [
            self.ffmpeg_path, 
            "-ss", f"{start_sec:.3f}", 
            "-t", f"{duration_sec:.3f}",
            "-i", self.input_path, 
            "-f", "rawvideo", 
            "-pix_fmt", "rgb24", 
            "-"
        ]
        
        encode_cmd = [
            self.ffmpeg_path, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{self.width}x{self.height}", "-r", str(self.fps),
            "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", self.output_path
        ]

        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW

        try:
            decode_proc = subprocess.Popen(decode_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=creation_flags)
            encode_proc = subprocess.Popen(encode_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creation_flags)
            
            frame_size = self.width * self.height * 3
            
            # Loop from start_frame to end_frame to maintain absolute frame indexing
            current_frame = self.start_frame
            
            while current_frame <= self.end_frame:
                if self._is_cancelled:
                    decode_proc.terminate()
                    encode_proc.terminate()
                    self.export_finished.emit(False, "Export cancelled.")
                    return

                raw_bytes = decode_proc.stdout.read(frame_size)
                if not raw_bytes or len(raw_bytes) < frame_size:
                    break # EOF

                img = QImage(raw_bytes, self.width, self.height, self.width * 3, QImage.Format.Format_RGB888)
                if img.isNull():
                    current_frame += 1
                    continue

                painter = QPainter(img)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                for ann in self._get_annotations_at_frame(current_frame):
                    self._draw_annotation(painter, ann)
                
                # Only draw burned subtitles if mode is 1 or 3
                if self.subtitle_mode == 1 or self.subtitle_mode == 3:
                    self._draw_bookmark_subtitle(painter, current_frame)
                
                self._draw_display_info(painter, current_frame)
                painter.end()

                encode_proc.stdin.write(img.constBits().tobytes())
                
                # Calculate progress based on exported frames
                progress = int(((current_frame - self.start_frame) / self.export_frame_count) * 100)
                self.progress_updated.emit(progress)
                
                current_frame += 1

            encode_proc.stdin.close()
            encode_proc.wait()
            decode_proc.stdout.close()
            decode_proc.wait()

            if encode_proc.returncode == 0:
                self.progress_updated.emit(100)
                self.export_finished.emit(True, f"Playblast exported: {self.output_path}")
            else:
                self.error_occurred.emit(f"FFmpeg encoding failed with code {encode_proc.returncode}")

        except Exception as e:
            self.error_occurred.emit(str(e))

    def cancel(self):
        self._is_cancelled = True

    def _get_annotations_at_frame(self, frame: int) -> List[Dict]:
        return [a for a in self.annotations if a["frame_number"] <= frame < a["frame_number"] + a.get("duration_frames", 1)]

    def _draw_bookmark_subtitle(self, painter: QPainter, frame: int):
        sub_duration = int(self.fps * 2)
        active_bm = None
        for bm in self.bookmarks:
            bm_frame = bm.get("frame_number", 0)
            if bm_frame <= frame < bm_frame + sub_duration:
                active_bm = bm
                break
        if active_bm:
            text = active_bm.get("name", "Bookmark")
            font = QFont("SF Pro Display", 12)
            font.setBold(True)
            painter.setFont(font)
            text_width = painter.fontMetrics().horizontalAdvance(text)
            x = (self.width - text_width) // 2
            y = self.height - 40
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 180))
            painter.drawRoundedRect(QRect(x - 10, y - 20, text_width + 20, 30), 6, 6)
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(x, y, text)

    def _draw_display_info(self, painter: QPainter, frame: int):
        text = format_display_info(frame, self.total_frames, self.fps, self.display_mode)
        font = QFont("Consolas", 12)
        font.setBold(True)
        painter.setFont(font)
        text_width = painter.fontMetrics().horizontalAdvance(text)
        box_width = text_width + 20
        painter.setPen(QPen(QColor(0, 0, 0, 160)))
        painter.setBrush(QColor(0, 0, 0, 160))
        painter.drawRect(0, 0, box_width, 30)
        painter.setPen(QPen(QColor(76, 141, 255)))
        painter.drawText(10, 20, text)

    def _draw_annotation(self, painter: QPainter, ann: Dict):
        data = ann.get("data", {})
        color = QColor(ann.get("color", "#FF0000"))
        brush_size = data.get("brush_size", 3)
        painter.setOpacity(data.get("opacity", 1.0))
        pen = QPen(color, brush_size)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        points = data.get("points", [])
        if not points: return
        abs_points = [QPoint(int(p["x"] * self.width), int(p["y"] * self.height)) for p in points]
        tool = data.get("tool_type", "pen")
        if tool == "pen":
            if len(abs_points) == 1: painter.drawPoint(abs_points[0])
            else:
                for i in range(len(abs_points) - 1): painter.drawLine(abs_points[i], abs_points[i+1])
        elif tool == "rect" and len(abs_points) >= 2:
            # FIX: Use two-point constructor for correct dimensions in export
            painter.drawRect(QRectF(abs_points[0], abs_points[1]).normalized())
        elif tool == "circle" and len(abs_points) >= 2:
            radius = (abs_points[1] - abs_points[0]).manhattanLength() / 2
            painter.drawEllipse(abs_points[0], radius, radius)
        elif tool == "arrow" and len(abs_points) >= 2:
            painter.drawLine(abs_points[0], abs_points[1])
            angle = math.atan2(abs_points[1].y() - abs_points[0].y(), abs_points[1].x() - abs_points[0].x())
            size = 10 + brush_size
            p1 = QPoint(abs_points[1].x() - int(size * math.cos(angle - math.pi/6)), abs_points[1].y() - int(size * math.sin(angle - math.pi/6)))
            p2 = QPoint(abs_points[1].x() - int(size * math.cos(angle + math.pi/6)), abs_points[1].y() - int(size * math.sin(angle + math.pi/6)))
            painter.drawPolygon(QPolygon([abs_points[1], p1, p2]))
        elif tool == "text" and data.get("text_content"):
            font = QFont("Segoe UI", brush_size * 4)
            painter.setFont(font)
            painter.drawText(abs_points[0], data["text_content"])