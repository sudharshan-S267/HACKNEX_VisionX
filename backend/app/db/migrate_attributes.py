import logging
from app.db.session import engine
from sqlalchemy import text

logger = logging.getLogger("visiontrace.migration")

NEW_COLUMNS = [
    ("clothing_upper", "TEXT"),
    ("clothing_upper_color", "TEXT"),
    ("clothing_lower", "TEXT"),
    ("clothing_lower_color", "TEXT"),
    ("has_backpack", "INTEGER DEFAULT 0"),
    ("has_handbag", "INTEGER DEFAULT 0"),
    ("has_suitcase", "INTEGER DEFAULT 0"),
    ("has_hat", "INTEGER DEFAULT 0"),
    ("has_cap", "INTEGER DEFAULT 0"),
    ("has_helmet", "INTEGER DEFAULT 0"),
    ("has_umbrella", "INTEGER DEFAULT 0"),
    ("carried_objects", "TEXT"),
    ("attribute_confidence", "REAL"),
    ("attributes_json", "TEXT"),
]


def migrate_event_attributes():
    """Ensure all visual attribute columns exist on the events table without destroying data."""
    with engine.connect() as conn:
        try:
            res = conn.execute(text("PRAGMA table_info(events)"))
            existing_cols = {row[1] for row in res.fetchall()}

            for col_name, col_type in NEW_COLUMNS:
                if col_name not in existing_cols:
                    logger.info(f"[DB MIGRATION] Adding column '{col_name}' ({col_type}) to events table.")
                    try:
                        conn.execute(text(f"ALTER TABLE events ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                    except Exception as err:
                        logger.debug(f"Column '{col_name}' add note: {err}")

            logger.info("[DB MIGRATION] Event visual attribute schema migration complete.")
        except Exception as e:
            logger.warning(f"[DB MIGRATION] Failed to migrate attribute columns: {e}")


if __name__ == "__main__":
    migrate_event_attributes()

