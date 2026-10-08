from typing import Optional
from pydantic import BaseModel, ConfigDict


class VideoUploadResponse(BaseModel):
    camera_id: str
    status: str = "processing"
    message: str = "Video uploaded successfully"
    video_id: Optional[int] = None


class VideoResponse(BaseModel):
    id: int
    camera_id: str
    filename: str
    duration: Optional[float] = None
    fps: Optional[float] = None
    processing_status: str
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
