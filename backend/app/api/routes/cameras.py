import logging
import os
from pathlib import Path
from typing import List, Optional

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

    clip_file = None

    # Check stored evidence path
    if event.evidence_path and os.path.exists(event.evidence_path):
        clip_file = event.evidence_path
    else:
        # Check canonical convention: data/evidence/evt_001.mp4
        candidate = settings.EVIDENCE_DIR / f"evt_{event.id:03d}.mp4"
        if candidate.exists():
            clip_file = str(candidate)

    if not clip_file or not os.path.exists(clip_file):
        # On-the-fly generation from the original video
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

        if video_rec and video_rec.filename:
            vp = Path(video_rec.filename)
            if not vp.is_absolute():
                vp = (settings.VIDEO_DIR / vp.name).resolve()
            if vp.exists():
                duration = video_rec.duration or 0.0
                clip_file = evidence_service.generate_clip(
                    video_path=vp,
                    timestamp=event.timestamp,
                    duration=duration,
                    event_id=event.id,
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
