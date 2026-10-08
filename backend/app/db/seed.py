import logging
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, Base, engine
from app.models.event import Camera, Event

logger = logging.getLogger("visiontrace.seed")

def seed_database(db: Session = None):
    """Seed camera and detection events for testing and demonstration."""
    close_after = False
    if db is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        close_after = True

    try:
        # Check if already seeded
        if db.query(Event).count() > 0:
            logger.info("Database already contains events, skipping seed.")
            return

        cameras_data = [
            {"camera_id": "CAM-01", "camera_name": "Main Gate", "location": "Main Gate", "status": "online"},
            {"camera_id": "CAM-02", "camera_name": "Parking", "location": "Parking", "status": "online"},
            {"camera_id": "CAM-03", "camera_name": "Building Entrance", "location": "Building", "status": "online"},
            {"camera_id": "CAM-04", "camera_name": "Exit Gate", "location": "Exit Gate", "status": "online"},
        ]

        for c in cameras_data:
            cam = Camera(**c)
            db.merge(cam)

        events_data = [
            {
                "event_id": "evt_001",
                "camera_id": "CAM-01",
                "camera_name": "Main Gate",
                "timestamp": 12.4,
                "confidence": 0.94,
                "event_type": "vehicle_detected",
                "object_type": "car",
                "color": "red",
                "action": "enter",
                "location": "Main Gate",
                "description": "red car detected entering campus",
                "evidence_url": "/api/v1/evidence/evt_001",
                "thumbnail_url": "/thumbnails/evt_001.jpg",
            },
            {
                "event_id": "evt_002",
                "camera_id": "CAM-02",
                "camera_name": "Parking",
                "timestamp": 18.7,
                "confidence": 0.88,
                "event_type": "vehicle_detected",
                "object_type": "car",
                "color": "red",
                "action": "park",
                "location": "Parking",
                "description": "red car detected in parking area",
                "evidence_url": "/api/v1/evidence/evt_002",
                "thumbnail_url": "/thumbnails/evt_002.jpg",
            },
            {
                "event_id": "evt_003",
                "camera_id": "CAM-03",
                "camera_name": "Building Entrance",
                "timestamp": 15.1,
                "confidence": 0.92,
                "event_type": "person_detected",
                "object_type": "person",
                "color": "blue",
                "action": "walk",
                "location": "Building",
                "description": "person wearing blue shirt entered main lobby",
                "evidence_url": "/api/v1/evidence/evt_003",
                "thumbnail_url": "/thumbnails/evt_003.jpg",
            },
            {
                "event_id": "evt_004",
                "camera_id": "CAM-04",
                "camera_name": "Exit Gate",
                "timestamp": 25.2,
                "confidence": 0.91,
                "event_type": "vehicle_detected",
                "object_type": "car",
                "color": "red",
                "action": "exit",
                "location": "Exit Gate",
                "description": "red car exiting through gate",
                "evidence_url": "/api/v1/evidence/evt_004",
                "thumbnail_url": "/thumbnails/evt_004.jpg",
            },
            {
                "event_id": "evt_005",
                "camera_id": "CAM-01",
                "camera_name": "Main Gate",
                "timestamp": 8.0,
                "confidence": 0.89,
                "event_type": "vehicle_detected",
                "object_type": "truck",
                "color": "white",
                "action": "enter",
                "location": "Main Gate",
                "description": "white delivery truck entered main gate",
                "evidence_url": "/api/v1/evidence/evt_005",
                "thumbnail_url": "/thumbnails/evt_005.jpg",
            },
            {
                "event_id": "evt_006",
                "camera_id": "CAM-02",
                "camera_name": "Parking",
                "timestamp": 22.0,
                "confidence": 0.85,
                "event_type": "vehicle_detected",
                "object_type": "motorcycle",
                "color": "black",
                "action": "park",
                "location": "Parking",
                "description": "black motorcycle parked in designated bay",
                "evidence_url": "/api/v1/evidence/evt_006",
                "thumbnail_url": "/thumbnails/evt_006.jpg",
            },
        ]

        for e in events_data:
            ev = Event(**e)
            db.merge(ev)

        db.commit()
        logger.info(f"Seeded {len(cameras_data)} cameras and {len(events_data)} events successfully.")
    finally:
        if close_after:
            db.close()

if __name__ == "__main__":
    seed_database()
    print("Database seeded successfully.")
