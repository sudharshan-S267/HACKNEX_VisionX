from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TimeRange(BaseModel):
    start: float = Field(..., description="Start timestamp in seconds")
    end: float = Field(..., description="End timestamp in seconds")

class BoundingBox(BaseModel):
    x: float
    y: float
    w: float
    h: float

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    camera_ids: Optional[List[str]] = Field(default=None, description="Optional camera ID filter list")
    time_range: Optional[TimeRange] = Field(default=None, description="Optional timestamp range filter")

class Match(BaseModel):
    camera_id: str
    camera_name: str
    timestamp: float
    confidence: float
    event_type: str
    description: str
    evidence_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    bounding_box: Optional[BoundingBox] = None

class TrajectoryPoint(BaseModel):
    camera_id: str
    camera_name: Optional[str] = None
    timestamp: float
    location: Optional[str] = None
    confidence: Optional[float] = None
    evidence_url: Optional[str] = None

class TrajectoryLink(BaseModel):
    from_camera: str
    to_camera: str
    time_delta: float
    confidence: float
    transition_valid: bool
    description: str = "consistent visual match"

class TrajectoryRequest(BaseModel):
    object_type: str = Field(..., description="Detected object class (e.g., car, person, truck)")
    color: Optional[str] = Field(default=None, description="Object color (e.g., red, blue)")

class TrajectoryResponse(BaseModel):
    object_type: str
    color: Optional[str] = None
    status: str = "consistent visual match"
    total_nodes: int = 0
    trajectory: List[TrajectoryPoint] = []
    links: Optional[List[TrajectoryLink]] = None

class QueryResponse(BaseModel):
    query: str
    answer: str
    matches: List[Match] = []
    trajectory: Optional[List[TrajectoryPoint]] = None
    processing_time_ms: Optional[float] = None
    total_frames_analyzed: Optional[int] = None

class ParsedQuery(BaseModel):
    raw_query: str
    object_type: Optional[str] = None
    color: Optional[str] = None
    action: Optional[str] = None
    location: Optional[str] = None
    camera_id: Optional[str] = None
    time_filter: Optional[float] = None
    operation: str = "search"  # search | first_seen | last_seen | trajectory | evidence
