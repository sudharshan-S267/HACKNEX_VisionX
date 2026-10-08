import os
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, Any, List

# Base directory of the backend
BASE_DIR = Path(__file__).resolve().parent.parent.parent

def load_env_file(filepath: Path) -> None:
    """Lightweight .env parser without external dependencies."""
    if not filepath.is_file():
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass

# Load .env if present
load_env_file(BASE_DIR / ".env")


class CameraConfig(BaseModel):
    camera_id: str
    camera_name: str
    location: str


class Settings:
    PROJECT_NAME: str = "VisionTrace AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    BASE_DIR: Path = BASE_DIR

    # SQLite Database Path
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "visiontrace.db")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///./{SQLITE_DB_PATH}")

    # Video and Evidence Storage Paths
    _raw_video_dir: str = os.getenv("VIDEO_DIR", "./data/videos")
    _raw_evidence_dir: str = os.getenv("EVIDENCE_DIR", "./data/evidence")

    VIDEO_DIR: Path = (BASE_DIR / _raw_video_dir).resolve() if not Path(_raw_video_dir).is_absolute() else Path(_raw_video_dir).resolve()
    EVIDENCE_DIR: Path = (BASE_DIR / _raw_evidence_dir).resolve() if not Path(_raw_evidence_dir).is_absolute() else Path(_raw_evidence_dir).resolve()

    FRAME_SAMPLE_INTERVAL: int = int(os.getenv("FRAME_SAMPLE_INTERVAL", "5"))
    YOLO_MODEL: str = os.getenv("YOLO_MODEL", "yolo11n.pt")

    # CORS Configuration
    raw_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    CORS_ORIGINS: List[str] = [orig.strip() for orig in raw_origins.split(",") if orig.strip()]
    if "*" not in CORS_ORIGINS and "http://localhost:5173" not in CORS_ORIGINS:
        CORS_ORIGINS.append("http://localhost:5173")

    # Ollama Configuration
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3:4b")
    OLLAMA_TIMEOUT: float = float(os.getenv("OLLAMA_TIMEOUT", "2.5"))

    # Known Cameras
    CAMERAS: Dict[str, Dict[str, str]] = {
        "CAM-01": {"camera_name": "Main Gate", "location": "main gate"},
        "CAM-02": {"camera_name": "Parking", "location": "parking"},
        "CAM-03": {"camera_name": "Building Entrance", "location": "building"},
        "CAM-04": {"camera_name": "Exit Gate", "location": "exit gate"},
    }

    # Topology transitions (Directed edges with plausible time window in seconds)
    # format: (src, dst, min_time, max_time, base_confidence)
    ALLOWED_TRANSITIONS: List[Dict[str, Any]] = [
        {"from_cam": "CAM-01", "to_cam": "CAM-02", "min_time": 1.0, "max_time": 300.0, "weight": 1.0},
        {"from_cam": "CAM-02", "to_cam": "CAM-03", "min_time": 1.0, "max_time": 300.0, "weight": 1.0},
        {"from_cam": "CAM-03", "to_cam": "CAM-04", "min_time": 1.0, "max_time": 300.0, "weight": 1.0},
        {"from_cam": "CAM-01", "to_cam": "CAM-03", "min_time": 2.0, "max_time": 300.0, "weight": 1.2},
        {"from_cam": "CAM-02", "to_cam": "CAM-04", "min_time": 2.0, "max_time": 300.0, "weight": 1.2},
        {"from_cam": "CAM-01", "to_cam": "CAM-04", "min_time": 3.0, "max_time": 300.0, "weight": 1.5},
    ]


settings = Settings()

# Ensure directories exist
settings.VIDEO_DIR.mkdir(parents=True, exist_ok=True)
settings.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
