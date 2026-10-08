import logging
import os
from pathlib import Path
from typing import List, Optional
import cv2

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    BackgroundTasks,
    status
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.camera import Camera
from app.models.video import Video
from app.models.event import Event
from app.schemas.camera import CameraResponse
from app.schemas.video import VideoUploadResponse, VideoResponse
from app.schemas.event import EventResponse
from app.services.video_service import video_service
from app.services.evidence_service import evidence_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Cameras & Video"])


@router.get("/cameras", response_model=List[CameraResponse])
def get_cameras(db: Session = Depends(get_db)):
    """
    GET /api/v1/cameras
    Returns list of registered cameras.
    """
    cameras = db.query(Camera).all()
    result = []
    for cam in cameras:
        v_url = None
        if cam.video_url:
            v_url = (
                cam.video_url
                if cam.video_url.startswith("/api") or cam.video_url.startswith("http")
                else f"/api/v1/cameras/{cam.camera_id}/video"
            )

        result.append(
            CameraResponse(
                camera_id=cam.camera_id,
                camera_name=cam.camera_name,
                name=cam.camera_name,
                location=cam.location,
                status=cam.status or "online",
                event_count=cam.event_count or 0,
                video_url=v_url,
                thumbnail_url=cam.thumbnail_url,
            )
        )
    return result


@router.post("/cameras/{camera_id}/video", response_model=VideoUploadResponse)
async def upload_camera_video(
    camera_id: str,
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    camera_name: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    POST /api/v1/cameras/{camera_id}/video
    Accept multipart/form-data, save under data/videos/, trigger background YOLO processing.
    """
    if not video.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename."
        )

    content = await video.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded video file is empty."
        )

    # Save the uploaded bytes
    saved_filename = (
        f"{camera_id}_{video.filename}"
        if not video.filename.startswith(camera_id)
        else video.filename
    )
    saved_path = video_service.save_uploaded_video(content, saved_filename)

    logger.info(f"[UPLOAD] Saved {saved_filename} ({len(content):,} bytes) for camera {camera_id}")
    logger.info(f"[UPLOAD] Absolute path: {saved_path}")
    logger.info(f"[UPLOAD] File exists: {saved_path.exists()}")

    # Resolve camera name
    default_name = camera_name or settings.CAMERAS.get(camera_id, {}).get(
        "camera_name", f"Camera {camera_id}"
    )

    # Create or update camera record
    camera = db.query(Camera).filter(Camera.camera_id == camera_id).first()
    if not camera:
        camera = Camera(
            camera_id=camera_id,
            camera_name=default_name,
            status="processing",
            video_url=str(saved_path),
        )
        db.add(camera)
    else:
        if camera_name:
            camera.camera_name = camera_name
        camera.status = "processing"
        camera.video_url = str(saved_path)

    # Create video record
    video_record = Video(
        camera_id=camera_id,
        filename=saved_filename,
        processing_status="uploaded",
    )
    db.add(video_record)
    db.commit()
    db.refresh(video_record)

    logger.info(
        f"[UPLOAD] Video record id={video_record.id} created for camera {camera_id}. "
        f"Scheduling background processing."
    )

    # Queue background YOLO processing
    background_tasks.add_task(video_service.process_video_background, video_record.id)

    return VideoUploadResponse(
        camera_id=camera_id,
        status="processing",
        message=f"Video uploaded successfully. Processing started (video_id={video_record.id}).",
        video_id=video_record.id,
    )


@router.get("/cameras/{camera_id}/video")
def get_camera_video(camera_id: str, db: Session = Depends(get_db)):
    """Return/stream the uploaded video file for a camera."""
    video_rec = (
        db.query(Video)
        .filter(Video.camera_id == camera_id)
        .order_by(Video.id.desc())
        .first()
    )
    file_path = None
    if video_rec and video_rec.filename:
        candidate = settings.VIDEO_DIR / video_rec.filename
        if candidate.exists():
            file_path = str(candidate)

    if not file_path:
        # Fallback: check files matching camera_id in VIDEO_DIR
        for p in settings.VIDEO_DIR.glob(f"{camera_id}_*"):
            if p.is_file():
                file_path = str(p)
                break

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file not found for camera {camera_id}."
        )

    return FileResponse(file_path, media_type="video/mp4")


@router.get("/cameras/{camera_id}/events", response_model=List[EventResponse])
def get_camera_events(
    camera_id: str,
    object_type: Optional[str] = None,
    color: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/cameras/{camera_id}/events
    Returns detected events for a specific camera.
    """
    query = db.query(Event).filter(Event.camera_id == camera_id)
    if object_type:
        query = query.filter(Event.object_type == object_type)
    if color:
        query = query.filter(Event.color == color)
    return query.order_by(Event.timestamp.asc()).limit(limit).all()


@router.get("/cameras/{camera_id}/status")
def get_camera_processing_status(camera_id: str, db: Session = Depends(get_db)):
    """
    GET /api/v1/cameras/{camera_id}/status
    Returns the processing status of the most recent video for this camera.
    """
    video_rec = (
        db.query(Video)
        .filter(Video.camera_id == camera_id)
        .order_by(Video.id.desc())
        .first()
    )
    if not video_rec:
        return {"camera_id": camera_id, "status": "no_video", "video_id": None}

    event_count = (
        db.query(Event)
        .filter(Event.camera_id == camera_id, Event.video_id == video_rec.id)
        .count()
    )

    return {
        "camera_id": camera_id,
        "video_id": video_rec.id,
        "filename": video_rec.filename,
        "status": video_rec.processing_status,
        "fps": video_rec.fps,
        "duration": video_rec.duration,
        "event_count": event_count,
    }


@router.get("/videos/{video_id}/status")
def get_video_status(video_id: int, db: Session = Depends(get_db)):
    """
    GET /api/v1/videos/{video_id}/status
    Returns processing status for a specific video by ID.
    """
    video_rec = db.query(Video).filter(Video.id == video_id).first()
    if not video_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video id={video_id} not found."
        )

    event_count = (
        db.query(Event)
        .filter(Event.video_id == video_id)
        .count()
    )

    return {
        "video_id": video_rec.id,
        "camera_id": video_rec.camera_id,
        "filename": video_rec.filename,
        "status": video_rec.processing_status,
        "fps": video_rec.fps,
        "duration": video_rec.duration,
        "event_count": event_count,
    }


