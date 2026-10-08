import logging
import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict
import cv2
import numpy as np

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

            # Clean up previous stale events for this camera to ensure footage grounding
            db.query(Event).filter(Event.camera_id == video.camera_id).delete()
            db.commit()

            frame_idx = 0
            sample_interval = max(1, settings.FRAME_SAMPLE_INTERVAL)
            logger.info(
                f"[PROCESS] Beginning processing for {video_path.name} on {video.camera_id} "
                f"(FPS={fps}, duration={duration}s, interval={sample_interval} frames, total_frames={total_frames})"
            )

            # Dictionary to accumulate object track history across frames:
            # track_id -> { "object_type": str, "timestamps": [], "confidences": [], "bboxes": [], "colors": [] }
            tracks: Dict[int, Dict[str, Any]] = {}
            untracked_counter = 1000

            # 3 & 4: Stream frames incrementally without loading full video into RAM
            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                if frame_idx % sample_interval == 0:
                    timestamp = round(float(frame_idx / fps), 2)
                    detections = detection_service.detect_frame(frame, conf_threshold=0.35, persist_track=True)

                    if detections:
                        logger.info(f"[FRAME] Frame {frame_idx}/{total_frames} ({timestamp}s) - [YOLO] {len(detections)} objects detected")

                    for det in detections:
                        t_id = det.get("object_id")
                        if t_id is None:
                            t_id = untracked_counter
                            untracked_counter += 1

                        if t_id not in tracks:
                            tracks[t_id] = {
                                "object_type": det["object_type"],
                                "timestamps": [],
                                "confidences": [],
                                "bboxes": [],
                                "colors": [],
                            }

                        tracks[t_id]["timestamps"].append(timestamp)
                        tracks[t_id]["confidences"].append(det["confidence"])
                        tracks[t_id]["bboxes"].append(det["bbox"])
                        tracks[t_id]["colors"].append((det.get("color"), det.get("color_confidence", 0.0)))

                frame_idx += 1

            cap.release()
            logger.info(f"[PROCESS] Finished frame scanning. Aggregating {len(tracks)} detected tracks into verified events...")

            # 5: Aggregate tracks into distinct, verified events
            cam_name = settings.CAMERAS.get(video.camera_id, {}).get("camera_name", f"Camera {video.camera_id}")
            created_events_count = 0

            for t_id, t_data in tracks.items():
                # Filter out single-frame noise flickers if video is long enough
                appearances = len(t_data["timestamps"])
                if duration > 5.0 and appearances < 2:
                    continue

                obj_type = t_data["object_type"]
                timestamps = t_data["timestamps"]
                confidences = t_data["confidences"]
                bboxes = t_data["bboxes"]
                color_tuples = t_data["colors"]

                t_start = round(min(timestamps), 2)
                t_end = round(max(timestamps), 2)

                # Pick the peak confidence detection as the primary timestamp and bbox
                best_idx = int(np.argmax(confidences))
                peak_timestamp = timestamps[best_idx]
                peak_conf = round(float(confidences[best_idx]), 4)
                peak_bbox = bboxes[best_idx]

                # Dominant color consensus voting across track
                valid_colors = [c for c, c_conf in color_tuples if c and c != "unknown"]
                final_color = None
                final_color_conf = 0.0

                if valid_colors:
                    from collections import Counter
                    color_counts = Counter(valid_colors)
                    final_color = color_counts.most_common(1)[0][0]
                    # Compute average confidence for the winning color
                    winning_confs = [c_conf for c, c_conf in color_tuples if c == final_color]
                    final_color_conf = round(float(np.mean(winning_confs)), 2) if winning_confs else 0.5
                    logger.info(f"[COLOR] Track {t_id} ({obj_type}) = {final_color} (confidence={final_color_conf})")

                desc = f"{final_color} {obj_type} detected" if final_color else f"{obj_type} detected"
                evt_code = f"evt_{video.camera_id}_{t_id:04d}"

                # Create event record in DB
                event = Event(
                    event_id=evt_code,
                    camera_id=video.camera_id,
                    video_id=video.id,
                    camera_name=cam_name,
                    timestamp=peak_timestamp,
                    timestamp_start=t_start,
                    timestamp_end=t_end,
                    confidence=peak_conf,
                    color_confidence=final_color_conf,
                    event_type=f"{obj_type}_detected",
                    object_type=obj_type,
                    object_id=t_id,
                    color=final_color,
                    bbox=peak_bbox,
                    description=desc,
                    evidence_path=None,
                )
                db.add(event)
                db.flush()  # Allocates event.id

                # Generate real evidence clip around the peak timestamp
                clip_path = evidence_service.generate_clip(
                    video_path=video_path,
                    timestamp=peak_timestamp,
                    duration=duration,
                    event_id=event.id,
                )
                event.evidence_path = clip_path
                created_events_count += 1
                logger.info(f"[EVENT] Created {evt_code} for Track {t_id} ({desc}) at {peak_timestamp}s [{t_start}s-{t_end}s]")

            # Mark video processing completed
            video.processing_status = "completed"

            # Update camera status and verified event count
            camera = db.query(Camera).filter(Camera.camera_id == video.camera_id).first()
            if camera:
                camera.status = "online"
                camera.video_path = f"/api/v1/cameras/{video.camera_id}/video"
                total_evts = db.query(Event).filter(Event.camera_id == video.camera_id).count()
                camera.event_count = total_evts

            db.commit()
            logger.info(f"[DATABASE] Video {video_id} ({video_path.name}) successfully processed. Stored {created_events_count} verified events.")

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
