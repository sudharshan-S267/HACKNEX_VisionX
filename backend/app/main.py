import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.session import engine, Base
from app.db.seed import seed_database
from app.api.routes.query import router as query_router
from app.api.routes.trajectory import router as trajectory_router
from app.api.routes.cameras import router as cameras_router
from app.services.query_service import query_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("visiontrace.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Initializing VisionTrace backend database tables...")
    Base.metadata.create_all(bind=engine)

    # Automatically ensure new columns exist in existing SQLite tables
    from sqlalchemy import text
    with engine.connect() as conn:
        for tbl, col, col_type in [
            ("videos", "error_message", "TEXT"),
            ("events", "video_id", "INTEGER"),
            ("events", "timestamp_start", "FLOAT"),
            ("events", "timestamp_end", "FLOAT"),
            ("events", "color_confidence", "FLOAT"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_type}"))
                conn.commit()
            except Exception:
                pass

    # Seed camera registry (no fake events)
    seed_database()

    # Reset any videos that were stuck in 'processing' from a previous crash
    from app.db.session import SessionLocal
    from app.services.video_service import video_service
    db = SessionLocal()
    try:
        video_service.reset_stuck_processing(db)
    finally:
        db.close()

    # Ensure debug directory exists
    debug_dir = settings.BASE_DIR / "data" / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Startup complete.")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down VisionTrace backend.")


app = FastAPI(
    title="VisionTrace AI",
    description="Multi-Camera Video Intelligence, Grounded Query, Trajectory and Video Ingestion Engine",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if "*" not in settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
# 1. Cameras, Video Upload & Ingestion, Evidence & Events: /api/v1/...
app.include_router(cameras_router)

# 2. Conversational & Grounded Query Engine: /api/v1/query
app.include_router(query_router, prefix="/api/v1")

# 3. Cross-Camera Trajectory Engine: /api/v1/trajectory
app.include_router(trajectory_router, prefix="/api/v1")


# Health Check Endpoints (both /health and /api/v1/health supported)
@app.get("/api/v1/health", summary="Service Health Check")
@app.get("/health", summary="Root Health Check")
def health_check():
    ollama_ok = query_service._check_ollama_health()
    return {
        "status": "ok",
        "version": settings.VERSION,
        "ollama": {
            "status": "connected" if ollama_ok else "unavailable",
            "base_url": settings.OLLAMA_BASE_URL,
            "model": settings.OLLAMA_MODEL,
        },
        "database": "sqlite",
        "yolo_model": settings.YOLO_MODEL,
    }


# Static Mounts for Direct Video/Evidence File Access
if settings.VIDEO_DIR.exists():
    app.mount("/data/videos", StaticFiles(directory=str(settings.VIDEO_DIR)), name="videos")

if settings.EVIDENCE_DIR.exists():
    app.mount("/data/evidence", StaticFiles(directory=str(settings.EVIDENCE_DIR)), name="evidence")

# Debug frames static mount
debug_dir = settings.BASE_DIR / "data" / "debug"
debug_dir.mkdir(parents=True, exist_ok=True)
app.mount("/data/debug", StaticFiles(directory=str(debug_dir)), name="debug")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
