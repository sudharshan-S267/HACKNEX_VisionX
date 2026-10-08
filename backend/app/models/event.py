from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class Camera(Base):
    __tablename__ = "cameras"

    camera_id = Column(String, primary_key=True, index=True)
    camera_name = Column(String, nullable=False)
    location = Column(String, nullable=True)
    status = Column(String, default="online")
    event_count = Column(Integer, default=0)
    video_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)

    # Alias property for name compatibility with backend2
    @property
    def name(self) -> str:
        return self.camera_name

    @name.setter
    def name(self, val: str) -> None:
        self.camera_name = val

    # Alias property for video_path compatibility with backend2
    @property
    def video_path(self) -> str:
        return self.video_url

    @video_path.setter
    def video_path(self, val: str) -> None:
        self.video_url = val

    videos = relationship("Video", back_populates="camera", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="camera", cascade="all, delete-orphan")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(String, unique=True, index=True, nullable=True)
    camera_id = Column(String, ForeignKey("cameras.camera_id"), index=True, nullable=False)
    video_id = Column(Integer, ForeignKey("videos.id"), index=True, nullable=True)
    camera_name = Column(String, nullable=True)
    timestamp = Column(Float, index=True, nullable=False)
    timestamp_start = Column(Float, nullable=True)
    timestamp_end = Column(Float, nullable=True)
    confidence = Column(Float, default=1.0)
    color_confidence = Column(Float, nullable=True)
    event_type = Column(String, index=True, nullable=False, default="object_detected")
    object_type = Column(String, index=True, nullable=True)
    object_id = Column(Integer, nullable=True)
    color = Column(String, index=True, nullable=True)
    action = Column(String, nullable=True)
    location = Column(String, nullable=True)
    description = Column(String, nullable=True)
    evidence_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    bounding_box = Column(Text, nullable=True)

    # Alias property for evidence_path compatibility with backend2
    @property
    def evidence_path(self) -> str:
        return self.evidence_url

    @evidence_path.setter
    def evidence_path(self, val: str) -> None:
        self.evidence_url = val

    # Alias property for bbox compatibility with backend2
    @property
    def bbox(self):
        import json
        if self.bounding_box:
            try:
                return json.loads(self.bounding_box)
            except Exception:
                return self.bounding_box
        return None

    @bbox.setter
    def bbox(self, val):
        import json
        if isinstance(val, (list, dict)):
            self.bounding_box = json.dumps(val)
        else:
            self.bounding_box = str(val) if val is not None else None

    camera = relationship("Camera", back_populates="events")
