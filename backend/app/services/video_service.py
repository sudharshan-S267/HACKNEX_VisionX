import logging
import os
import json
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from collections import Counter
import cv2
import numpy as np

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.camera import Camera
from app.models.video import Video
from app.models.event import Event
from app.services.detection_service import detection_service
from app.services.evidence_service import evidence_service
from app.services.attribute_service import attribute_service
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

        file_size = dest_path.stat().st_size
        print("\n" + "=" * 50)
        print("VIDEO INGESTION")
        print("=" * 50)
        print(f"Original filename : {filename}")
        print(f"Saved path        : {dest_path}")
        print(f"File size         : {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
        print("=" * 50 + "\n")

        return dest_path

    @staticmethod
    def reset_stuck_processing(db) -> None:
        """
        At startup, reset any videos stuck in 'processing' state to 'failed'.
        These were left unfinished due to a previous server crash.
        """
        stuck = db.query(Video).filter(Video.processing_status == "processing").all()
        for v in stuck:
            logger.warning(
                f"[STARTUP] Video id={v.id} ({v.filename}) was stuck in 'processing'. "
                f"Resetting to 'failed'. Re-upload to reprocess."
            )
            v.processing_status = "failed"
            v.error_message = "Server restarted while video was processing."
            camera = db.query(Camera).filter(Camera.camera_id == v.camera_id).first()
            if camera and camera.status == "processing":
                has_events = db.query(Event).filter(Event.camera_id == v.camera_id).count() > 0
                camera.status = "online" if has_events else "offline"
        if stuck:
            db.commit()

    @staticmethod
    def process_video_background(video_id: int) -> None:
        """
        Real video processing pipeline:
        1. Validate uploaded file.
        2. Open video with OpenCV — read real metadata.
        3. Sample frames using FRAME_SAMPLE_INTERVAL.
        4. Run YOLO inference on each sampled frame.
        5. Aggregate detections into per-track events using ByteTrack IDs.
        6. Save events to database.
        7. Generate evidence clips via FFmpeg/OpenCV.
        8. Save annotated debug frames.
        9. Update video status to 'completed'.
        """
        db = SessionLocal()
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                logger.error(f"Video record id={video_id} not found in database.")
                return

            # ── Resolve absolute path ────────────────────────────────────────
            video_path = Path(video.filename)
            if not video_path.is_absolute():
                video_path = (settings.VIDEO_DIR / video_path.name).resolve()

            print("\n" + "=" * 50)
            print("VISIONTRACE PROCESSING")
            print("=" * 50)
            print(f"Video ID          : {video_id}")
            print(f"Camera            : {video.camera_id}")
            print(f"File              : {video_path}")
            print("=" * 50)

            # ── File existence check ─────────────────────────────────────────
            if not video_path.exists():
                msg = f"Video file not found: {video_path}"
                logger.error(f"[INGEST] {msg}")
                video.processing_status = "failed"
                db.commit()
                return

            file_size = video_path.stat().st_size
            if file_size == 0:
                msg = f"Video file is empty (0 bytes): {video_path}"
                logger.error(f"[INGEST] {msg}")
                video.processing_status = "failed"
                db.commit()
                return

            print(f"PROCESSING ACTUAL FILE: {video_path}")
            print(f"File exists       : True")
            print(f"File size         : {file_size:,} bytes")

            video.processing_status = "processing"
            db.commit()

            # ── Read video metadata ──────────────────────────────────────────
            try:
                fps, duration, total_frames, width, height = get_video_metadata(video_path)
                video.fps = round(fps, 2)
                video.duration = round(duration, 2)
                db.commit()
            except Exception as e:
                logger.error(f"[INGEST] Failed to read video metadata: {e}")
                video.processing_status = "failed"
                db.commit()
                return

            print(f"\nVIDEO:")
            print(f"  path      = {video_path}")
            print(f"  fps       = {fps}")
            print(f"  frames    = {total_frames}")
            print(f"  width     = {width}")
            print(f"  height    = {height}")
            print(f"  duration  = {duration:.2f}s")

            # ── Open video ───────────────────────────────────────────────────
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                msg = f"OpenCV could not open video file: {video_path}"
                logger.error(f"[INGEST] {msg}")
                video.processing_status = "failed"
                db.commit()
                return

            # ── YOLO model ───────────────────────────────────────────────────
            try:
                model = detection_service.get_model()
            except Exception as e:
                logger.error(f"\nYOLO INITIALIZATION FAILED:\n{e}\n")
                video.processing_status = "failed"
                db.commit()
                cap.release()
                return

            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"

            sample_interval = max(1, settings.FRAME_SAMPLE_INTERVAL)
            print(f"\n  Model             : {settings.YOLO_MODEL}")
            print(f"  Device            : {device}")
            print(f"  Sample interval   : every {sample_interval} frames")
            print("=" * 50 + "\n")

            # ── Remove stale events for this camera (re-upload scenario) ─────
            db.query(Event).filter(Event.camera_id == video.camera_id).delete()
            db.commit()

            # ── Debug directory ──────────────────────────────────────────────
            debug_dir = (settings.BASE_DIR / "data" / "debug" / str(video_id)).resolve()
            debug_dir.mkdir(parents=True, exist_ok=True)

            # ── Frame streaming loop ─────────────────────────────────────────
            # track_id -> { object_type, timestamps, confidences, bboxes, colors, frames, crops }
            tracks: Dict[int, Dict[str, Any]] = {}
            co_located_by_frame: Dict[int, List[Dict[str, Any]]] = {}
            untracked_counter = 100000  # High range so they don't collide with real track IDs

            frame_idx = 0
            frames_read = 0
            frames_processed = 0
            frames_with_detections = 0
            raw_detection_count = 0

            # Debug frame save limit (save at most first 20 annotated frames with detections)
            debug_frames_saved = 0
            MAX_DEBUG_FRAMES = 20

            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                frames_read += 1

                if frame_idx % sample_interval == 0:
                    frames_processed += 1
                    timestamp = round(float(frame_idx / fps), 2)

                    # ── YOLO inference ───────────────────────────────────────
                    detections = detection_service.detect_frame(
                        frame, conf_threshold=0.35, persist_track=True
                    )

                    if detections:
                        frames_with_detections += 1
                        raw_detection_count += len(detections)
                        co_located_by_frame[frame_idx] = detections
                        logger.info(
                            f"Frame {frame_idx}/{total_frames} ({timestamp}s) "
                            f"— {len(detections)} detection(s)"
                        )
                        for det in detections:
                            logger.info(
                                f"  {det['object_type'].upper()} conf={det['confidence']:.4f} "
                                f"color={det.get('color','?')} "
                                f"track={det.get('object_id','?')}"
                            )

                        # ── Debug frame annotation ───────────────────────────
                        if debug_frames_saved < MAX_DEBUG_FRAMES:
                            debug_frame = frame.copy()
                            for det in detections:
                                x1, y1, x2, y2 = det["bbox"]
                                color_bgr = (0, 255, 0)  # green default
                                label = (
                                    f"{det['object_type'].upper()} {det['confidence']:.2f}"
                                )
                                if det.get("object_id") is not None:
                                    label += f" T{det['object_id']}"
                                if det.get("color"):
                                    label += f" {det['color']}"
                                ts_label = f"{int(timestamp//60):02d}:{timestamp%60:05.2f}"
                                cv2.rectangle(debug_frame, (x1, y1), (x2, y2), color_bgr, 2)
                                cv2.putText(
                                    debug_frame, label,
                                    (x1, max(y1 - 10, 10)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_bgr, 1
                                )
                                cv2.putText(
                                    debug_frame, ts_label,
                                    (x1, min(y2 + 15, frame.shape[0] - 5)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1
                                )
                            debug_out = debug_dir / f"frame_{frame_idx:06d}.jpg"
                            cv2.imwrite(str(debug_out), debug_frame)
                            debug_frames_saved += 1

                    # ── Accumulate tracks ─────────────────────────────────────
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
                                "frame_numbers": [],
                                "crops": [],
                            }

                        tracks[t_id]["timestamps"].append(timestamp)
                        tracks[t_id]["confidences"].append(det["confidence"])
                        tracks[t_id]["bboxes"].append(det["bbox"])
                        tracks[t_id]["colors"].append(
                            (det.get("color"), det.get("color_confidence", 0.0))
                        )
                        tracks[t_id]["frame_numbers"].append(frame_idx)

                        # Capture candidate person crops for second-stage attribute enrichment
                        if det["object_type"] == "person" and len(tracks[t_id]["crops"]) < 6:
                            x1, y1, x2, y2 = det["bbox"]
                            if x2 > x1 and y2 > y1:
                                crop_img = frame[y1:y2, x1:x2].copy()
                                tracks[t_id]["crops"].append({
                                    "crop": crop_img,
                                    "confidence": det["confidence"],
                                    "bbox": det["bbox"],
                                    "frame_idx": frame_idx,
                                    "timestamp": timestamp,
                                })

                frame_idx += 1

            cap.release()

            print(f"\nFRAME SCAN COMPLETE:")
            print(f"  Frames read           : {frames_read}")
            print(f"  Frames processed      : {frames_processed}")
            print(f"  Frames with detections: {frames_with_detections}")
            print(f"  Raw detections        : {raw_detection_count}")
            print(f"  Unique tracks         : {len(tracks)}")

            if frames_read == 0:
                logger.error("[PROCESS] Zero frames read from video — processing failed.")
                video.processing_status = "failed"
                db.commit()
                return

            # ── Consolidate tracks into events ───────────────────────────────
            cam_name = settings.CAMERAS.get(video.camera_id, {}).get(
                "camera_name", f"Camera {video.camera_id}"
            )
            created_events_count = 0

            for t_id, t_data in tracks.items():
                # Skip single-frame noise if video is long enough
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

                # Peak confidence detection as representative event
                best_idx = int(np.argmax(confidences))
                peak_timestamp = timestamps[best_idx]
                peak_conf = round(float(confidences[best_idx]), 4)
                peak_bbox = bboxes[best_idx]

                # Dominant color via voting across track
                valid_colors = [c for c, c_conf in color_tuples if c and c != "unknown"]
                final_color = None
                final_color_conf = 0.0

                if valid_colors:
                    color_counts = Counter(valid_colors)
                    final_color = color_counts.most_common(1)[0][0]
                    winning_confs = [
                        c_conf for c, c_conf in color_tuples if c == final_color
                    ]
                    final_color_conf = (
                        round(float(np.mean(winning_confs)), 2) if winning_confs else 0.5
                    )

                # ── Second-Stage Visual Intelligence & Attribute Enrichment Layer ───
                enriched = {}
                if obj_type == "person":
                    rep_frames = attribute_service.select_representative_frames(
                        t_data.get("crops", []), max_reps=3
                    )
                    enriched = attribute_service.enrich_track(
                        video_id=video.id,
                        track_id=t_id,
                        object_type=obj_type,
                        representative_frames=rep_frames,
                        co_located_detections_by_frame=co_located_by_frame,
                    )

                if obj_type == "person" and enriched:
                    desc_parts = []
                    if enriched.get("clothing_upper_color"):
                        desc_parts.append(f"wearing {enriched.get('clothing_upper')}")
                    if enriched.get("clothing_lower_color"):
                        desc_parts.append(f"wearing {enriched.get('clothing_lower')}")
                    if enriched.get("has_backpack"):
                        desc_parts.append("with a backpack")
                    if enriched.get("has_cap"):
                        desc_parts.append("wearing a cap")
                    desc = f"person detected ({', '.join(desc_parts)})" if desc_parts else "person detected"
                elif final_color:
                    desc = f"{final_color} {obj_type} detected"
                else:
                    desc = f"{obj_type} detected"

                evt_code = f"evt_{video.camera_id}_{t_id:04d}"

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
                    clothing_upper=enriched.get("clothing_upper"),
                    clothing_upper_color=enriched.get("clothing_upper_color"),
                    clothing_lower=enriched.get("clothing_lower"),
                    clothing_lower_color=enriched.get("clothing_lower_color"),
                    has_backpack=1 if enriched.get("has_backpack") else 0,
                    has_handbag=1 if enriched.get("has_handbag") else 0,
                    has_suitcase=1 if enriched.get("has_suitcase") else 0,
                    has_cap=1 if enriched.get("has_cap") else 0,
                    has_hat=1 if enriched.get("has_hat") else 0,
                    carried_objects=json.dumps(enriched.get("carried_objects", [])),
                    attribute_confidence=enriched.get("attribute_confidence"),
                    attributes_json=json.dumps(enriched) if enriched else None,
                )
                db.add(event)
                db.flush()

                # Generate evidence clip from the SAME uploaded video
                clip_path = evidence_service.generate_clip(
                    video_path=video_path,
                    timestamp=peak_timestamp,
                    duration=duration,
                    event_id=event.id,
                    force=True,
                )
                event.evidence_path = clip_path
                created_events_count += 1

                logger.info(
                    f"[EVENT] {evt_code} | track={t_id} | {desc} "
                    f"| conf={peak_conf:.4f} | ts={peak_timestamp}s "
                    f"| [{t_start}s-{t_end}s] | appearances={appearances}"
                )

            # ── Mark completed ───────────────────────────────────────────────
            video.processing_status = "completed"

            camera = db.query(Camera).filter(Camera.camera_id == video.camera_id).first()
            if camera:
                camera.status = "online"
                camera.video_path = f"/api/v1/cameras/{video.camera_id}/video"
                total_evts = db.query(Event).filter(Event.camera_id == video.camera_id).count()
                camera.event_count = total_evts

            db.commit()

            print("\n" + "=" * 50)
            print("PROCESSING COMPLETE")
            print("=" * 50)
            print(f"  Frames read           : {frames_read}")
            print(f"  Frames processed      : {frames_processed}")
            print(f"  Frames with detections: {frames_with_detections}")
            print(f"  Raw detections        : {raw_detection_count}")
            print(f"  Unique tracks         : {len(tracks)}")
            print(f"  Final events stored   : {created_events_count}")
            print(f"  Debug frames saved    : {debug_frames_saved} → {debug_dir}")
            print("=" * 50 + "\n")

            logger.info(
                f"[DATABASE] Video {video_id} ({video_path.name}) processed. "
                f"{created_events_count} events stored for camera {video.camera_id}."
            )

        except Exception as e:
            logger.exception(f"Unexpected error during video processing video_id={video_id}: {e}")
            try:
                video = db.query(Video).filter(Video.id == video_id).first()
                if video:
                    video.processing_status = "failed"
                    video.error_message = str(e)
                    camera = db.query(Camera).filter(Camera.camera_id == video.camera_id).first()
                    if camera and camera.status == "processing":
                        has_events = db.query(Event).filter(Event.camera_id == video.camera_id).count() > 0
                        camera.status = "online" if has_events else "offline"
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()


video_service = VideoService()
