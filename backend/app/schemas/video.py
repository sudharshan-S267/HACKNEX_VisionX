from typing import Optional
from pydantic import BaseModel, ConfigDict


class VideoUploadResponse(BaseModel):
    camera_id: str
    status: str = "processing"
    message: str = "Video uploaded successfully"


class VideoResponse(BaseModel):
    id: int
    camera_id: str
    filename: str
    duration: Optional[float] = None
    fps: Optional[float] = None
    processing_status: str

    model_config = ConfigDict(from_attributes=True)