@router.get("/evidence/{event_id}")
def get_evidence_clip(event_id: int, db: Session = Depends(get_db)):
    """
    GET /api/v1/evidence/{event_id}
    Returns playable evidence video clip for the requested event.
    The clip is extracted from the SAME video that was uploaded and processed.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found."
        )

    # Resolve source video record
    video_rec = None
    if event.video_id:
        video_rec = db.query(Video).filter(Video.id == event.video_id).first()
    if not video_rec:
        video_rec = (
            db.query(Video)
            .filter(Video.camera_id == event.camera_id)
            .order_by(Video.id.desc())
            .first()
        )

    video_path = None
    if video_rec and video_rec.filename:
        vp = Path(video_rec.filename)
        if not vp.is_absolute():
            vp = (settings.VIDEO_DIR / vp.name).resolve()
        if vp.exists():
            video_path = vp

    clip_file = None
    # Check stored evidence path
    if event.evidence_path and os.path.exists(event.evidence_path):
        clip_file = event.evidence_path
    else:
        # Check canonical convention: data/evidence/evt_001.mp4
        candidate = settings.EVIDENCE_DIR / f"evt_{event.id:03d}.mp4"
        if candidate.exists():
            clip_file = str(candidate)

    # Validate that existing clip exists, has content, and matches source video dimensions
    needs_regeneration = False
    if not clip_file or not os.path.exists(clip_file) or os.path.getsize(clip_file) < 1024:
        needs_regeneration = True
    elif video_path:
        try:
            cap_c = cv2.VideoCapture(str(clip_file))
            cw = int(cap_c.get(cv2.CAP_PROP_FRAME_WIDTH))
            ch = int(cap_c.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap_c.release()

            cap_v = cv2.VideoCapture(str(video_path))
            vw = int(cap_v.get(cv2.CAP_PROP_FRAME_WIDTH))
            vh = int(cap_v.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap_v.release()

            if vw > 0 and vh > 0 and (cw != vw or ch != vh):
                logger.warning(
                    f"[EVIDENCE] Clip {clip_file} dimensions ({cw}x{ch}) do not match "
                    f"source video ({vw}x{vh}). Regenerating from source video."
                )
                needs_regeneration = True
        except Exception as e:
            logger.warning(f"[EVIDENCE] Clip dimension check error: {e}")
            needs_regeneration = True

    if needs_regeneration and video_path:
        duration = video_rec.duration if video_rec else 0.0
        clip_file = evidence_service.generate_clip(
            video_path=video_path,
            timestamp=event.timestamp,
            duration=duration,
            event_id=event.id,
            force=True,
        )
        if clip_file:
            event.evidence_path = clip_file
            db.commit()

    if not clip_file or not os.path.exists(clip_file):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence clip for event {event_id} not available."
        )

    return FileResponse(clip_file, media_type="video/mp4")


@router.get("/evidence/{event_id}/frame")
def get_evidence_frame(event_id: int, db: Session = Depends(get_db)):
    """
    GET /api/v1/evidence/{event_id}/frame
    Returns an annotated evidence snapshot frame extracted from the real CCTV video.
    CRITICAL: Draws the bounding box reticle ONLY around the requested object event.
    NEVER draws boxes around any people or other objects in the frame.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found."
        )

    # Check cached frame
    cached_frame_file = settings.EVIDENCE_DIR / f"evt_{event.id:03d}_frame.jpg"
    if cached_frame_file.exists() and cached_frame_file.stat().st_size > 500:
        return FileResponse(str(cached_frame_file), media_type="image/jpeg")

    # Locate real video source
    video_rec = None
    if event.video_id:
        video_rec = db.query(Video).filter(Video.id == event.video_id).first()
    if not video_rec:
        video_rec = (
            db.query(Video)
            .filter(Video.camera_id == event.camera_id)
            .order_by(Video.id.desc())
            .first()
        )

    if not video_rec or not video_rec.filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source video for event {event_id} not available."
        )

    vp = Path(video_rec.filename)
    if not vp.is_absolute():
        vp = (settings.VIDEO_DIR / vp.name).resolve()
    if not vp.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source video file not found on disk: {vp}"
        )

    import cv2
    import json
    import numpy as np

    cap = cv2.VideoCapture(str(vp))
    if not cap.isOpened():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cannot open video for frame extraction."
        )

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_idx = max(0, int(event.timestamp * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read video frame at timestamp {event.timestamp}s."
        )

    # Draw bounding box ONLY around the requested target object
    bbox = None
    if event.bounding_box:
        try:
            bb_data = json.loads(event.bounding_box)
            if isinstance(bb_data, list) and len(bb_data) >= 4:
                bbox = [int(v) for v in bb_data[:4]]
            elif isinstance(bb_data, dict):
                bx = int(bb_data.get("x", 0))
                by = int(bb_data.get("y", 0))
                bw = int(bb_data.get("w", 0))
                bh = int(bb_data.get("h", 0))
                bbox = [bx, by, bx + bw, by + bh]
        except Exception:
            pass

    annotated = frame.copy()
    if bbox:
        x1, y1, x2, y2 = bbox
        h_frame, w_frame = annotated.shape[:2]
        x1 = max(0, min(x1, w_frame - 1))
        y1 = max(0, min(y1, h_frame - 1))
        x2 = max(x1 + 1, min(x2, w_frame))
        y2 = max(y1 + 1, min(y2, h_frame))

        # Cyan target box (BGR: 255, 200, 0)
        color_bgr = (255, 200, 0)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color_bgr, 2)

        # Tactical corner brackets
        corner_len = min(15, (x2 - x1) // 3, (y2 - y1) // 3)
        if corner_len > 3:
            cv2.line(annotated, (x1, y1), (x1 + corner_len, y1), (255, 255, 255), 3)
            cv2.line(annotated, (x1, y1), (x1, y1 + corner_len), (255, 255, 255), 3)
            cv2.line(annotated, (x2, y1), (x2 - corner_len, y1), (255, 255, 255), 3)
            cv2.line(annotated, (x2, y1), (x2, y1 + corner_len), (255, 255, 255), 3)
            cv2.line(annotated, (x1, y2), (x1 + corner_len, y2), (255, 255, 255), 3)
            cv2.line(annotated, (x1, y2), (x1, y2 - corner_len), (255, 255, 255), 3)
            cv2.line(annotated, (x2, y2), (x2 - corner_len, y2), (255, 255, 255), 3)
            cv2.line(annotated, (x2, y2), (x2, y2 - corner_len), (255, 255, 255), 3)

        # Label tag: TARGET ONLY (e.g. CAR 92% or RED CAR 92%)
        obj_name = (event.object_type or "OBJECT").upper()
        col_name = f"{event.color.upper()} " if event.color else ""
        conf_pct = int((event.confidence or 1.0) * 100)
        label = f"{col_name}{obj_name} {conf_pct}%"

        (txt_w, txt_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        badge_y1 = max(0, y1 - txt_h - 10)
        badge_y2 = y1
        badge_x2 = min(w_frame, x1 + txt_w + 10)
        cv2.rectangle(annotated, (x1, badge_y1), (badge_x2, badge_y2), (20, 20, 20), -1)
        cv2.rectangle(annotated, (x1, badge_y1), (badge_x2, badge_y2), color_bgr, 1)
        cv2.putText(
            annotated, label,
            (x1 + 5, y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA
        )

    cv2.imwrite(str(cached_frame_file), annotated)
    return FileResponse(str(cached_frame_file), media_type="image/jpeg")


@router.get("/events", response_model=List[EventResponse])
def get_events(
    camera_id: Optional[str] = None,
    object_type: Optional[str] = None,
    color: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List detected events, with optional filters."""
    query = db.query(Event)
    if camera_id:
        query = query.filter(Event.camera_id == camera_id)
    if object_type:
        query = query.filter(Event.object_type == object_type)
    if color:
        query = query.filter(Event.color == color)
    return query.order_by(Event.id.asc()).limit(limit).all()


@router.get("/videos", response_model=List[VideoResponse])
def get_videos(db: Session = Depends(get_db)):
    """List video processing records."""
    return db.query(Video).order_by(Video.id.desc()).all()
