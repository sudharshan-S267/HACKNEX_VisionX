from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict, field_validator
import json


class EventBase(BaseModel):
    camera_id: str
    timestamp: float
    object_type: Optional[str] = None
    object_id: Optional[int] = None
    color: Optional[str] = None
    confidence: float
    bbox: Optional[List[float]] = None  # [x1, y1, x2, y2] — optional, may be null
    description: Optional[str] = None
    evidence_path: Optional[str] = None


class EventCreate(EventBase):
    pass


class EventResponse(BaseModel):
    id: int
    camera_id: str
    video_id: Optional[int] = None
    camera_name: Optional[str] = None
    timestamp: float
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    object_type: Optional[str] = None
    object_id: Optional[int] = None
    color: Optional[str] = None
    confidence: float
    color_confidence: Optional[float] = None
    event_type: Optional[str] = None
    description: Optional[str] = None
    evidence_url: Optional[str] = None
    bbox: Optional[List[float]] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("bbox", mode="before")
    @classmethod
    def parse_bbox(cls, v: Any) -> Optional[List[float]]:
        """Parse bounding_box JSON string or list into List[float]."""
        if v is None:
            return None
        if isinstance(v, list):
            return [float(x) for x in v]
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [float(x) for x in parsed]
            except Exception:
                pass
        return None
