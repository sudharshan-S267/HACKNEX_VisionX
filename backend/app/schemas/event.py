from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class EventBase(BaseModel):
    camera_id: str
    timestamp: float
    object_type: str
    object_id: Optional[int] = None
    color: Optional[str] = None
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]
    description: str
    evidence_path: Optional[str] = None


class EventCreate(EventBase):
    pass


class EventResponse(EventBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
