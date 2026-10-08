import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional
import cv2

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_ffmpeg_binary() -> Optional[str]:
    """Locate ffmpeg binary via PATH or imageio-ffmpeg."""
    cli = shutil.which("ffmpeg")
    if cli:
        return cli
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    return None


class EvidenceService:
    def __init__(self, evidence_dir: Optional[Path] = None):
        self.evidence_dir = evidence_dir or settings.EVIDENCE_DIR
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_exe = get_ffmpeg_binary()

    def generate_clip(
        self,
        video_path: Path,
        timestamp: float,
        duration: float,
        event_id: int
    ) -> str:
        """
        Generate evidence clip from (timestamp - 3) to (timestamp + 3) seconds.
        Saves under data/evidence/evt_001.mp4.
        Returns the relative or canonical path string.
        """
        start_time = max(0.0, timestamp - 3.0)
        end_time = min(duration, timestamp + 3.0) if duration > 0 else (timestamp + 3.0)
        clip_duration = max(0.5, end_time - start_time)

        output_filename = f"evt_{event_id:03d}.mp4"
        output_file = (self.evidence_dir / output_filename).resolve()

        # If already generated and valid size, return path
        if output_file.exists() and output_file.stat().st_size > 1024:
            return str(output_file)

        # Attempt 1: FFmpeg (fast, produces web-compatible H.264 video)
        if self.ffmpeg_exe:
            try:
                cmd = [
                    self.ffmpeg_exe,
                    "-y",
                    "-ss", f"{start_time:.3f}",
                    "-t", f"{clip_duration:.3f}",
                    "-i", str(video_path),
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-crf", "26",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    str(output_file)
                ]
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
                if result.returncode == 0 and output_file.exists() and output_file.stat().st_size > 0:
                    return str(output_file)
                else:
                    logger.warning(f"FFmpeg failed with code {result.returncode}: {result.stderr.decode('utf-8', errors='ignore')}")
            except Exception as e:
                logger.warning(f"FFmpeg clip generation error: {e}")

        # Attempt 2: OpenCV Fallback
        try:
            self._generate_clip_opencv(video_path, start_time, end_time, output_file)
            if output_file.exists() and output_file.stat().st_size > 0:
                return str(output_file)
        except Exception as e:
            logger.error(f"OpenCV clip generation error: {e}")

        return str(output_file)

    def _generate_clip_opencv(
        self,
        video_path: Path,
        start_time: float,
        end_time: float,
        output_file: Path
    ) -> None:
        """Fallback clip generation using OpenCV VideoWriter."""
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video for clipping: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        start_frame = max(0, int(start_time * fps))
        end_frame = min(total_frames, int(end_time * fps)) if total_frames > 0 else int(end_time * fps)

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(str(output_file), fourcc, fps, (width, height))

        current_frame = start_frame
        while current_frame <= end_frame:
            ret, frame = cap.read()
            if not ret:
                break
            writer.write(frame)
            current_frame += 1

        cap.release()
        writer.release()


evidence_service = EvidenceService()
