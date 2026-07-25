from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FFProbeNotFound(Exception):
    """Raised when ffprobe executable cannot be located."""


class InvalidVideoFile(Exception):
    """Raised when the provided file is not a valid/openable video for ffprobe."""


class FFProbeExecutionError(Exception):
    """Raised when ffprobe returns a non-zero exit code or fails to execute."""


@dataclass
class VideoMetadata:
    path: str
    filename: str
    width: Optional[int]
    height: Optional[int]
    fps: Optional[float]
    duration_seconds: Optional[float]
    duration_ms: Optional[int]
    frame_count: Optional[int]
    codec: Optional[str]
    pixel_format: Optional[str]
    bitrate: Optional[int]
    audio_codec: Optional[str]
    has_audio: bool
    rotation: Optional[int]

    def __str__(self) -> str:  # pretty print
        return (
            f"VideoMetadata(path={self.path}, filename={self.filename}, width={self.width}, height={self.height}, "
            f"fps={self.fps}, duration_seconds={self.duration_seconds}, duration_ms={self.duration_ms}, frame_count={self.frame_count}, "
            f"codec={self.codec}, pixel_format={self.pixel_format}, bitrate={self.bitrate}, audio_codec={self.audio_codec}, "
            f"has_audio={self.has_audio}, rotation={self.rotation})"
        )


