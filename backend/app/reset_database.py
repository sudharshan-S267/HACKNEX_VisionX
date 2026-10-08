import logging
import shutil
from pathlib import Path

from app.core.config import settings
from app.db.session import engine, Base, SessionLocal
from app.db.seed import seed_database

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("visiontrace.reset")


def reset_database():
    """
    Safe development reset mechanism:
    1. Eradicates old SQLite database tables.
    2. Re-creates clean database tables.
    3. Seeds only camera definitions (CAM-01 to CAM-04).
    4. Cleans up stale evidence clips.
    """
    logger.info("Dropping all existing database tables...")
    Base.metadata.drop_all(bind=engine)

    logger.info("Recreating database tables...")
    Base.metadata.create_all(bind=engine)

    logger.info("Initializing registered cameras...")
    seed_database()

    # Clean old evidence clips to avoid stale clips
    if settings.EVIDENCE_DIR.exists():
        logger.info(f"Purging old evidence clips from {settings.EVIDENCE_DIR}...")
        for clip in settings.EVIDENCE_DIR.glob("evt_*.mp4"):
            try:
                clip.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove clip {clip.name}: {e}")

    logger.info("Database reset complete. All events cleared. 4 cameras registered and ready for real footage.")


if __name__ == "__main__":
    reset_database()
