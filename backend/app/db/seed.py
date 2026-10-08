import logging
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, Base, engine
from app.models.event import Camera

logger = logging.getLogger("visiontrace.seed")


def seed_database(db: Session = None):
    """
    Ensure the 4 registered camera definitions exist in the database.
    DO NOT SEED MOCK OR FAKE EVENTS: The database must remain clean until
    actual videos are uploaded and processed by YOLO.
    """
    close_after = False
    if db is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        close_after = True

    try:
        cameras_data = [
            {"camera_id": "CAM-01", "camera_name": "Main Gate", "location": "Main Gate", "status": "online"},
            {"camera_id": "CAM-02", "camera_name": "Parking", "location": "Parking", "status": "online"},
            {"camera_id": "CAM-03", "camera_name": "Building Entrance", "location": "Building", "status": "online"},
            {"camera_id": "CAM-04", "camera_name": "Exit Gate", "location": "Exit Gate", "status": "online"},
        ]

        for c in cameras_data:
            existing = db.query(Camera).filter(Camera.camera_id == c["camera_id"]).first()
            if not existing:
                cam = Camera(**c)
                db.add(cam)

        db.commit()
        logger.info("Initialized camera registry. Events table is empty and strictly awaiting real video ingestion.")
    finally:
        if close_after:
            db.close()


if __name__ == "__main__":
    seed_database()
    print("Camera registry initialized.")
