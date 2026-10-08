from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    camera_id = Column(String, ForeignKey("cameras.camera_id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    duration = Column(Float, nullable=True)
    fps = Column(Float, nullable=True)
    processing_status = Column(String, default="uploaded")

    camera = relationship("Camera", back_populates="videos")
