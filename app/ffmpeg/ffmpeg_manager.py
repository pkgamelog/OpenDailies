import os, sys, json, subprocess
from typing import Dict, Any, Optional

class FFmpegManager:
    def __init__(self):
        self.ffmpeg_path = self._get_executable_path("ffmpeg")
        self.ffprobe_path = self._get_executable_path("ffprobe")

    def _get_executable_path(self, exe_name: str) -> str:
        if getattr(sys, 'frozen', False):
            return os.path.join(sys._MEIPASS, f"{exe_name}.exe")
        return exe_name

    def probe_video(self, file_path: str) -> Optional[Dict[str, Any]]:
        try:
            cmd = [self.ffprobe_path, "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", file_path]
            
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW
                
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=creation_flags)
            if proc.returncode != 0:
                return None
            info = json.loads(proc.stdout)
            
            streams = info.get("streams", [])
            vstream = None
            for s in streams:
                if s.get("codec_type") == "video":
                    vstream = s
                    break
            fmt = info.get("format", {})
            if not vstream:
                return None

            frame_rate = 0.0
            fr = vstream.get("r_frame_rate") or vstream.get("avg_frame_rate")
            try:
                if fr and "/" in fr:
                    num, den = fr.split("/")
                    frame_rate = float(num) / float(den) if float(den) != 0 else 0.0
                else:
                    frame_rate = float(fr or 0.0)
            except Exception:
                frame_rate = 0.0

            # FIX: Prevent 0 FPS which causes ZeroDivisionError crashes downstream
            if frame_rate <= 0.0:
                frame_rate = 24.0

            duration = 0.0
            try:
                duration = float(fmt.get("duration", 0.0))
            except Exception:
                duration = 0.0

            return {
                "duration_ms": int(duration * 1000),
                "frame_rate": frame_rate,
                "width": int(vstream.get("width", 0)),
                "height": int(vstream.get("height", 0)),
                "codec": vstream.get("codec_name", ""),
            }
        except Exception:
            return None

    def trim_video(self, input_path: str, output_path: str, start_sec: float, duration_sec: float, lossless: bool = True) -> bool:
        try:
            cmd = [self.ffmpeg_path, "-y", "-ss", str(start_sec), "-i", input_path, "-t", str(duration_sec)]
            if lossless:
                cmd += ["-c", "copy", output_path]
            else:
                cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", output_path]

            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW
                
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=creation_flags)
            return proc.returncode == 0
        except Exception:
            return False