class FFProbeService:
    """Service for extracting video metadata using ffprobe.

    This class is pure Python and does not depend on Qt.
    """

    def __init__(self, ffprobe_path: Optional[str] = None) -> None:
        # locate ffprobe: priority project_root/ffprobe.exe, then PATH
        self._ffprobe = None
        if ffprobe_path:
            self._ffprobe = ffprobe_path
        else:
            # project root is two levels up from this file (app/playback)
            project_root = Path(__file__).resolve().parents[2]
            cand = project_root / "ffprobe.exe"
            if cand.exists():
                self._ffprobe = str(cand)
                logger.debug("Using ffprobe from project root: %s", self._ffprobe)
            else:
                # try ffprobe in PATH (also accept 'ffprobe')
                which_name = shutil.which("ffprobe") or shutil.which("ffprobe.exe")
                if which_name:
                    self._ffprobe = which_name
                    logger.debug("Using ffprobe from PATH: %s", self._ffprobe)

        if not self._ffprobe:
            logger.error("ffprobe executable not found. Checked project root and PATH.")
            raise FFProbeNotFound("ffprobe executable not found in project root or PATH")

    def probe(self, video_path: str) -> VideoMetadata:
        """Probes the given video file and returns VideoMetadata.

        Raises FFProbeExecutionError or InvalidVideoFile on failure.
        """
        path = Path(video_path)
        if not path.exists():
            logger.error("Video file does not exist: %s", video_path)
            raise InvalidVideoFile(f"File not found: {video_path}")

        cmd = [self._ffprobe, "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", str(path)]
        logger.debug("Running ffprobe command: %s", cmd)

        logger.debug("Running ffprobe: %s", cmd)
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except FileNotFoundError:
            logger.exception("ffprobe executable not found when attempting to run")
            raise FFProbeNotFound("ffprobe executable not found when attempting to run")
        except subprocess.TimeoutExpired:
            logger.exception("ffprobe timed out for file: %s", video_path)
            raise FFProbeExecutionError("ffprobe timed out")

        if proc.returncode != 0:
            logger.error("ffprobe failed (code %s): %s", proc.returncode, proc.stderr)
            raise FFProbeExecutionError(f"ffprobe failed: {proc.stderr.strip()}")

        try:
            info = json.loads(proc.stdout)
        except Exception:
            logger.exception("Failed to parse ffprobe JSON output")
            raise FFProbeExecutionError("Failed to parse ffprobe JSON output")

        streams = info.get("streams", [])
        fmt = info.get("format", {})

        # Find first video stream
        vstream = None
        astream = None
        for s in streams:
            if s.get("codec_type") == "video" and vstream is None:
                vstream = s
            elif s.get("codec_type") == "audio" and astream is None:
                astream = s

        if not vstream:
            logger.error("No video stream found in file: %s", video_path)
            raise InvalidVideoFile("No video stream found")

        # extract basic fields
        filename = path.name

        codec = vstream.get("codec_name")
        pix_fmt = vstream.get("pix_fmt") or vstream.get("pixel_format")

        # width/height
        width = None
        height = None
        try:
            width = int(vstream.get("width")) if vstream.get("width") is not None else None
            height = int(vstream.get("height")) if vstream.get("height") is not None else None
        except Exception:
            width = None
            height = None

        # duration
        duration_seconds = None
        # prefer format.duration
        try:
            if fmt.get("duration") is not None:
                duration_seconds = float(fmt.get("duration"))
            elif vstream.get("duration") is not None:
                duration_seconds = float(vstream.get("duration"))
        except Exception:
            duration_seconds = None

        if duration_seconds is None:
            logger.error("Could not determine duration for file: %s", video_path)
            raise InvalidVideoFile("Could not determine video duration")

        duration_ms = int(duration_seconds * 1000)

        # fps parsing
        fps = None
        for key in ("r_frame_rate", "avg_frame_rate", "frame_rate"):
            fr = vstream.get(key)
            if fr:
                try:
                    if isinstance(fr, str) and "/" in fr:
                        num, den = fr.split("/")
                        numf = float(num)
                        denf = float(den)
                        if denf != 0:
                            fps = numf / denf
                            break
                    else:
                        fps = float(fr)
                        break
                except Exception:
                    continue

        if fps is None or fps <= 0:
            # try to compute from format tags
            try:
                # sometimes tags contain "TBR" or similar
                tags = vstream.get("tags") or {}
                tbr = tags.get("TBR") or tags.get("FRAME_RATE")
                if tbr:
                    fps = float(tbr)
            except Exception:
                fps = None

        if fps is None or fps <= 0:
            logger.warning("FPS could not be determined reliably for %s", video_path)

        # frame count
        frame_count = None
        nb_frames = vstream.get("nb_frames")
        if nb_frames is not None:
            try:
                frame_count = int(nb_frames)
            except Exception:
                frame_count = None

        if frame_count is None and fps and duration_seconds:
            try:
                frame_count = int(round(duration_seconds * fps))
            except Exception:
                frame_count = None

        # bitrate
        bitrate = None
        try:
            br = fmt.get("bit_rate") or vstream.get("bit_rate")
            if br is not None:
                bitrate = int(br)
        except Exception:
            bitrate = None

        # audio codec
        audio_codec = None
        has_audio = False
        if astream:
            has_audio = True
            audio_codec = astream.get("codec_name")

        # rotation metadata
        rotation = None
        try:
            # common location: tags.rotate or side_data_list.rotation
            tags = vstream.get("tags") or {}
            rot = tags.get("rotate")
            if rot is not None:
                rotation = int(rot)
            else:
                sdl = vstream.get("side_data_list") or []
                if isinstance(sdl, list) and len(sdl) > 0:
                    for sd in sdl:
                        if sd.get("rotation") is not None:
                            rotation = int(sd.get("rotation"))
                            break
        except Exception:
            rotation = None

        meta = VideoMetadata(
            path=str(path.resolve()),
            filename=filename,
            width=width,
            height=height,
            fps=(float(fps) if fps is not None else None),
            duration_seconds=(float(duration_seconds) if duration_seconds is not None else None),
            duration_ms=(int(duration_ms) if duration_ms is not None else None),
            frame_count=(int(frame_count) if frame_count is not None else None),
            codec=(codec if codec else None),
            pixel_format=(pix_fmt if pix_fmt else None),
            bitrate=(bitrate if bitrate else None),
            audio_codec=(audio_codec if audio_codec else None),
            has_audio=bool(has_audio),
            rotation=(int(rotation) if rotation is not None else None),
        )

        logger.debug("Probe result: %s", meta)
        return meta


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser(description="Probe a video file using ffprobe and print metadata")
    parser.add_argument("video", help="Path to video file to probe")
    parser.add_argument("--ffprobe", help="Optional path to ffprobe executable")
    args = parser.parse_args()

    try:
        svc = FFProbeService(ffprobe_path=args.ffprobe)
        md = svc.probe(args.video)
        logger.info("Probe output: %s", md)
    except Exception as e:
        logger.exception("Failed to probe video: %s", e)
        sys.exit(2)
