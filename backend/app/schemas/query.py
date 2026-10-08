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
    norm_x: Optional[float] = None
    norm_y: Optional[float] = None
    norm_w: Optional[float] = None
    norm_h: Optional[float] = None

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    camera_ids: Optional[List[str]] = Field(default=None, description="Optional camera ID filter list")
    time_range: Optional[TimeRange] = Field(default=None, description="Optional timestamp range filter")

class Match(BaseModel):
    id: Optional[int] = None
    camera_id: str
    camera_name: str
    timestamp: float
    confidence: float
    event_type: str
    object_type: Optional[str] = None
    color: Optional[str] = None
    description: str
    evidence_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    bounding_box: Optional[BoundingBox] = None
    clothing_upper: Optional[str] = None
    clothing_upper_color: Optional[str] = None
    clothing_lower: Optional[str] = None
    clothing_lower_color: Optional[str] = None
    has_backpack: Optional[bool] = None
    has_cap: Optional[bool] = None
    has_hat: Optional[bool] = None
    carried_objects: Optional[List[str]] = None
    attribute_confidence: Optional[float] = None

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
    status: str = "resolved"  # resolved | unsupported_object | clarification_required | all_objects | gender_unsupported
    matches: List[Match] = []
    trajectory: Optional[List[TrajectoryPoint]] = None
    processing_time_ms: Optional[float] = None
    total_frames_analyzed: Optional[int] = None

class QueryIntent(BaseModel):
    raw_query: str
    object_type: Optional[str] = None
    object_types: List[str] = Field(default_factory=list)
    color: Optional[str] = None
    clothing_upper_color: Optional[str] = None
    clothing_lower_color: Optional[str] = None
    has_backpack: Optional[bool] = None
    has_cap: Optional[bool] = None
    has_hat: Optional[bool] = None
    carried_object: Optional[str] = None
    action: Optional[str] = None
    location: Optional[str] = None
    camera_id: Optional[str] = None
    time_start: Optional[float] = None
    time_end: Optional[float] = None
    time_filter: Optional[float] = None
    attributes: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    status: str = "resolved"  # resolved | unsupported_object | clarification_required | all_objects | gender_unsupported
    status_message: Optional[str] = None
    operation: str = "search"  # search | first_seen | last_seen | trajectory | evidence

# Alias for backward compatibility
ParsedQuery = QueryIntent
