from typing import Optional
from pydantic import BaseModel, ConfigDict


class CameraBase(BaseModel):
    camera_id: str
    camera_name: str
    location: Optional[str] = None
    status: str = "online"
    event_count: int = 0


class CameraCreate(BaseModel):
    camera_id: str
    camera_name: Optional[str] = None
    name: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = "online"


class CameraResponse(CameraBase):
    name: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
