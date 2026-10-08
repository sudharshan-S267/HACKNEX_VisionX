import logging
import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict
import cv2

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.camera import Camera
from app.models.video import Video
from app.models.event import Event
from app.services.detection_service import detection_service
from app.services.evidence_service import evidence_service
from app.utils.video import get_video_metadata

logger = logging.getLogger(__name__)


class VideoService:
    @staticmethod
    def save_uploaded_video(file_bytes: bytes, filename: str) -> Path:
        """Save raw uploaded video bytes to data/videos directory."""
        settings.VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        dest_path = (settings.VIDEO_DIR / filename).resolve()
        with open(dest_path, "wb") as f:
            f.write(file_bytes)
        return dest_path

    @staticmethod
    def process_video_background(video_id: int) -> None:
        """
        Background processing pipeline:
        1. Open video with OpenCV.
        2. Read FPS & duration.
        3. Read frames incrementally (streaming, no high RAM usage).
        4. Sample frames using FRAME_SAMPLE_INTERVAL.
        5. Run YOLO object detection.
        6. Store events in database.
        7. Generate evidence video clips (T - 3s to T + 3s).
        8. Update status to 'completed'.
        """
        db = SessionLocal()
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                logger.error(f"Video record id={video_id} not found.")
                return

            video_path = Path(video.filename)
            if not video_path.is_absolute():
                video_path = (settings.VIDEO_DIR / video_path.name).resolve()

            if not video_path.exists():
                logger.error(f"Video file not found at {video_path}")
                video.processing_status = "failed"
                db.commit()
                return

            video.processing_status = "processing"
            db.commit()

            # 1 & 2: Open with OpenCV, extract FPS & duration
            try:
                fps, duration, total_frames, width, height = get_video_metadata(video_path)
                video.fps = round(fps, 2)
                video.duration = round(duration, 2)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to read video metadata: {e}")
                fps = 30.0
                duration = 0.0

            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.error(f"Could not open video file: {video_path}")
                video.processing_status = "failed"
                db.commit()
                return

            frame_idx = 0
            sample_interval = max(1, settings.FRAME_SAMPLE_INTERVAL)
            created_events: List[Dict] = []
            clip_cache: Dict[str, str] = {}  # Cache window -> clip path

            logger.info(f"Beginning frame-by-frame processing for {video_path.name} (FPS={fps}, duration={duration}s, interval={sample_interval})")

            # 3 & 4: Stream frames incrementally without loading full video into RAM
            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                # 5: Sample frames using FRAME_SAMPLE_INTERVAL
                if frame_idx % sample_interval == 0:
                    timestamp = round(float(frame_idx / fps), 2)

                    # 6 & 7: Run YOLO detection on sampled frame
                    detections = detection_service.detect_frame(frame, conf_threshold=0.35, persist_track=True)

                    # 8: Record events
                    for det_idx, det in enumerate(detections):
                        evt_code = f"evt_{video.camera_id}_{int(timestamp*10):04d}_{det_idx+1}"
                        cam_name = settings.CAMERAS.get(video.camera_id, {}).get("camera_name", f"Camera {video.camera_id}")
                        event = Event(
                            event_id=evt_code,
                            camera_id=video.camera_id,
                            camera_name=cam_name,
                            timestamp=timestamp,
                            event_type=f"{det['object_type']}_detected",
                            object_type=det["object_type"],
                            object_id=det.get("object_id"),
                            color=det.get("color"),
                            confidence=det["confidence"],
                            bbox=det["bbox"],
                            description=det["description"],
                            evidence_path=None
                        )
                        db.add(event)
                        db.flush()  # Populates event.id

                        # Clip time window key for deduplicating identical cuts
                        window_key = f"{round(timestamp, 1)}"
                        target_clip_filename = f"evt_{event.id:03d}.mp4"
                        target_clip_path = (settings.EVIDENCE_DIR / target_clip_filename).resolve()

                        if window_key in clip_cache and Path(clip_cache[window_key]).exists():
                            # Fast copy identical window
                            shutil.copyfile(clip_cache[window_key], target_clip_path)
                            event.evidence_path = str(target_clip_path)
                        else:
                            clip_path = evidence_service.generate_clip(
                                video_path=video_path,
                                timestamp=timestamp,
                                duration=duration,
                                event_id=event.id
                            )
                            event.evidence_path = clip_path
                            clip_cache[window_key] = clip_path

                        created_events.append({"id": event.id, "timestamp": timestamp})

                frame_idx += 1

            cap.release()

            # Mark completed
            video.processing_status = "completed"
            
            # Ensure camera status is online and update event count
            camera = db.query(Camera).filter(Camera.camera_id == video.camera_id).first()
            if camera:
                camera.status = "online"
                camera.video_path = f"/api/v1/cameras/{video.camera_id}/video"
                # Update event count
                total_evts = db.query(Event).filter(Event.camera_id == video.camera_id).count()
                camera.event_count = total_evts

            db.commit()
            logger.info(f"Video {video_id} processed successfully. Created {len(created_events)} events.")

        except Exception as e:
            logger.exception(f"Unexpected error in video processing: {e}")
            try:
                video = db.query(Video).filter(Video.id == video_id).first()
                if video:
                    video.processing_status = "failed"
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()


video_service = VideoService()
